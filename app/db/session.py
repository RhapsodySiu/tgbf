from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.config import settings

url = make_url(settings.database_url)

# SQLite: disable pooling
if url.drivername.startswith("sqlite"):
    engine_kwargs = {
        "echo": settings.environment == "dev",
        "poolclass": NullPool,
    }
else:
    engine_kwargs = {
        "echo": settings.environment == "dev",
        "pool_size": settings.pool_size,
        "max_overflow": 10,
        "pool_pre_ping": True,
    }

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session