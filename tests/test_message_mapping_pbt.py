from datetime import datetime
from uuid import uuid4

from hypothesis import given, strategies as st

from app.db.models.message import ContentType, Direction, Message
from app.services.chat_service import build_history_payload, map_message_to_chat_payload


def _make_message(content: str, direction: Direction, ts: datetime) -> Message:
    return Message(
        message_id=str(uuid4()),
        bot_id="bot-1",
        chat_id=100,
        user_id=1,
        dedup_key=None,
        direction=direction,
        content_type=ContentType.TEXT,
        content=content,
        attachment_path=None,
        metadata_={},
        created_at=ts,
    )


@given(
    content=st.text(min_size=1).filter(lambda v: v.strip() != ""),
    is_outbound=st.booleans(),
)
def test_mapping_preserves_content_and_role(content: str, is_outbound: bool) -> None:
    direction = Direction.OUTBOUND if is_outbound else Direction.INBOUND
    row = _make_message(content, direction, datetime.utcnow())

    mapped = map_message_to_chat_payload(row)

    assert mapped is not None
    assert mapped["content"] == content.strip()
    assert mapped["role"] == ("assistant" if is_outbound else "user")


@given(
    empty_content=st.sampled_from(["", " ", "   ", "\n", "\t"]),
)
def test_empty_payload_filtered(empty_content: str) -> None:
    row = _make_message(empty_content, Direction.INBOUND, datetime.utcnow())
    assert map_message_to_chat_payload(row) is None


@given(
    rows=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=20),
            st.text(min_size=1).filter(lambda v: v.strip() != ""),
            st.booleans(),
        ),
        min_size=1,
        max_size=20,
        unique_by=lambda x: x[0],
    )
)
def test_build_history_payload_preserves_input_order(rows: list[tuple[int, str, bool]]) -> None:
    sorted_rows = sorted(rows, key=lambda x: x[0])
    messages = [
        _make_message(
            content=content,
            direction=Direction.OUTBOUND if is_outbound else Direction.INBOUND,
            ts=datetime.utcfromtimestamp(order),
        )
        for order, content, is_outbound in sorted_rows
    ]

    payload = build_history_payload(messages)
    assert len(payload) == len(messages)
    assert [p["content"] for p in payload] == [m.content.strip() for m in messages]
