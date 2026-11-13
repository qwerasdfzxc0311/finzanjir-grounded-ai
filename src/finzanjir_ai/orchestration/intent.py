from __future__ import annotations

import re

_WORD_FIXES = {
    "toshvaqa": "toshbaqa",
    "qansha": "qancha",
    "umir": "umr",
    "koradi": "ko'radi",
}
_PROJECT_MARKERS = {
    "finzanjir", "loyiha", "bank", "firibgarlik", "moliyaviy", "karta",
    "hisob", "signal", "risk", "case", "prototip", "pilot", "fuqaro",
    "tolov", "himoya", "zanjir", "tizim", "hujjat",
}
_GENERAL_LIFESPAN_MARKERS = {"umr", "yashaydi", "yil", "qancha", "necha", "lifespan", "live", "years", "long"}
_ASSISTANT_IDENTITY_PATTERNS = (
    r"\bsening\s+maqsad(ing)?\b",
    r"\bsening\s+vazifa(ng)?\b",
    r"\bsen\s+kimsan\b",
    r"\bsen\s+nima\s+qila\s+olasan\b",
    r"\bwhat\s+is\s+your\s+purpose\b",
)

def normalize_query_for_intent(query: str) -> str:
    value = query.casefold().replace("ʻ", "'").replace("’", "'")
    tokens = re.findall(r"[a-zа-яёқғҳў]+", value)
    return " ".join(_WORD_FIXES.get(token, token) for token in tokens)

def classify_query_intent(query: str) -> str:
    """Conservative routing: only clear general-knowledge patterns leave project RAG."""
    normalized = normalize_query_for_intent(query)
    if not normalized:
        return "project"
    if any(re.search(pattern, normalized) for pattern in _ASSISTANT_IDENTITY_PATTERNS):
        return "project"
    tokens = set(normalized.split())
    if tokens & _PROJECT_MARKERS:
        return "project"
    author_markers = {"muallif", "muallifi", "yaratuvchi", "asoschi", "muallifning", "biografiya", "tarjimai", "hayoti", "qiziqishlari"}
    if tokens & author_markers or {"kim", "yaratgan"} <= tokens:
        return "author"
    if "toshbaqa" in tokens and tokens & _GENERAL_LIFESPAN_MARKERS:
        return "general_knowledge"
    return "project"
