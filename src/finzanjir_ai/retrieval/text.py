from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)

# Common function words across FINZANJIR's supported languages. This list is
# intentionally conservative: domain words are not removed as stopwords.
STOPWORDS = frozenset({
    # Uzbek
    "bu", "bilan", "bir", "bo", "bo'yicha", "deb", "degan", "ekan", "uchun",
    "va", "yoki", "qanday", "nima", "nega", "ning", "dan", "da", "ga", "u",
    "men", "sen", "siz", "ular", "shu", "o'sha", "haqida", "kerak", "qaysi",
    "qayerda", "qachon", "bormi", "bo'lsa", "bo'ladi", "edi", "emas", "bor",
    "yo'q", "kabi", "ham", "esa", "faqat", "juda", "ko'p", "uch", "ikki",
    "nima", "qil", "qiladi", "qilish", "qilgan", "qilmoqda",
    # English
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "how", "i", "if", "in", "is", "it", "its", "may", "might", "of", "on",
    "or", "our", "should", "that", "the", "their", "them", "there", "these",
    "this", "those", "to", "was", "we", "were", "what", "when", "where", "which",
    "who", "why", "will", "with", "would", "you", "your",
    # Russian
    "а", "без", "бы", "был", "была", "были", "быть", "в", "во", "для", "до",
    "его", "ее", "если", "же", "за", "и", "из", "или", "им", "как", "когда",
    "к", "ли", "мне", "мы", "на", "над", "не", "него", "нее", "нет", "но",
    "о", "об", "от", "по", "под", "при", "с", "со", "так", "то", "у", "что",
    "это", "я",
    # Kazakh / Karakalpak common function words
    "мен", "пен", "және", "үшін", "бұл", "сол", "ол", "не", "қалай",
    "да", "де", "ғана", "емес", "бар", "жоқ", "ушын", "бул", "олар",
})

# Script conversion is a search aid only. It never changes or writes canonical
# knowledge. These mappings target Uzbek/Kazakh/Karakalpak Cyrillic variants.
_CYRILLIC_TO_LATIN = {
    "а": "a", "ә": "a", "б": "b", "в": "v", "г": "g", "ғ": "g'",
    "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "қ": "q", "л": "l", "м": "m", "н": "n",
    "ң": "ng", "о": "o", "ө": "o", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ұ": "u", "ү": "u", "ў": "o'", "ф": "f",
    "х": "x", "ҳ": "h", "һ": "h", "і": "i", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}
_CENTRAL_ASIAN_CYRILLIC_MARKERS = frozenset("әіңғқөұүһўҳі")
_CENTRAL_ASIAN_CYRILLIC_WORDS = frozenset({
    "нима", "сенинг", "вазифанг", "мақсадинг", "ҳақида", "лойиҳа",
    "учун", "керак", "фуқаро", "молиявий", "қандай", "қанча",
})


def tokenize(value: str) -> tuple[str, ...]:
    normalized = (
        str(value).casefold()
        .replace("’", "'")
        .replace("ʻ", "'")
        .replace("ʼ", "'")
        .replace("`", "'")
    )
    return tuple(token for token in _TOKEN_RE.findall(normalized) if token)


def meaningful_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token for token in tokenize(value)
        if token not in STOPWORDS and (len(token) > 1 or token == "ai")
    )


def cyrillic_to_latin_search_variant(value: str) -> str | None:
    """Return a conservative Central-Asian Cyrillic-to-Latin search variant.

    Russian-only text is deliberately left alone to reduce noisy transliteration.
    """
    source = str(value).casefold()
    has_marker = any(char in _CENTRAL_ASIAN_CYRILLIC_MARKERS for char in source)
    has_known_word = bool(set(re.findall(r"[^\W\d_]+", source, flags=re.UNICODE)) & _CENTRAL_ASIAN_CYRILLIC_WORDS)
    if not (has_marker or has_known_word):
        return None
    # Kazakh uses ы as "y" in common Latin spellings (e.g. Қаржы -> qarjy).
    # Apply this only when Kazakh-specific markers are present.
    kazakh_markers = frozenset("әіңөұүі")
    is_kazakh = any(char in kazakh_markers for char in source)
    mapping = dict(_CYRILLIC_TO_LATIN)
    if is_kazakh:
        mapping.update({"ы": "y", "і": "i", "й": "y"})
    converted = "".join(mapping.get(char, char) for char in source)
    if is_kazakh:
        converted = re.sub(r"(?<![^\W\d_])және(?![^\W\d_])", "zhane", converted)
    converted = re.sub(r"\s+", " ", converted).strip()
    return converted if converted and converted != source else None


def query_script_variants(value: str) -> tuple[str, ...]:
    """Original query plus safe script variants, preserving original priority."""
    original = str(value).strip()
    if not original:
        return ()
    variants = [original]
    converted = cyrillic_to_latin_search_variant(original)
    if converted and converted.casefold() != original.casefold():
        variants.append(converted)
    return tuple(variants)
