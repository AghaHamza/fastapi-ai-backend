from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_session
from models import Post, User, Category
from auth import get_current_user

router = APIRouter(prefix="/posts", tags=["Posts"])

class PostCreate(BaseModel):
    title: str
    content: str
    category_id: int | None = None

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author_name: str | None = None
    category_name: str | None = None

    class Config:
        from_attributes = True

@router.get("/")
async def get_posts(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Post).options(
            selectinload(Post.author),
            selectinload(Post.category)
        ).order_by(Post.created_at.desc())
    )
    posts = result.scalars().all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "author": p.author.name if p.author else None,
            "category": p.category.name if p.category else None,
            "created_at": p.created_at
        }
        for p in posts
    ]

@router.get("/{post_id}")
async def get_post(post_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Post).options(
            selectinload(Post.author),
            selectinload(Post.category),
            selectinload(Post.comments).selectinload(Comment.author)
        ).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author": post.author.name if post.author else None,
        "category": post.category.name if post.category else None,
        "created_at": post.created_at,
        "comments": [
            {
                "id": c.id,
                "content": c.content,
                "author": c.author.name,
                "created_at": c.created_at
            }
            for c in post.comments
        ]
    }

@router.post("/", status_code=201)
async def create_post(
    body: PostCreate,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    post = Post(
        title=body.title,
        content=body.content,
        user_id=user_id,
        category_id=body.category_id
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post

@router.put("/{post_id}")
async def update_post(
    post_id: int,
    body: PostCreate,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Post).where(Post.id == post_id, Post.user_id == user_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or unauthorized")

    post.title = body.title
    post.content = body.content
    post.category_id = body.category_id
    await session.commit()
    await session.refresh(post)
    return post

@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    user_id: int = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Post).where(Post.id == post_id, Post.user_id == user_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or unauthorized")

    await session.delete(post)
    await session.commit()
    return {"message": "Post deleted successfully"}