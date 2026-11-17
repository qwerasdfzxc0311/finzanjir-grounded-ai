"""Conservative suffix normalization for lexical retrieval.

This is not a full morphological analyzer. It emits one high-confidence stem
for common Uzbek/Karakalpak/Kazakh/Russian inflections and preserves the
original token when no safe suffix rule applies.
"""
from __future__ import annotations

from functools import lru_cache

_UZBEK_KARAKALPAK_SUFFIXES = (
    "larining", "larning", "lariga", "laridan", "larida", "larini",
    "larimiz", "laringiz", "lari", "ları", "leri", "lardı", "lerdi",
    "nıń", "niń", "dıń", "diń", "lardan", "lerden", "dan", "den",
    "tan", "ten", "ning", "ga", "ge", "ka", "ke", "qa", "ni", "nı", "sini", "ini", "im", "ing", "ingiz",
    "miz", "si", "men", "ben", "pen", "ǵa", "lash",
)

_KAZAKH_SUFFIXES = (
    "лардың", "лердің", "дардың", "дердің", "тардың", "тердің",
    "лар", "лер", "дар", "дер", "тар", "тер", "ның", "нің",
    "дың", "дің", "ты", "ті", "ды", "ді", "ны", "ні", "ға", "ге",
    "қа", "ке", "дан", "ден", "тан", "тен",
    "мен", "бен", "пен", "лық", "лік", "дық", "дік", "тық", "тік",
)

_RUSSIAN_SUFFIXES = (
    "иями", "ями", "ами", "ого", "ему", "ыми", "ими", "ее", "ие",
    "ые", "ой", "ей", "ом", "ем", "ах", "ях", "ам", "ям", "ов",
    "ев", "ую", "юю", "ая", "яя", "ое", "ый", "ий",
)


@lru_cache(maxsize=65536)
def morphological_stem(token: str) -> str:
    """Return a conservative stem; do not strip one-letter endings."""
    value = str(token).casefold().strip()
    if not value:
        return value
    is_cyrillic = any("\u0400" <= char <= "\u04ff" for char in value)
    suffixes = _KAZAKH_SUFFIXES + _RUSSIAN_SUFFIXES if is_cyrillic else _UZBEK_KARAKALPAK_SUFFIXES
    for suffix in sorted(set(suffixes), key=lambda item: (-len(item), item)):
        if value.endswith(suffix) and len(value) - len(suffix) >= 3:
            stem = value[:-len(suffix)].rstrip("'")
            if len(stem) >= 3:
                return stem
    return value
