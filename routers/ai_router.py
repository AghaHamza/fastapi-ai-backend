from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_session
from models import Post
from auth import get_current_user
import os
from fastapi.responses import StreamingResponse
import json

router = APIRouter(prefix="/ai", tags=["AI"])

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

class ChatMessage(BaseModel):
    message: str

class SummarizeRequest(BaseModel):
    post_id: int

# Simple chat
@router.post("/chat")
async def chat(
    body: ChatMessage,
    user_id: int = Depends(get_current_user)
):
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": body.message}
        ]
    )
    return {
        "response": response.choices[0].message.content,
        "tokens_used": response.usage.total_tokens
    }

# Summarize a blog post
@router.post("/summarize")
async def summarize_post(
    body: SummarizeRequest,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    post = await session.get(Post, body.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a content summarizer. Return a concise 2-3 sentence summary."},
            {"role": "user", "content": f"Title: {post.title}\n\nContent: {post.content}"}
        ]
    )

    return {
        "post_id": post.id,
        "title": post.title,
        "summary": response.choices[0].message.content
    }

# Multi-turn conversation
@router.post("/chat/conversation")
async def conversation(
    messages: list[dict],
    user_id: int = Depends(get_current_user)
):
    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages
    )

    return {
        "messages": messages + [
            {"role": "assistant", "content": response.choices[0].message.content}
        ],
        "latest_response": response.choices[0].message.content
    }

# Streaming chat endpoint
@router.post("/chat/stream")
async def chat_stream(
    body: ChatMessage,
    
):
    async def generate():
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": body.message}
            ],
            stream=True
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                data = json.dumps({"chunk": delta})
                yield f"data: {data}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )