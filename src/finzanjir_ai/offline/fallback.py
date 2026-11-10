from __future__ import annotations

from dataclasses import dataclass

from finzanjir_ai.answer.generator import AnswerResult, GroundedAnswerGenerator
from finzanjir_ai.retrieval.grounding import GroundedContext


@dataclass(frozen=True)
class OfflineResult:
    mode: str
    answer: AnswerResult


class OfflineAnswerRouter:
    def __init__(self) -> None:
        self._generator = GroundedAnswerGenerator()

    def answer(
        self,
        query: str,
        context: GroundedContext,
        *,
        primary_available: bool,
    ) -> OfflineResult:
        if primary_available:
            return OfflineResult(
                mode="full_grounded",
                answer=self._generator.generate(query, context),
            )
        if context.items:
            return OfflineResult(
                mode="retrieval_only",
                answer=self._generator.generate(query, context),
            )
        return OfflineResult(
            mode="abstention",
            answer=self._generator.generate(query, context),
        )
