from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    confidence: float
    abstained: bool
    knowledge_refs: tuple[str, ...]
    provenance: tuple[str, ...]
    runtime_refs: tuple[str, ...]


def generate_grounded_answer(*, question: str, knowledge: list[dict[str, Any]], runtime: list[dict[str, Any]]) -> GroundedAnswer:
    if not question.strip() or not knowledge:
        return GroundedAnswer(
            answer="Yetarli asos mavjud emas. FINZANJIR AI bu savolga ishonchli grounded javob bera olmaydi.",
            confidence=0.0,
            abstained=True,
            knowledge_refs=(),
            provenance=(),
            runtime_refs=tuple(str(item.get("id")) for item in runtime if item.get("id")),
        )

    knowledge_refs = tuple(str(item["record_id"]) for item in knowledge if item.get("record_id"))
    provenance: list[str] = []
    for item in knowledge:
        for source in item.get("provenance", ()):
            provenance.append(str(source))
    runtime_refs = tuple(str(item["id"]) for item in runtime if item.get("id"))
    confidence = min(0.95, 0.6 + 0.1 * min(len(knowledge), 3) + (0.1 if runtime else 0.0))
    answer = knowledge[0].get("statement", "").strip()
    return GroundedAnswer(
        answer=answer,
        confidence=confidence,
        abstained=False,
        knowledge_refs=knowledge_refs,
        provenance=tuple(dict.fromkeys(provenance)),
        runtime_refs=runtime_refs,
    )
