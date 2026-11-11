from __future__ import annotations

from dataclasses import dataclass

from finzanjir_ai.retrieval.grounding import GroundedContext


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    confidence: float
    abstained: bool
    citations: tuple[str, ...]


class GroundedAnswerGenerator:
    ABSTENTION_THRESHOLD = 0.35

    def generate(self, query: str, context: GroundedContext) -> AnswerResult:
        if not context.items:
            return AnswerResult(
                answer="Yetarli asoslangan bilim topilmadi, shuning uchun ishonchli javob berishdan tiyilaman.",
                confidence=0.0,
                abstained=True,
                citations=(),
            )

        items = context.items[:3]
        statements = " ".join(item.statement for item in items)
        top_score = max(0.0, min(1.0, items[0].score))
        supported = sum(
            1 for item in items
            if isinstance(item.evidence, dict) and item.evidence.get("status") == "supported"
        )
        confidence = min(1.0, 0.7 * top_score + 0.3 * (supported / len(items)))
        if supported == 0 or confidence < self.ABSTENTION_THRESHOLD:
            return AnswerResult(
                answer="Authoritative evidence ishonchlilik chegarasidan past; javob berishdan bosh tortildi.",
                confidence=0.0 if supported == 0 else confidence,
                abstained=True,
                citations=tuple(item.record_id for item in items),
            )
        return AnswerResult(
            answer=statements,
            confidence=confidence,
            abstained=False,
            citations=tuple(item.record_id for item in items),
        )


@dataclass(frozen=True)
class FunctionAnswerResult:
    answer: str
    confidence: float
    abstained: bool
    knowledge_refs: tuple[str, ...]
    provenance: tuple[str, ...]


def generate_grounded_answer(*, question: str, knowledge: list[dict], runtime: list[dict]) -> FunctionAnswerResult:
    if not knowledge:
        return FunctionAnswerResult(
            answer="Yetarli asoslangan bilim topilmadi, shuning uchun ishonchli javob berishdan tiyilaman.",
            confidence=0.0,
            abstained=True,
            knowledge_refs=(),
            provenance=(),
        )
    statements = " ".join(str(item.get("statement", "")) for item in knowledge if item.get("statement"))
    refs = tuple(str(item.get("record_id")) for item in knowledge if item.get("record_id"))
    provenance = tuple(
        str(source)
        for item in knowledge
        for source in item.get("provenance", [])
    )
    confidence = 1.0 if statements else 0.0
    return FunctionAnswerResult(
        answer=statements,
        confidence=confidence,
        abstained=not bool(statements),
        knowledge_refs=refs,
        provenance=provenance,
    )
