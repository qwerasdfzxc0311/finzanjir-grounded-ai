from __future__ import annotations

import re

from finzanjir_ai.orchestration.intent import detect_query_language
from .text import query_script_variants


# Conservative domain vocabulary bridge. It creates search hints only; translated
# words are never evidence and never alter the user's original question.
_TRANSLATION_PATTERNS: dict[str, tuple[tuple[str, str], ...]] = {
    "ru": (
        (r"\bмошеннич\w*\b", "firibgarlik"),
        (r"\bфинансов\w*\b", "moliyaviy"),
        (r"\bбезопасност\w*\b", "xavfsizlik"),
        (r"\bзащит\w*\b", "himoya"),
        (r"\bбан\w*\b", "bank"),
        (r"\bплатеж\w*\b", "to'lov"),
        (r"\bкарт\w*\b", "karta"),
        (r"\bсистем\w*\b", "tizim"),
        (r"\bархитектур\w*\b", "arxitektura"),
        (r"\bструктур\w*\b", "tuzilma"),
        (r"\bданн\w*\b", "ma'lumot"),
        (r"\bсигнал\w*\b", "signal"),
        (r"\bрис\w*\b", "risk"),
        (r"\bрешен\w*\b", "qaror"),
        (r"\bуполномоч\w*\b", "vakolatli"),
        (r"\bпроект\w*\b", "loyiha"),
        (r"\bцел\w*\b", "maqsad"),
        (r"\bпроцесс\w*\b", "jarayon"),
        (r"\bэтап\w*\b", "bosqich"),
        (r"\bтранзакц\w*\b", "tranzaksiya"),
        (r"\bполучател\w*\b", "qabul qiluvchi"),
        (r"\bотлича\w*\b", "farq"),
        (r"\bразниц\w*\b", "farq"),
        (r"\bпохож\w*\b", "o'xshash"),
        (r"\bстра\w*\b", "davlat"),
        (r"\bданные\b", "ma'lumot"),
    ),
    "en": (
        (r"\bfraud\w*\b", "firibgarlik"),
        (r"\bfinancial\w*\b", "moliyaviy"),
        (r"\bsecurity\b", "xavfsizlik"),
        (r"\bprotect\w*\b", "himoya"),
        (r"\bprevention\b", "oldini olish"),
        (r"\bbank\w*\b", "bank"),
        (r"\bpayment\w*\b", "to'lov"),
        (r"\bcard\w*\b", "karta"),
        (r"\bsystem\w*\b", "tizim"),
        (r"\barchitectur\w*\b", "arxitektura"),
        (r"\bstructure\b", "tuzilma"),
        (r"\bdata\b", "ma'lumot"),
        (r"\bsignal\w*\b", "signal"),
        (r"\brisk\b", "risk"),
        (r"\bdecision\w*\b", "qaror"),
        (r"\bauthori[sz]ed\b", "vakolatli"),
        (r"\bproject\w*\b", "loyiha"),
        (r"\bpurpose\b", "maqsad"),
        (r"\bgoal\b", "maqsad"),
        (r"\bprocess\w*\b", "jarayon"),
        (r"\bstage\w*\b", "bosqich"),
        (r"\btransaction\w*\b", "tranzaksiya"),
        (r"\brecipient\w*\b", "qabul qiluvchi"),
        (r"\bdiffer\w*\b", "farq"),
        (r"\bsimilar\b", "o'xshash"),
        (r"\bcountr\w*\b", "davlat"),
        (r"\bcase\b", "case"),
        (r"\breview\b", "ko'rib chiqish"),
    ),
    "kk": (
        (r"\балаяқтық\w*\b", "firibgarlik"),
        (r"\bқарж\w*\b", "moliyaviy"),
        (r"\bқауіпсіз\w*\b", "xavfsizlik"),
        (r"\bқорға\w*\b", "himoya"),
        (r"\bбанк\w*\b", "bank"),
        (r"\bтөлем\w*\b", "to'lov"),
        (r"\bкарт\w*\b", "karta"),
        (r"\bжүй\w*\b", "tizim"),
        (r"\bархитектур\w*\b", "arxitektura"),
        (r"\bқұрылым\w*\b", "tuzilma"),
        (r"\bдерек\w*\b", "ma'lumot"),
        (r"\bбелгі\w*\b", "signal"),
        (r"\bтәуекел\w*\b", "risk"),
        (r"\bшешім\w*\b", "qaror"),
        (r"\bуәкілет\w*\b", "vakolatli"),
        (r"\bжоба\w*\b", "loyiha"),
        (r"\bмақсат\w*\b", "maqsad"),
        (r"\bпроцесс\w*\b", "jarayon"),
        (r"\bкезең\w*\b", "bosqich"),
        (r"\bтранзакц\w*\b", "tranzaksiya"),
        (r"\bалушы\w*\b", "qabul qiluvchi"),
        (r"\bерекшелен\w*\b", "farq"),
        (r"\bайырмаш\w*\b", "farq"),
        (r"\bұқсас\w*\b", "o'xshash"),
        (r"\bелдер\w*\b", "davlat"),
    ),
    "kaa": (
        (r"\bqáwipsizlik\w*\b", "xavfsizlik"),
        (r"\bqáwip\w*\b", "risk"),
        (r"\bqorǵaw\w*\b", "himoya"),
        (r"\bbank\w*\b", "bank"),
        (r"\btólem\w*\b", "to'lov"),
        (r"\bkarta\w*\b", "karta"),
        (r"\bsistema\w*\b", "tizim"),
        (r"\barxitektura\w*\b", "arxitektura"),
        (r"\bmaǵlıwmat\w*\b", "ma'lumot"),
        (r"\bsignal\w*\b", "signal"),
        (r"\bsheshim\w*\b", "qaror"),
        (r"\bjoybar\w*\b", "loyiha"),
        (r"\bmaqset\w*\b", "maqsad"),
        (r"\bbasqısh\w*\b", "bosqich"),
        (r"\btranzakciya\w*\b", "tranzaksiya"),
        (r"\balıwshı\w*\b", "qabul qiluvchi"),
        (r"\bparıql\w*\b", "farq"),
        (r"\bpariq\w*\b", "farq"),
        (r"\busas\w*\b", "o'xshash"),
        (r"\bsalıstır\w*\b", "taqqoslash"),
        (r"\bbasqa\b", "boshqa"),
        (r"\bmámleket\w*\b", "davlat"),
    ),
}


def translate_search_hint(query: str, language: str | None = None) -> tuple[str | None, int]:
    """Return a low-priority Uzbek lexical hint and number of mapped terms."""
    lang = language or detect_query_language(query)
    patterns = _TRANSLATION_PATTERNS.get(lang)
    if not patterns:
        return None, 0

    hint = str(query).casefold()
    mapped = 0
    for pattern, replacement in patterns:
        hint, count = re.subn(pattern, replacement, hint, flags=re.UNICODE)
        mapped += count

    # Require at least two mapped terms to avoid noisy one-word expansions.
    if mapped < 2 or hint == str(query).casefold():
        return None, mapped
    return " ".join(hint.split()), mapped


def cross_lingual_query_variants(query: str) -> tuple[str, ...]:
    """Original + script hint + low-priority Uzbek concept-language hint."""
    variants = list(query_script_variants(query))
    hint, _ = translate_search_hint(query)
    if hint and all(hint.casefold() != item.casefold() for item in variants):
        variants.append(hint)
    return tuple(variants)
