from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


IM_START = "<|im_start|>"
IM_END = "<|im_end|>"
IM_SEP = "<|im_sep|>"
ALLOWED_ROLES = frozenset({"system", "user", "assistant", "tool"})


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


def _escape_content(content: str) -> str:
    # Escape the escape marker first, then reserved structural markers.
    return (
        content.replace("\\", "\\\\")
        .replace(IM_START, "<\\|im_start|>")
        .replace(IM_END, "<\\|im_end|>")
        .replace(IM_SEP, "<\\|im_sep|>")
    )


def _unescape_content(content: str) -> str:
    # Reverse only the escapes emitted by _escape_content.
    return (
        content.replace("<\\|im_start|>", IM_START)
        .replace("<\\|im_end|>", IM_END)
        .replace("<\\|im_sep|>", IM_SEP)
        .replace("\\\\", "\\")
    )


def serialize_chat(messages: Iterable[ChatMessage]) -> str:
    """Serialize a conversation to FINZANJIR Chat Format v1.

    This is a plain-text format proposal, not yet a tokenizer special-token
    implementation and not a training-data ingestion pipeline.
    """
    blocks: list[str] = []
    for message in messages:
        if message.role not in ALLOWED_ROLES:
            raise ValueError(f"unsupported chat role: {message.role!r}")
        if not isinstance(message.content, str):
            raise TypeError("message content must be text")
        if not message.content:
            raise ValueError("message content must not be empty")
        blocks.append(
            f"{IM_START}{message.role}{IM_SEP}\n"
            f"{_escape_content(message.content)}{IM_END}"
        )
    if not blocks:
        raise ValueError("conversation must contain at least one message")
    return "\n".join(blocks)


def parse_chat(serialized: str) -> tuple[ChatMessage, ...]:
    """Parse a complete v1 conversation; reject malformed or partial input."""
    if not isinstance(serialized, str) or not serialized:
        raise ValueError("serialized conversation must be non-empty text")

    messages: list[ChatMessage] = []
    cursor = 0
    while cursor < len(serialized):
        if serialized.startswith("\n", cursor):
            cursor += 1
            continue
        if not serialized.startswith(IM_START, cursor):
            raise ValueError(f"expected message start at offset {cursor}")
        role_start = cursor + len(IM_START)
        sep = serialized.find(IM_SEP, role_start)
        if sep < 0:
            raise ValueError("message header is missing separator")
        role = serialized[role_start:sep]
        if role not in ALLOWED_ROLES:
            raise ValueError(f"unsupported chat role: {role!r}")
        content_start = sep + len(IM_SEP) + 1
        if content_start > len(serialized) or serialized[sep + len(IM_SEP):content_start] != "\n":
            raise ValueError("message header must end with a newline")
        end = serialized.find(IM_END, content_start)
        if end < 0:
            raise ValueError("message is missing end marker")
        content = _unescape_content(serialized[content_start:end])
        if not content:
            raise ValueError("message content must not be empty")
        messages.append(ChatMessage(role=role, content=content))
        cursor = end + len(IM_END)
        if cursor < len(serialized) and serialized[cursor] != "\n":
            raise ValueError(f"unexpected data after message at offset {cursor}")
    if not messages:
        raise ValueError("conversation must contain at least one message")
    return tuple(messages)
