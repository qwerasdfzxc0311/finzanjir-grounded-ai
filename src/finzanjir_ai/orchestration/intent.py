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
    "uz": {"nima", "haqida", "uchun", "kerak", "loyiha", "moliyaviy", "firibgarlik", "fuqaro", "maqsad", "tahlil", "xavf", "va", "muhim", "bank", "karta", "kartani", "kartasini", "bloklay", "bloklashi", "oladi", "oladimi", "qanday", "qila", "mumkin", "emas", "qonuniy", "ozi", "shubhali", "nimani", "anglatadi", "fuqaroning", "aybdorligini", "isbotlaydimi", "banklarga", "qarshimi", "ochiladi", "qatlamli", "arxitekturasi", "toshvaqa", "qansha", "umir", "koradi", "нима", "лойиҳа", "учун", "керак", "мақсад", "фуқаро", "молиявий", "фарқ", "фарқи", "ўхшаш", "бошқа", "давлат", "нимаси", "қилади", "таққослаш"},
    "ru": {"что", "такое", "проект", "расскажи", "объясни", "зачем", "финансовый", "мошенничество", "граждан"},
    "en": {"what", "is", "about", "tell", "explain", "project", "financial", "fraud", "citizen", "purpose", "the", "and", "why", "how", "does", "can", "card", "bank", "false", "positive", "negative", "important", "mean", "means", "risk", "signal", "case", "escalation", "requires", "evidence", "threshold", "assessment", "supporting", "transaction", "suspicious", "legitimate", "account", "money", "flow", "data", "privacy", "system", "help", "protect", "funds", "decision", "human", "review"},
    "kk": {"жоба", "қаржы", "алаяқтық", "азамат", "туралы", "мақсат", "деген", "не", "zhoba", "qarzhy", "azamat", "turaly", "maqset", "ushin"},
    "kaa": {"joybar", "qarjı", "puqara", "haqqında", "haqqinda", "maqset", "qáwip", "degen", "ushın", "ushin", "maǵlıwmat", "joybar", "avtor", "avtordıń", "jaratqan", "мақсет", "пуқара", "ҳаққында", "қаўип"},
}


def detect_query_language(query: str) -> str:
    """Conservative language routing for the five supported project languages."""
    value = query.casefold()
    tokens = set(re.findall(r"[^\W\d_]+", value, flags=re.UNICODE))
    kaa_hits = len(tokens & _LANGUAGE_MARKERS["kaa"])
    kk_hits = len(tokens & _LANGUAGE_MARKERS["kk"])
    # Several Uzbek-Cyrillic words also contain letters used in Kazakh.
    # Resolve a strong Uzbek lexical signature before generic script detection.
    uz_cyrillic_hits = len(tokens & {
        "бошқа", "давлат", "фарқ", "фарқи", "ўхшаш",
        "нимаси", "таққослаш", "лойиҳа", "молиявий", "фуқаро",
    })
    if uz_cyrillic_hits >= 2:
        return "uz"
    if re.search(r"[әіңғқөұүһі]", value):
        return "kaa" if kaa_hits > kk_hits else "kk"
    uzbek_phrases = (
        "bank kartasini", "bank kartani", "kartasini o'zi", "kartani o'zi",
        "o'zi bloklay", "o'zi bloklay oladimi", "bloklay oladimi",
        "bloklash mumkinmi", "bloklaydimi", "qila oladimi",
    )
    if (
        re.search(r"[ўҳ]", value)
        or tokens & {"нима", "лойиҳа", "учун", "керак", "мақсад", "фуқаро", "молиявий"}
        or sum(token in tokens for token in {"bank", "karta", "kartasini", "kartani", "bloklay", "oladimi", "o'zi"}) >= 2
        or any(phrase in value for phrase in uzbek_phrases)
    ):
        return "uz"
    if kaa_hits > kk_hits and kaa_hits:
        return "kaa"
    if kk_hits:
        return "kk"
    if re.search(r"[а-яё]", value):
        return "ru"
    scores = {language: len(tokens & markers) for language, markers in _LANGUAGE_MARKERS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "uz"


def is_project_overview_query(query: str) -> bool:
    """Keep broad 'what is FINZANJIR?' questions on the single mission record."""
    normalized = normalize_query_for_intent(query)
    tokens = set(normalized.split())
    if not ({"finzanjir", "финзанжир"} & tokens):
        return False
    detail_markers = {
        "bank", "банк", "karta", "kartani", "карта", "блок", "blok", "signal",
        "сигнал", "risk", "риск", "case", "fuqaro", "граждан", "murojaat",
        "ma'lumot", "malumot", "данные", "data", "law", "qonun", "закон",
        "detect", "aniqlash", "aniqlaydi", "qanday ishlaydi", "how",
    }
    if tokens & detail_markers:
        return False
    exact_forms = {
        "finzanjir nima", "finzanjir nima va nima uchun kerak", "finzanjir nima uchun kerak",
        "finzanjir haqida", "finzanjir haqida aytib ber", "finzanjir haqida qisqacha aytib ber",
        "finzanjirning maqsadi", "finzanjir qanday loyiha",
        "финзанжир нима", "финзанжир ҳақида", "финзанжир ҳақида айтып бер",
        "что такое finzanjir", "расскажи о finzanjir", "о finzanjir",
        "what is finzanjir", "tell me about finzanjir", "about finzanjir",
        "finzanjir деген не", "finzanjir туралы", "finzanjir қандай жоба",
        "finzanjir degen ne", "finzanjir haqqında", "finzanjir joybar",
    }
    return normalized in exact_forms


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
        "salamat", "smaylov", "author", "автор", "avtor", "avtordıń",
    }
    if tokens & author_markers or {"kim", "yaratgan"} <= tokens:
        return "author"
    if (
        "finzanjir" in tokens
        and any(phrase in normalized for phrase in ("qanday yaralgan", "qanday boshlangan", "qayerdan boshlangan", "kelib chiqishi"))
    ):
        return "author"
    if (
        "finzanjir" in tokens
        and any(phrase in normalized for phrase in ("nima uchun yaratilgan", "nima sababdan yaratilgan", "nima maqsadda yaratilgan"))
    ):
        return "author"
    if (
        any(token.startswith("finzanjir") for token in tokens)
        and any(phrase in normalized for phrase in (
            "maqsadi nima", "asosiy maqsadi",
            "nima uchun yarat", "nima sababdan yarat", "nima maqsadda yarat",
            "yaratilish sababi", "yaratilishidan maqsad", "yaratishdan maqsad",
            "yaratishdan ko zlangan maqsad", "ne ushin jaratqan", "ne ushın jaratqan",
            "why was finzanjir created", "why create finzanjir",
            "purpose of finzanjir", "почему создан finzanjir", "почему был создан finzanjir",
            "зачем был создан finzanjir", "для чего был создан finzanjir",
            "для чего finzanjir", "зачем создан finzanjir",
        ))
    ):
        return "author"
    if "kiber qalqon" in normalized and any(
        marker in normalized for marker in ("qanday", "paydo", "boshlanish", "finzanjir")
    ):
        return "author"
    if any(term in tokens for term in ("atmos", "sinbad")) and "finzanjir" in tokens:
        return "author"
    if is_project_overview_query(query):
        return "project_overview"
    if tokens & _PROJECT_MARKERS:
        return "project"
    if "toshbaqa" in tokens and tokens & _GENERAL_LIFESPAN_MARKERS:
        return "general_knowledge"
    return "project"





def is_bank_authority_query(query: str) -> bool:
    """Recognize direct questions about whether FINZANJIR can block or override cards."""
    normalized = normalize_query_for_intent(query)
    tokens = set(normalized.split())
    has_project = bool(tokens & {"finzanjir", "финзанжир"})
    card_terms = {
        "karta", "kartani", "kartasini", "карта", "карту", "картаны",
        "card", "cards", "kartasın", "bank",
    }
    action_terms = {
        "bloklay", "bloklashi", "bloklash", "bloklaydi",
        "блокировать", "заблокировать", "блоктай", "бұғаттай",
        "block", "blocks", "blocking", "freeze", "freezes",
    }
    return has_project and bool(tokens & card_terms) and bool(tokens & action_terms)


def is_signal_guilt_query(query: str) -> bool:
    """Recognize questions asking whether a risk signal proves a person's guilt."""
    normalized = normalize_query_for_intent(query)
    tokens = set(normalized.split())
    signal_terms = {"signal", "сигнал", "qáwip", "belgi"}
    guilt_terms = {
        "aybdor", "aybdorligini", "aybdorlik", "isbot", "isbotlaydimi",
        "guilt", "prove", "proves", "винов", "доказ", "кінә", "айып",
    }
    return bool(tokens & signal_terms) and bool(
        tokens & guilt_terms or any(term in normalized for term in ("aybdorligini isbot", "prove guilt", "доказательство вины"))
    )


def is_case_purpose_query(query: str) -> bool:
    """Recognize a request for the purpose of opening a Case."""
    normalized = normalize_query_for_intent(query)
    tokens = set(normalized.split())
    return "case" in tokens and any(
        marker in normalized
        for marker in ("nima uchun", "nega", "maqsad", "ochil", "why", "для чего", "зачем")
    )


def is_fraud_graph_definition_query(query: str) -> bool:
    """Recognize direct Fraud Graph explanations without matching unrelated questions."""
    normalized = normalize_query_for_intent(query)
    patterns = (
        r"\b(?:fraud graph|fraudgraph|firibgarlik grafigi)\s+(?:nima\b|nima degani\b|nimani anglatadi\b|qanday ishlaydi\b|ta'rif\b|tarif\b|tushuntir\b|izohla\b)",
        r"\bwhat is (?:the )?fraud graph\b",
        r"\bwhat does (?:the )?fraud graph mean\b",
        r"\b(?:define|explain) (?:the )?fraud graph\b",
        r"\bhow does (?:the )?fraud graph work\b",
        r"\bчто такое fraud graph\b",
        r"\bчто означает fraud graph\b",
        r"\bобъясни fraud graph\b",
        r"\bfraud graph (?:не|нені білдіреді|қалай жұмыс істейді|degen ne)\b",
        r"\bfraud graph qanday isleydi\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def is_c_model_query(query: str) -> bool:
    normalized = normalize_query_for_intent(query)
    return any(marker in normalized for marker in ("c modeli", "c model", "model c"))


def is_sixteen_layer_query(query: str) -> bool:
    raw = " ".join(str(query).casefold().replace("’", "'").split())
    normalized = normalize_query_for_intent(query)
    return (
        ("16" in raw and ("qatlam" in raw or "layer" in raw or "қабат" in raw))
        or any(marker in raw for marker in (
            "o'n olti qatlam", "on olti qatlam", "sixteen layer",
        ))
        or any(marker in normalized for marker in ("16 qatlam", "16 layer", "16 қабат", "16 қабатты"))
    )


def is_author_overview_query(query: str) -> bool:
    """Detect a request for a whole person profile, not one biography facet."""
    normalized = normalize_query_for_intent(query)
    overview_phrases = (
        "haqida aytib ber", "haqida malumot", "tarjimai hol", "biografiya",
        "batafsil aytib", "tolqroq malumot", "tell me about", "who is",
    )
    family_facet_markers = (
        "onasi", "onasining", "ona haqida", "otasi", "singlisi",
        "mother", "father", "sister", "мать", "отец", "сестра",
        "анасы", "атасы",
    )
    if any(marker in normalized for marker in family_facet_markers):
        return False
    return classify_query_intent(query) == "author" and any(
        phrase in normalized for phrase in overview_phrases
    )


def is_author_motivation_query(query: str) -> bool:
    """Recognize clear questions about why FINZANJIR was created, not any author mention."""
    normalized = normalize_query_for_intent(query)
    if not normalized:
        return False
    tokens = set(normalized.split())
    author_ref = bool(tokens & {
        "muallif", "muallifi", "muallifning", "yaratuvchi", "asoschi",
        "author", "автор", "avtor", "avtordıń",
    })
    project_ref = any(token.startswith("finzanjir") for token in tokens) or bool(tokens & {"loyiha", "project"})
    has_creation_verb = any(token.startswith((
        "yarat", "jarat", "create", "creat", "созда", "жаса",
    )) for token in tokens)
    reason_markers = (
        "nima uchun", "nega", "nima sabab", "qanday sabab",
        "maqsad", "maqset", "sebep", "why", "reason", "purpose",
        "почему", "зачем", "для чего", "причина", "цель",
        "не үшін", "не себеп", "мақсат", "себеп", "ne ushin", "ne ushın",
    )
    explicit_purpose_markers = (
        "maqsadi nima", "asosiy maqsadi",
        "yaratilish sababi", "yaratilishidan maqsad",
        "yaratishdan maqsad", "yaratishdan maqsadi",
        "yaratishdan ko zlangan maqsad",
        "why was finzanjir created", "why create finzanjir",
        "purpose of finzanjir", "почему создан finzanjir",
        "почему был создан finzanjir", "зачем был создан finzanjir",
        "для чего был создан finzanjir", "для чего finzanjir",
        "зачем создан finzanjir",
    )
    if author_ref and has_creation_verb and any(marker in normalized for marker in reason_markers):
        return True
    if project_ref and (
        any(marker in normalized for marker in explicit_purpose_markers)
        or (has_creation_verb and any(marker in normalized for marker in reason_markers))
    ):
        return True
    return False


def is_author_motivation_follow_up(query: str) -> bool:
    """Recognize explicit anaphoric follow-ups asking why the author created the project."""
    normalized = normalize_query_for_intent(query)
    return any(marker in normalized for marker in (
        "u nima sababdan yarat", "u nima uchun yarat",
        "u nima maqsadda yarat", "nima sababdan yaratgan",
        "nega yaratgan", "nima maqsadda yaratgan",
        "why did he create", "why did they create",
        "why was it created", "зачем он создал",
        "почему он создал", "не себептен құрды",
    ))
