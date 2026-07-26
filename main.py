from fastapi import FastAPI
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

from routers import auth_router, posts_router, ai_router
from database import engine
from models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Blog API", lifespan=lifespan)

app.include_router(auth_router.router)
app.include_router(posts_router.router)
app.include_router(ai_router.router)