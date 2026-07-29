from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from database import get_session
from models import Document
from auth import get_current_user
from groq import AsyncGroq
import os
from sentence_transformers import SentenceTransformer

router = APIRouter(prefix="/rag", tags=["RAG"])

# Load embedding model once at startup
# Downloads automatically on first run (~90MB)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

class DocumentInput(BaseModel):
    filename: str
    content: str

class QuestionInput(BaseModel):
    question: str

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

# Upload and index a document
@router.post("/upload", status_code=201)
async def upload_document(
    body: DocumentInput,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Split document into chunks
    chunks = chunk_text(body.content)

    # Generate embeddings for all chunks at once
    embeddings = embedder.encode(chunks)

    # Save each chunk with its embedding
    for chunk, embedding in zip(chunks, embeddings):
        doc = Document(
            filename=body.filename,
            content=chunk,
            embedding=embedding.tolist(),
            user_id=user_id
        )
        session.add(doc)

    await session.commit()

    return {
        "message": f"Document indexed successfully",
        "filename": body.filename,
        "chunks_created": len(chunks)
    }

# Ask a question about your documents
@router.post("/ask")
async def ask_question(
    body: QuestionInput,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # 1. Convert question to embedding
    question_embedding = embedder.encode(body.question).tolist()

    # 2. Find most similar chunks using pgvector
    result = await session.execute(
        text("""
            SELECT content, filename,
                   1 - (embedding <=> :embedding) AS similarity
            FROM documents
            WHERE user_id = :user_id
            ORDER BY embedding <=> :embedding
            LIMIT 3
        """),
        {
            "embedding": str(question_embedding),
            "user_id": user_id
        }
    )
    chunks = result.fetchall()

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No documents found. Upload a document first."
        )

    # 3. Build context from retrieved chunks
    context = "\n\n".join([
        f"[From {chunk.filename}]:\n{chunk.content}"
        for chunk in chunks
    ])

    # 4. Ask LLM with context
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a helpful assistant that answers questions 
                based ONLY on the provided context. If the answer is not in the 
                context, say 'I don't have information about this in the provided 
                documents.' Do not make up information."""
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {body.question}"
            }
        ]
    )

    return {
        "question": body.question,
        "answer": response.choices[0].message.content,
        "sources": [
            {
                "filename": chunk.filename,
                "similarity": round(chunk.similarity, 3),
                "preview": chunk.content[:200] + "..."
            }
            for chunk in chunks
        ]
    }