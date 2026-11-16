import pytest

from finzanjir_ai.training.chat_format import (
    ChatMessage,
    IM_END,
    IM_SEP,
    IM_START,
    parse_chat,
    serialize_chat,
)


def test_chat_format_round_trips_multilingual_conversation():
    messages = (
        ChatMessage("system", "Answer from approved evidence."),
        ChatMessage("user", "Salom, FINZANJIR!"),
        ChatMessage("assistant", "Сәлем! Qaraqalpaqsha: Сәлеметсиз бе?"),
        ChatMessage("tool", "source_id: doc-17"),
    )
    assert parse_chat(serialize_chat(messages)) == messages


def test_reserved_markers_inside_content_are_escaped():
    content = f"Literal markers: {IM_START} {IM_SEP} {IM_END} and \\"
    messages = (ChatMessage("user", content),)
    assert parse_chat(serialize_chat(messages)) == messages


@pytest.mark.parametrize("role", ["developer", "system_prompt", "", "USER"])
def test_unknown_roles_are_rejected(role):
    with pytest.raises(ValueError, match="unsupported"):
        serialize_chat([ChatMessage(role, "text")])


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
