from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

MAX_CONVERSATION_TURNS = 12
MAX_TURN_CHARS = 1200
MAX_CONTEXT_CHARS = 4800

# Conservative markers: only clear anaphora / ellipsis trigger context injection.
_FOLLOW_UP_PATTERNS = (
    r"(?<!\w)(?:u|uning|unga|undan|bunga|buni|shuni|shu|o'sha|o‘sha|"
    r"oldingi|avvalgi|birinchi|ikkinchi|undan\s+oldin|yuqoridagi|"
    r"onasi|otasi|uning\s+onasi|uning\s+otasi|ular|ularning)(?!\w)",
    r"(?<!\w)(?:у|унинг|унга|ундан|бу|буни|шун|ўша|олдинги|аввалги|"
    r"биринчи|иккинчи|онаси|отаси|улар|уларнинг)(?!\w)",
    r"(?<!\w)(?:он|она|его|её|ему|ей|этот|эта|это|этом|тот|та|те|они|их)(?!\w)",
    r"(?<!\w)(?:he|she|it|they|him|her|his|its|them|this|that|those|"
    r"these|former|previous|first|second)(?!\w)|\bwhat about\b|\band then\b",
    r"(?<!\w)(?:ol|onı|onıń|oǵan|onnan|bul|bunı|sonı|sonıń|"
    r"aldıńǵı|birinshi|ekinshi|anasi|anası)(?!\w)",
    r"(?<!\w)(?:ол|оны|оның|оған|одан|бұл|мұны|соның|алдыңғы|бірінші|екінші)(?!\w)",
)
_FOLLOW_UP_RE = re.compile("|".join(f"(?:{pattern})" for pattern in _FOLLOW_UP_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class ConversationContext:
    turns: tuple[dict[str, str], ...]
    is_follow_up: bool
    context_text: str
    contextual_query: str


def normalize_conversation_history(history: Any) -> tuple[dict[str, str], ...]:
    """Accept only bounded user/assistant text turns; never persist them here."""
    if not isinstance(history, (list, tuple)):
        return ()
    normalized: list[dict[str, str]] = []
    for item in history[-MAX_CONVERSATION_TURNS:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().casefold()
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = content.strip()
        if not content or content.startswith("Xatolik:"):
            continue
        normalized.append({"role": role, "content": content[:MAX_TURN_CHARS]})
    return tuple(normalized[-MAX_CONVERSATION_TURNS:])


def is_context_dependent_query(query: str) -> bool:
    value = str(query or "").strip().casefold()
    if not value:
        return False
    return bool(_FOLLOW_UP_RE.search(value))


def build_conversation_context(query: str, history: Any) -> ConversationContext:
    """Resolve clear follow-ups using recent turns as context, never as evidence."""
    turns = normalize_conversation_history(history)
    current = str(query or "").strip()
    follow_up = bool(turns) and is_context_dependent_query(current)
    if not follow_up:
        return ConversationContext(
            turns=turns,
            is_follow_up=False,
            context_text="",
            contextual_query=current,
        )

    if re.search(r"(?<!\w)(?:birinchi|first|первый|бірінші|birinshi)(?!\w)", current, re.IGNORECASE):
        selected = turns[:2]
    elif re.search(r"(?<!\w)(?:ikkinchi|second|второй|екінші|ekinshi)(?!\w)", current, re.IGNORECASE):
        selected = turns[2:4]
    else:
        selected = turns[-4:]
    role_labels = {
        "user": "Foydalanuvchi",
        "assistant": "Oldingi AI javobi (ishonchsiz kontekst)",
    }
    lines = [f"{role_labels[item['role']]}: {item['content']}" for item in selected]
    context_text = "\n".join(lines)[:MAX_CONTEXT_CHARS]
    contextual_query = (
        current
        + "\n\nSuhbat konteksti (faqat ishora va mavzuni aniqlash uchun; fakt yoki dalil emas):\n"
        + context_text
    )
    return ConversationContext(
        turns=turns,
        is_follow_up=True,
        context_text=context_text,
        contextual_query=contextual_query,
    )
