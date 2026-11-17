from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlsplit
from typing import Any

from finzanjir_ai.orchestration.intent import detect_query_language
from finzanjir_ai.retrieval.text import meaningful_tokens


_INTROS = {
    "uz": "Tavily orqali topilgan ochiq manbalardan mavzuga mos ma'lumotlar ajratildi:",
    "ru": "Из открытых источников, найденных через Tavily, выделены относящиеся к теме сведения:",
    "en": "Relevant information was extracted from public sources found through Tavily:",
    "kk": "Tavily арқылы табылған ашық дереккөздерден тақырыпқа қатысты мәліметтер бөлінді:",
    "kaa": "Tavily arqalı tabılǵan ashıq dereklerden temaǵa tiyisli maǵlıwmatlar ajıratıldı:",
}
_LIMITS = {
    "uz": "Cheklov: bu javob tashqi sahifalardan olingan parchalarni mahalliy qoidaviy mexanizm bilan tartiblash orqali tuzildi. Bu mustaqil fakt tekshiruvi yoki FINZANJIRning tasdiqlangan bilim bazasiga qo'shish degani emas.",
    "ru": "Ограничение: ответ составлен локальным алгоритмом отбора фрагментов внешних страниц. Это не является независимой проверкой фактов или добавлением сведений в подтверждённую базу FINZANJIR.",
    "en": "Limit: this answer was assembled locally by selecting passages from external pages. It is not an independent fact-check and does not add the material to FINZANJIR's approved knowledge base.",
    "kk": "Шектеу: жауап сыртқы беттерден алынған үзінділерді жергілікті алгоритммен іріктеу арқылы жасалды. Бұл тәуелсіз факт-тексеру немесе FINZANJIR-дің расталған білім қорына қосу емес.",
    "kaa": "Sheklew: bul juwap sırtqı betlerden alınǵan bóleklerdi jergilikli algoritm menen tańlaw arqalı dúzildi. Bul ǵárezsiz fakt tekseriwi yamasa FINZANJIR tastıyıqlanǵan bilim bazasına qosıw emes.",
}


@dataclass(frozen=True)
class LocalResearchAnswer:
    answer: str
    confidence: float
    abstained: bool
    sources: tuple[dict[str, Any], ...]
    provenance: tuple[str, ...]
    generation_mode: str = "tavily_local_extractive"
    confidence_basis: str = "heuristic_source_relevance_not_probability"


def _safe_https_url(value: Any) -> str | None:
    url = str(value or "").strip()
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or len(url) > 2000
        ):
            return None
        host = parsed.hostname.casefold()
        if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
            return None
        return url
    except ValueError:
        return None


def _domain(url: str) -> str:
    host = (urlsplit(url).hostname or "").casefold()
    return host[4:] if host.startswith("www.") else host


def _clean_text(value: Any, *, limit: int = 18000) -> str:
    text = str(value or "")[:limit]
    text = re.sub(r"!\\[[^\\]]*\\]\\([^)]*\\)", " ", text)
    text = re.sub(r"\\[([^\\]]+)\\]\\([^)]*\\)", r"\\1", text)
    text = re.sub(r"<[^>]{1,300}>", " ", text)
    text = re.sub(r"^\\s{0,3}#{1,6}\\s*", "", text, flags=re.MULTILINE)
    text = re.sub("\\x60{3}.*?\\x60{3}", " ", text, flags=re.DOTALL)
    text = re.sub(r"\\s+", " ", text).strip()
    return text


def _sentences(value: str) -> tuple[str, ...]:
    parts = re.split(r"(?<=[.!?])\\s+|\\s*[•▪]\\s*|(?<=;)\\s+|\\s{2,}", value)
    cleaned = []
    for part in parts:
        sentence = part.strip(" \\t\\r\\n-*•")
        if 35 <= len(sentence) <= 520:
            cleaned.append(sentence)
    return tuple(cleaned)


def compose_tavily_local_answer(
    query: str,
    results: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    language: str | None = None,
    max_sentences: int = 5,
    max_sources: int = 6,
) -> LocalResearchAnswer:
    """Create a source-linked answer without calling any language model.

    The composer only extracts, ranks, deduplicates and orders source passages.
    It does not paraphrase external claims, follow instructions found in pages,
    approve facts, or write external content into FINZANJIR's canonical KB.
    """
    lang = language or detect_query_language(query)
    intro = _INTROS.get(lang, _INTROS["uz"])
    limitation = _LIMITS.get(lang, _LIMITS["uz"])
    query_terms = set(meaningful_tokens(query))
    candidates: list[tuple[float, str, str, str, str]] = []
    source_rows: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_sentences: set[str] = set()

    for item in list(results)[: max(1, min(int(max_sources), 8))]:
        if not isinstance(item, dict):
            continue
        url = _safe_https_url(item.get("url"))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = str(item.get("title") or "Untitled source")[:300]
        snippet = _clean_text(item.get("snippet") or item.get("content") or "", limit=1800)
        raw = _clean_text(item.get("raw_content") or "", limit=18000)
        domain = _domain(url)
        provider_score = item.get("score")
        provider_score = float(provider_score) if isinstance(provider_score, (int, float)) else 0.0
        provider_score = max(0.0, min(1.0, provider_score))
        source_rows.append({
            "title": title,
            "url": url,
            "snippet": snippet[:1200],
            "published_date": item.get("published_date"),
            "score": provider_score,
            "domain": domain,
        })

        body = raw or snippet
        if not body:
            continue
        for sentence in _sentences(body):
            normalized = " ".join(meaningful_tokens(sentence))
            if not normalized or normalized in seen_sentences:
                continue
            sentence_terms = set(normalized.split())
            overlap = len(query_terms & sentence_terms)
            if query_terms and overlap == 0:
                continue
            lexical = overlap / max(1, len(query_terms))
            official_bonus = 0.08 if (
                domain.endswith(".gov")
                or ".gov." in domain
                or domain.endswith(".edu")
                or domain.endswith(".int")
                or domain in {"who.int", "un.org", "europa.eu"}
            ) else 0.0
            score = 0.65 * lexical + 0.25 * provider_score + official_bonus
            candidates.append((score, sentence, url, title, domain))
            seen_sentences.add(normalized)

    candidates.sort(key=lambda row: (-row[0], row[4], row[1]))
    selected: list[tuple[float, str, str, str, str]] = []
    domain_counts: dict[str, int] = {}
    for candidate in candidates:
        if domain_counts.get(candidate[4], 0) >= 2:
            continue
        selected.append(candidate)
        domain_counts[candidate[4]] = domain_counts.get(candidate[4], 0) + 1
        if len(selected) >= max(1, min(int(max_sentences), 8)):
            break

    selected_urls = tuple(dict.fromkeys(row[2] for row in selected))
    selected_sources = tuple(row for row in source_rows if row["url"] in selected_urls)
    if not selected:
        if source_rows:
            message = {
                "uz": "Tavily mos sahifalarni topdi, ammo mahalliy mexanizm ulardan savolga bevosita mos, yetarlicha aniq parcha ajrata olmadi. Manbalarni quyida ochib tekshirishingiz mumkin.",
                "ru": "Tavily нашёл подходящие страницы, но локальный механизм не смог выделить из них достаточно точные фрагменты, непосредственно отвечающие на вопрос. Источники можно открыть ниже.",
                "en": "Tavily found candidate pages, but the local composer could not extract sufficiently relevant passages to answer safely. You can inspect the sources below.",
                "kk": "Tavily сәйкес беттерді тапты, бірақ жергілікті механизм сұраққа тікелей жауап беретін жеткілікті нақты үзінділерді бөле алмады. Дереккөздерді төменнен ашып тексеруге болады.",
                "kaa": "Tavily sáykes betlerdi taptı, biraq jergilikli mexanizm sorawǵa tikkeley juwap beretuǵın jetkilikli anıq bóleklerdi ajırata almadı. Derekti tómennen ashıp tekseriwge boladı.",
            }.get(lang, _INTROS["uz"])
        else:
            message = {
                "uz": "Tavily qidiruvida mos ochiq manba topilmadi. Taxminiy javob tuzilmadi.",
                "ru": "Поиск Tavily не нашёл подходящих открытых источников. Предположительный ответ не сформирован.",
                "en": "Tavily search found no suitable public sources. No speculative answer was generated.",
                "kk": "Tavily іздеуінен сәйкес ашық дереккөздер табылмады. Болжамды жауап жасалмады.",
                "kaa": "Tavily izlewinde sáykes ashıq derek tabılmadı. Boljam juwap dúzilmedi.",
            }.get(lang, _INTROS["uz"])
        return LocalResearchAnswer(
            answer=message,
            confidence=0.0,
            abstained=True,
            sources=tuple(source_rows),
            provenance=tuple(row["url"] for row in source_rows),
        )

    lines = [intro]
    for index, (_, sentence, _url, _title, _domain) in enumerate(selected, start=1):
        source_lang = detect_query_language(sentence)
        prefix = f"[{source_lang}] " if source_lang != lang else ""
        lines.append(f"{index}. {prefix}{sentence}")
    lines.append(limitation)
    unique_domains = len({row[4] for row in selected})
    average_score = sum(row[0] for row in selected) / len(selected)
    # This is a retrieval-quality heuristic, not a calibrated probability.
    confidence = min(0.82, 0.35 + 0.08 * min(unique_domains, 3) + 0.15 * average_score)
    return LocalResearchAnswer(
        answer="\\n\\n".join(lines),
        confidence=round(confidence, 3),
        abstained=False,
        sources=selected_sources,
        provenance=selected_urls,
    )
