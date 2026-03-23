from aiogram import BaseMiddleware
from aiogram.types import Message

from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.db.session import get_session


class AllowlistMiddleware(BaseMiddleware):
    def __init__(self):
        self.user_repo = UserRepository(User)
        super().__init__()

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
        
        print(f"# user_id {user.id}")
        async with get_session() as session:
            user = await self.user_repo.get_by_id(session, user.id)
            if user and user.is_allowed:
                return await handler(event, data)
            else:
                print("User not registered, abort")
                return