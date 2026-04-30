import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.bot import Bot
from app.db.models.message import Message
from app.db.models.relationship import Relationship
from app.db.models.user import User
from app.db.repositories.bot import BotRepository
from app.db.repositories.message import ChatMessageRepository
from app.db.repositories.user import UserRepository

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_db():
    """Create in-memory test database with schema."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_db):
    """Create async session for tests."""
    async_session = async_sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
def bot_repo():
    """Create bot repository instance."""
    return BotRepository(Bot)


@pytest_asyncio.fixture
def user_repo():
    """Create user repository instance."""
    return UserRepository(User)


@pytest_asyncio.fixture
def message_repo():
    """Create message repository instance."""
    return ChatMessageRepository(Message)
