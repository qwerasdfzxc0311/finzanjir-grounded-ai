from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finzanjir_ai.retrieval.text import meaningful_tokens


@dataclass(frozen=True)
class LocalComposition:
    answer: str
    citations: tuple[str, ...]
    abstained: bool
    generation_mode: str = "local_composed_grounded"


_INTROS = {
    "uz": "Savolga mos tasdiqlangan loyiha ma'lumotlari:",
    "ru": "Подтвержденные сведения проекта, относящиеся к вопросу:",
    "en": "Verified project information relevant to the question:",
    "kk": "Сұраққа қатысты жобаның расталған мәліметтері:",
    "kaa": "Sorawǵa tiyisli joybardıń tastıyıqlanǵan maǵlıwmatları:",
}


def compose_local_grounded_answer(
    query: str,
    items: list[Any] | tuple[Any, ...],
    *,
    language: str = "uz",
    max_items: int = 5,
    max_chars: int = 6000,
) -> LocalComposition:
    """Compose a concise answer from source statements without paraphrasing facts.

    This is a deterministic evidence composer, not a generative language model.
    It ranks already-grounded statements, preserves their wording, and returns
    the exact source record IDs used. Missing matches produce an abstention.
    """
    query_tokens = set(meaningful_tokens(query))
    if not items:
        return LocalComposition("", (), True, "local_composer_no_match")

    ranked: list[tuple[float, str, str]] = []
    supporting: list[tuple[float, str, str]] = []
    seen: set[str] = set()
    for item in items:
        statement = str(getattr(item, "statement", "") or "").strip()
        record_id = str(getattr(item, "record_id", "") or "").strip()
        if not statement or not record_id:
            continue
        normalized = " ".join(meaningful_tokens(statement))
        if not normalized or normalized in seen:
            continue
        statement_tokens = set(normalized.split())
        alias_tokens = set(meaningful_tokens(" ".join(getattr(item, "aliases", ()) or ())))
        direct_overlap = len(query_tokens & statement_tokens)
        alias_overlap = len(query_tokens & alias_tokens)
        source_score = max(0.0, min(1.0, float(getattr(item, "score", 0.0) or 0.0)))
        if not query_tokens and len(items) == 1:
            direct_overlap = 1
        if direct_overlap == 0 and alias_overlap == 0:
            # A high-confidence item already admitted to the grounded context
            # may be a supporting fact expressed with different vocabulary.
            # Keep it only when at least one directly matched fact anchors the answer.
            if source_score >= 0.80:
                supporting.append((0.20 * source_score, record_id, statement))
            continue
        score = direct_overlap / max(1, len(query_tokens))
        score += 0.20 * alias_overlap / max(1, len(query_tokens))
        ranked.append((score + 0.025 * source_score, record_id, statement))
        seen.add(normalized)

    if ranked:
        ranked.extend(entry for entry in supporting if entry[1] not in {value[1] for value in ranked})
    if not ranked:
        return LocalComposition("", (), True, "local_composer_no_match")

    ranked.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))
    selected = ranked[:max(1, min(int(max_items), 8))]
    intro = _INTROS.get(language, _INTROS["uz"])
    lines = [intro]
    citations: list[str] = []
    for _, record_id, statement in selected:
        candidate = f"{len(citations) + 1}. {statement}"
        if sum(len(line) + 2 for line in lines) + len(candidate) > max_chars:
            break
        lines.append(candidate)
        citations.append(record_id)

    if not citations:
        return LocalComposition("", (), True, "local_composer_no_match")
    return LocalComposition(
        answer="\n\n".join(lines),
        citations=tuple(dict.fromkeys(citations)),
        abstained=False,
    )
