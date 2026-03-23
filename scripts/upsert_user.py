import argparse
import asyncio
from datetime import datetime

from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.db.session import get_session


def parse_joined_at(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value)

async def main():
    parser = argparse.ArgumentParser(
        description="Insert or update a user"
    )
    parser.add_argument("--user-id", type=int, required=True, help="Telegram user_id")
    parser.add_argument("--username", type=str, default=None)
    parser.add_argument("--first-name", type=str, default=None)
    parser.add_argument("--invite-token", type=str, default=None)
    parser.add_argument(
        "--joined-at",
        type=str,
        default=None,
        help="ISO datetime, e.g. 2026-04-01",
    )
    parser.add_argument("--allowed", dest="is_allowed", action="store_true")
    parser.add_argument("--disallowed", dest="is_allowed", action="store_false")
    parser.set_defaults(is_allowed=True)

    args = parser.parse_args()

    repo = UserRepository(User)

    payload = {
        "user_id": args.user_id,
        "username": args.username,
        "first_name": args.first_name,
        "is_allowed": args.is_allowed,
        "invite_token": args.invite_token,
        "joined_at": parse_joined_at(args.joined_at),
    }

    async with get_session() as session:
        existing = await repo.get_by_id(session, args.user_id)

        if existing:
            # keep update payload explicit and safe
            update_data = {
                "username": payload["username"],
                "first_name": payload["first_name"],
                "is_allowed": payload["is_allowed"],
                "invite_token": payload["invite_token"],
                "joined_at": payload["joined_at"],
            }
            user = await repo.update(session, args.user_id, update_data)
            action = "updated"
        else:
            user = await repo.create(session, payload)
            action = "created"
    
    print(
        f"User {action}: "
        f"user_id={user.user_id}, username={user.username}, "
        f"first_name={user.first_name}, is_allowed={user.is_allowed}"
    )

if __name__ == "__main__":
    asyncio.run(main())