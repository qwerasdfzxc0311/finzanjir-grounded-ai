from __future__ import annotations

import re
import unicodedata


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = (
        text.replace("ʻ", "'")
        .replace("‘", "'")
        .replace("’", "'")
        .replace("ʼ", "'")
        .replace("`", "'")
    )
    text = re.sub(r"[^\w']+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


_PATTERNS = {
    "comparison": (
        # Uzbek Latin / Cyrillic
        r"\bfarq\w*\b", r"\btaqqos\w*\b", r"\bqiyos\w*\b",
        r"\bo'xshash\w*\b", r"\bboshqa davlat\w*\b",
        r"\bnimasi bilan\b", r"\bkuchliroq\b",
        r"\bфарқ\w*\b", r"\bтаққос\w*\b", r"\bўхшаш\w*\b",
        r"\bнимаси билан\b", r"\bбошқа давлат\w*\b",
        # Russian
        r"\bчем отличается\b", r"\bотлича\w*\b", r"\bразниц\w*\b",
        r"\bсравн\w*\b", r"\bпохож\w*\b", r"\bсильнее\b",
        # English
        r"\bdiffer\w*\b", r"\bcompar\w*\b", r"\bsimilar\w*\b",
        r"\bversus\b", r"\bvs\b", r"\bstronger\b",
        # Kazakh / Karakalpak
        r"\байырмаш\w*\b", r"\bсалыстыр\w*\b", r"\bұқсас\w*\b",
        r"\bерекшел\w*\b", r"\bparıql\w*\b", r"\bpariq\w*\b",
        r"\bsalıstır\w*\b", r"\busas\w*\b",
    ),
    "status_audit": (
        # Uzbek
        r"\bhozir\b", r"\bprototip\w*\b", r"\breja\w*\b",
        r"\btaklif\w*\b", r"\bmavjud\w*\b", r"\bjoriy\b",
        r"\bqaysi .*\bbor\b", r"\bqaysi .*\byo'q\b",
        # Uzbek Cyrillic
        r"\bҳозир\b", r"\bпрототип\w*\b", r"\bрежа\w*\b",
        r"\bтаклиф\w*\b", r"\bмавжуд\w*\b",
        # Russian
        r"\bсейчас\b", r"\bпрототип\w*\b", r"\bплан\w*\b",
        r"\bреализован\w*\b", r"\bвнедрен\w*\b", r"\bсуществу\w*\b",
        # English
        r"\bcurrently\b", r"\bcurrent\b", r"\bprototype\w*\b",
        r"\bplanned\b", r"\bplan\w*\b", r"\bimplemented\b",
        r"\bdeployed\b", r"\broadmap\b", r"\bexists\b",
        # Kazakh / Karakalpak
        r"\bқазір\b", r"\bжоспар\w*\b", r"\bенгізіл\w*\b",
        r"\bházir\b", r"\breje\b", r"\bprototip\w*\b",
    ),
    "architecture": (
        # Uzbek
        r"\barxitektur\w*\b", r"\btuzil\w*\b", r"\btarkib\w*\b",
        r"\bkomponent\w*\b", r"\bqatlam\w*\b", r"\bma'lumot .* qayerdan\b",
        # Uzbek Cyrillic
        r"\bархитектур\w*\b", r"\bтузил\w*\b", r"\bтаркиб\w*\b",
        r"\bқатлам\w*\b", r"\bкомпонент\w*\b",
        # Russian
        r"\bархитектур\w*\b", r"\bструктур\w*\b",
        r"\bкомпонент\w*\b", r"\bсло\w*\b", r"\bисточник данных\b",
        # English
        r"\barchitectur\w*\b", r"\bstructure\b", r"\bcomponent\w*\b",
        r"\blayer\w*\b", r"\bdata flow\b", r"\bdata source\w*\b",
        # Kazakh / Karakalpak
        r"\bқұрылым\w*\b", r"\bқабат\w*\b", r"\bқұрам\w*\b",
        r"\bqurılım\w*\b", r"\bqatlam\w*\b", r"\bkomponent\w*\b",
    ),
    "process": (
        # Uzbek
        r"\bqanday ishl\w*\b", r"\bqanday aniql\w*\b",
        r"\bkeyin nima bo'l\w*\b", r"\bjarayon\w*\b",
        r"\bbosqich\w*\b", r"\bketma ket\b",
        # Uzbek Cyrillic
        r"\bқандай ишл\w*\b", r"\bкейин нима бўл\w*\b",
        r"\bжараён\w*\b", r"\ббосқич\w*\b",
        # Russian
        r"\bкак работает\b", r"\bпроцесс\w*\b",
        r"\bпосле сигнал\w*\b", r"\bчто происходит\b",
        r"\bэтап\w*\b",
        # English
        r"\bhow does .* work\b", r"\bhow .* works\b",
        r"\bprocess\w*\b", r"\bworkflow\w*\b",
        r"\bwhat happens (next|after)\b", r"\bafter the signal\b",
        # Kazakh / Karakalpak
        r"\bқалай жұмыс іст\w*\b", r"\bкейін не бол\w*\b",
        r"\bпроцесс\w*\b", r"\bqalay isle\w*\b",
        r"\bkeyin ne bol\w*\b", r"\bbasqısh\w*\b",
    ),
    "reason": (
        r"\bnega\b", r"\bnima uchun\b", r"\bsabab\w*\b",
        r"\bпочему\b", r"\bзачем\b", r"\bпричин\w*\b",
        r"\bwhy\b", r"\breason\w*\b", r"\bнеге\b",
    ),
    "definition": (
        r"\bnima\b", r"\bчто такое\b", r"\bwhat is\b",
        r"\bdefine\b", r"\bdegen ne\b",
    ),
}


def classify_task_type(query: str) -> str:
    """Classify the requested answer task, independently from project/general routing.

    This is a conservative, language-aware baseline. It does not infer facts or
    replace evidence retrieval; unknown task shapes fall back to explanation.
    """
    value = _normalize(query)
    if not value:
        return "explanation"

    priority = ("comparison", "status_audit", "architecture", "process", "reason", "definition")
    for task_type in priority:
        if any(re.search(pattern, value, flags=re.UNICODE) for pattern in _PATTERNS[task_type]):
            return task_type
    return "explanation"
