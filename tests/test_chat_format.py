import pytest

from finzanjir_ai.training.chat_format import (
    ChatMessage,
    IM_END,
    IM_SEP,
    IM_START,
    IM_TURN_END,
    parse_chat,
    serialize_chat,
)


def test_chat_format_round_trips_multilingual_conversation():
    messages = (
        ChatMessage("system", "Answer from approved evidence."),
        ChatMessage("user", "Salom, FINZANJIR!"),
        ChatMessage("assistant", "Сәлем! Qaraqalpaqsha: Сәлеметсиз бе?", end_of_turn=True),
        ChatMessage("tool", "source_id: doc-17"),
    )
    assert parse_chat(serialize_chat(messages)) == messages


def test_reserved_markers_inside_content_are_escaped():
    content = f"Literal markers: {IM_START} {IM_SEP} {IM_END} {IM_TURN_END} and \\"
    messages = (ChatMessage("user", content),)
    assert parse_chat(serialize_chat(messages)) == messages


@pytest.mark.parametrize("role", ["developer", "system_prompt", "", "USER"])
def test_unknown_roles_are_rejected(role):
    with pytest.raises(ValueError, match="unsupported"):
        serialize_chat([ChatMessage(role, "text")])


def test_only_assistant_can_end_a_turn():
    with pytest.raises(ValueError, match="only assistant"):
        serialize_chat([ChatMessage("user", "hello", end_of_turn=True)])
    with pytest.raises(ValueError, match="only assistant"):
        parse_chat(f"{IM_START}tool{IM_SEP}\\nresult{IM_TURN_END}")


def test_assistant_turn_end_round_trips_separately_from_message_end():
    messages = (
        ChatMessage("assistant", "Thinking or tool handoff.", end_of_turn=False),
        ChatMessage("tool", "Tool result."),
        ChatMessage("assistant", "Final answer.", end_of_turn=True),
    )
    serialized = serialize_chat(messages)
    assert serialized.count(IM_END) == 2
    assert serialized.count(IM_TURN_END) == 1
    assert parse_chat(serialized) == messages


def test_empty_conversation_and_empty_message_are_rejected():
    with pytest.raises(ValueError, match="at least one"):
        serialize_chat([])
    with pytest.raises(ValueError, match="must not be empty"):
        serialize_chat([ChatMessage("user", "")])


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not a message",
        f"{IM_START}user{IM_SEP}\nhello",
        f"{IM_START}unknown{IM_SEP}\nhello{IM_END}",
        f"{IM_START}user{IM_SEP}hello{IM_END}",
    ],
)
def test_malformed_conversations_are_rejected(raw):
    with pytest.raises(ValueError):
        parse_chat(raw)
