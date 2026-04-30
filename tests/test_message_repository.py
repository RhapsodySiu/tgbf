async def test_scoped_read_and_dedup(test_session, bot_repo, user_repo, message_repo) -> None:
    bot_id = "bot-001"
    user_id = 42
    chat_id = 777

    db = test_session

    await bot_repo.create(
        db,
        {
            "bot_id": bot_id,
            "display_name": "Test Bot",
            "telegram_token": "token",
            "persona_config": {},
            "is_active": True,
        },
    )

    await user_repo.create(
        db,
        {
            "user_id": user_id,
            "username": "alice",
            "first_name": "Alice",
            "is_allowed": True,
            "invite_token": None,
        },
    )

    first = await message_repo.save_inbound(
        db,
        bot_id=bot_id,
        chat_id=chat_id,
        user_id=user_id,
        content="hello",
        dedup_key="dup-1",
    )

    duplicate = await message_repo.save_inbound(
        db,
        bot_id=bot_id,
        chat_id=chat_id,
        user_id=user_id,
        content="hello",
        dedup_key="dup-1",
    )

    assert first.message_id == duplicate.message_id

    await message_repo.save_outbound(
        db,
        bot_id=bot_id,
        chat_id=chat_id,
        user_id=user_id,
        content="world",
    )

    rows = await message_repo.get_recent_for_context(
        db,
        bot_id=bot_id,
        chat_id=chat_id,
        user_id=user_id,
        limit=20,
    )

    assert len(rows) == 2
    assert {row.content for row in rows} == {"hello", "world"}

    other_chat_rows = await message_repo.get_recent_for_context(
        db,
        bot_id=bot_id,
        chat_id=999,
        user_id=user_id,
        limit=20,
    )
    assert other_chat_rows == []
