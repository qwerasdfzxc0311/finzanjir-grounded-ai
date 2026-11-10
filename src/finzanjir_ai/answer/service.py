from __future__ import annotations

from dataclasses import dataclass

from finzanjir_ai.retrieval.grounding import GroundedContext


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    confidence: float
    citations: tuple[str, ...]
    abstained: bool


class GroundedAnswerService:
    def answer(self, query: str, context: GroundedContext, *, abstention_threshold: float = 0.35) -> GroundedAnswer:
        if not context.items:
            return GroundedAnswer(
                answer="Yetarli authoritative evidence topilmadi; javob berishdan bosh tortildi.",
                confidence=0.0,
                citations=(),
                abstained=True,
            )
        confidence = round(sum(max(0.0, min(1.0, item.score)) for item in context.items) / len(context.items), 4)
        if confidence < abstention_threshold:
            return GroundedAnswer(
                answer="Authoritative evidence ishonchlilik chegarasidan past; javob berishdan bosh tortildi.",
                confidence=confidence,
                citations=tuple(item.record_id for item in context.items),
                abstained=True,
            )
        statements = " ".join(item.statement for item in context.items)
        return GroundedAnswer(
            answer=statements,
            confidence=confidence,
            citations=tuple(item.record_id for item in context.items),
            abstained=False,
        )
