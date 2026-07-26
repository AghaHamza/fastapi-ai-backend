from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_session
from models import User
from auth import hash_password, verify_password, create_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterBody(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginBody(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=201)
async def register(
    body: RegisterBody,
    session: AsyncSession = Depends(get_session)
):
    # Check if email already exists
    result = await session.execute(
        select(User).where(User.email == body.email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already in use"
        )

    # Create new user
    user = User(
        name=body.name,
        email=body.email,
        password=hash_password(body.password)
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }


@router.post("/login")
async def login(
    body: LoginBody,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(User).where(User.email == body.email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(body.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_token(user.id)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }