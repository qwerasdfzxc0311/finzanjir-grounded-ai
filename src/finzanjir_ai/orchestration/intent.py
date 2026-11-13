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
    tokens = re.findall(r"[^\W\d_]+", value, flags=re.UNICODE)
    return " ".join(_WORD_FIXES.get(token, token) for token in tokens)


_LANGUAGE_MARKERS = {
    "uz": {"nima", "haqida", "uchun", "kerak", "loyiha", "moliyaviy", "firibgarlik", "fuqaro", "maqsad", "tahlil", "xavf"},
    "ru": {"что", "такое", "проект", "расскажи", "объясни", "зачем", "финансовый", "мошенничество", "граждан"},
    "en": {"what", "is", "about", "tell", "explain", "project", "financial", "fraud", "citizen", "purpose"},
    "kk": {"жоба", "қаржы", "алаяқтық", "азамат", "туралы", "мақсат", "деген", "не", "zhoba", "qarzhy", "azamat", "turaly", "maqset", "ushin"},
    "kaa": {"joybar", "qarjı", "puqara", "haqqında", "haqqinda", "maqset", "qáwip", "degen", "ushın", "ushin", "maǵlıwmat"},
}


def detect_query_language(query: str) -> str:
    """Conservative language routing for the five supported project languages."""
    value = query.casefold()
    tokens = set(re.findall(r"[^\\W\\d_]+", value, flags=re.UNICODE))
    if re.search(r"[әіңғқөұүһ]", value):
        kaa_hits = len(tokens & _LANGUAGE_MARKERS["kaa"])
        kk_hits = len(tokens & _LANGUAGE_MARKERS["kk"])
        return "kaa" if kaa_hits > kk_hits else "kk"
    if re.search(r"[а-яё]", value):
        return "ru"
    scores = {language: len(tokens & markers) for language, markers in _LANGUAGE_MARKERS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "uz"


def is_project_overview_query(query: str) -> bool:
    """Keep broad 'what is FINZANJIR?' questions on the single mission record."""
    normalized = normalize_query_for_intent(query)
    tokens = set(normalized.split())
    if "finzanjir" not in tokens:
        return False
    phrases = (
        "nima", "haqida", "aytib ber", "tushuntir", "qanday loyiha",
        "что такое", "о проекте", "расскажи о", "объясни",
        "what is", "tell me about", "explain", "project overview",
        "деген не", "туралы", "айтып бер", "түсіндір", "жоба",
        "degen ne", "haqqinda", "aytip ber", "túsindir", "joybar",
    )
    return any(phrase in normalized for phrase in phrases)


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
    if is_project_overview_query(query):
        return "project_overview"
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
