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
        return "assistant_identity"
    tokens = set(normalized.split())
    author_markers = {
        "muallif", "muallifi", "muallifning", "yaratuvchi", "asoschi",
        "biografiya", "tarjimai", "hayoti", "qiziqishlari", "motivatsiya",
        "salamat", "smaylov",
    }
    if tokens & author_markers or {"kim", "yaratgan"} <= tokens:
        return "author"
    if tokens & _PROJECT_MARKERS:
        return "project"
    if "toshbaqa" in tokens and tokens & _GENERAL_LIFESPAN_MARKERS:
        return "general_knowledge"
    return "project"


def is_author_overview_query(query: str) -> bool:
    """Detect a request for a whole person profile, not one biography facet."""
    normalized = normalize_query_for_intent(query)
    overview_phrases = (
        "haqida aytib ber", "haqida malumot", "tarjimai hol", "biografiya",
        "batafsil aytib", "tolqroq malumot", "tell me about", "who is",
    )
    return classify_query_intent(query) == "author" and any(
        phrase in normalized for phrase in overview_phrases
    )
