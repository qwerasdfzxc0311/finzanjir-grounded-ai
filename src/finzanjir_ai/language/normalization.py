"""Local, conservative multilingual text normalization.

This module preserves the user's original text at the API boundary. It produces
an additional normalized view for matching; it does not translate or claim to
understand meaning by itself.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from collections.abc import Mapping


_APOSTROPHES = str.maketrans({
    "ʻ": "'", "ʼ": "'", "’": "'", "‘": "'", "`": "'",
    "＇": "'", "´": "'",
})

# Only high-confidence, author-reviewable corrections belong here. Keep this
# list deliberately small: aggressive autocorrection can change a question.
_DEFAULT_ALIASES = {
    "toshvaqa": "toshbaqa",
    "qansha": "qancha",
    "umir": "umr",
    "koradi": "ko'radi",
    "ushun": "uchun",
    "qaraqalpaq": "qoraqalpoq",
    "qaraqalpaqsha": "qoraqalpoqcha",
}


def normalize_multilingual_text(
    text: str,
    *,
    aliases: Mapping[str, str] | None = None,
) -> str:
    """Return a matching-friendly normalized view without changing source text."""
    value = unicodedata.normalize("NFKC", str(text)).casefold().translate(_APOSTROPHES)
    value = value.replace("ё", "е")
    value = re.sub(r"[​-‏‪-‮﻿]", "", value)
    value = re.sub(r"[_/\\|]+", " ", value)
    value = re.sub(r"[^\w'\s]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    corrections = dict(_DEFAULT_ALIASES)
    if aliases:
        corrections.update({
            str(source).casefold(): str(target).casefold()
            for source, target in aliases.items()
            if str(source).strip() and str(target).strip()
        })
    tokens = [corrections.get(token, token) for token in value.split()]
    return " ".join(tokens)


@lru_cache(maxsize=32768)
def character_ngrams(text: str, *, min_n: int = 2, max_n: int = 4) -> tuple[str, ...]:
    """Create deterministic character n-grams for typo-tolerant local matching."""
    if min_n < 1 or max_n < min_n or max_n > 8:
        raise ValueError("n-gram bounds must satisfy 1 <= min_n <= max_n <= 8")
    value = f" {normalize_multilingual_text(text)} "
    grams = {
        value[index:index + size]
        for size in range(min_n, max_n + 1)
        for index in range(max(0, len(value) - size + 1))
    }
    return tuple(sorted(grams))
