from contextvars import ContextVar


_bot_id_ctx: ContextVar[str | None] = ContextVar("bot_id", default=None)
_chat_id_ctx: ContextVar[int | None] = ContextVar("chat_id", default=None)
_user_id_ctx: ContextVar[int | None] = ContextVar("user_id", default=None)


def bind_log_context(*, bot_id: str, chat_id: int | None, user_id: int) -> None:
    _bot_id_ctx.set(bot_id)
    _chat_id_ctx.set(chat_id)
    _user_id_ctx.set(user_id)


def clear_log_context() -> None:
    _bot_id_ctx.set(None)
    _chat_id_ctx.set(None)
    _user_id_ctx.set(None)


def get_log_context() -> dict:
    context = {
        "bot_id": _bot_id_ctx.get(),
        "chat_id": _chat_id_ctx.get(),
        "user_id": _user_id_ctx.get(),
    }
    return {k: v for k, v in context.items() if v is not None}
