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
        citations = tuple(item.record_id for item in items)

        return AnswerResult(
            answer=statements,
            confidence=confidence,
            abstained=False,
            citations=citations,
        )
