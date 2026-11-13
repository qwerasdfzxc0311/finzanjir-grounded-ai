from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[^\\W_]+", re.UNICODE)

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


def tokenize(value: str) -> tuple[str, ...]:
    normalized = (
        str(value).casefold()
        .replace("’", "'")
        .replace("ʻ", "'")
        .replace("ʼ", "'")
    )
    return tuple(token for token in _TOKEN_RE.findall(normalized) if token)


def meaningful_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token for token in tokenize(value)
        if token not in STOPWORDS and (len(token) > 1 or token == "ai")
    )
