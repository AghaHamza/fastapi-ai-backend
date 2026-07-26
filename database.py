from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv
import os
import ssl

load_dotenv()

# Remove sslmode and channel_binding from URL — asyncpg handles SSL differently
DATABASE_URL = os.getenv("DATABASE_URL")\
    .replace("postgresql://", "postgresql+asyncpg://")\
    .replace("?sslmode=require&channel_binding=require", "")\
    .replace("?sslmode=require", "")

# Create SSL context manually
ssl_context = ssl.create_default_context()

# Create async engine with SSL
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"ssl": ssl_context}
)

async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session