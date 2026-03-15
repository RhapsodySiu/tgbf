import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
# All models must be imported so Base.metadata is fully populated
from app.db.models.user import User
from app.db.models.bot import Bot 
from app.db.models.relationship import Relationship
from app.db.models.message import Message

from app.db.repositories.user import UserRepository

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
repo = UserRepository(User)

async def setup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def test_user_crud():
    async with TestSession() as db:
        user = await repo.create(db, {
            "user_id": 100001,
            "username": "alice",
            "first_name": "Alice",
            "is_allowed": False,
            "invite_token": "token-abc-123",
        })
        assert user.user_id == 100001
        print(f"✓ CREATE  : user_id={user.user_id}, username={user.username}")

         # GET BY ID
        found = await repo.get_by_id(db, 100001)
        assert found is not None and found.username == "alice"
        print(f"✓ GET_BY_ID: {found.username}")

        # GET ALL
        all_users = await repo.get_all(db)
        assert len(all_users) == 1
        print(f"✓ GET_ALL  : {len(all_users)} user(s)")

        # UPDATE
        updated = await repo.update(db, 100001, {"first_name": "Alicia"})
        assert updated.first_name == "Alicia"
        print(f"✓ UPDATE   : first_name={updated.first_name}")

        # GET BY INVITE TOKEN
        by_token = await repo.get_by_invite_token(db, "token-abc-123")
        assert by_token is not None
        print(f"✓ BY_TOKEN : found {by_token.username}")

        # SET ALLOWED
        allowed = await repo.set_allowed(db, 100001, True)
        assert allowed.is_allowed is True
        print(f"✓ SET_ALLOWED: is_allowed={allowed.is_allowed}")

        # GET ALLOWED USERS
        allowed_list = await repo.get_allowed_users(db)
        assert len(allowed_list) == 1
        print(f"✓ GET_ALLOWED_USERS: {len(allowed_list)} user(s)")

        # DELETE
        deleted = await repo.delete(db, 100001)
        assert deleted is True
        gone = await repo.get_by_id(db, 100001)
        assert gone is None
        print(f"✓ DELETE   : confirmed gone={gone is None}")


async def teardown():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

async def main():
    print("── setup ──────────────────────────────")
    await setup()

    print("── UserRepository CRUD ─────────────────")
    await test_user_crud()

    print("── teardown ───────────────────────────")
    await teardown()

    print("\n✅ All assertions passed.")


if __name__ == "__main__":
    asyncio.run(main())