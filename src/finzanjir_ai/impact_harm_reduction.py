class ImpactHarmReduction:
    """Compute transparent outcome-rate comparisons without unsupported causal claims."""

    @staticmethod
    def _count(value, field: str, *, allow_zero: bool = True) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{field} must be an integer")
        if value < 0 or (not allow_zero and value == 0):
            raise ValueError(f"{field} must be {'positive' if not allow_zero else 'non-negative'}")
        return value

    @staticmethod
    def _context(value, field: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string or None")
        normalized = value.strip()
        return normalized or None

    def compare_rate(
        self,
        *,
        baseline_events: int,
        baseline_denominator: int,
        current_events: int,
        current_denominator: int,
        segment: str | None,
        dataset_version: str | None,
        methodology: str,
    ) -> dict:
        baseline_events = self._count(baseline_events, "baseline_events")
        current_events = self._count(current_events, "current_events")
        baseline_denominator = self._count(baseline_denominator, "baseline_denominator")
        current_denominator = self._count(current_denominator, "current_denominator")
        segment = self._context(segment, "segment")
        dataset_version = self._context(dataset_version, "dataset_version")
        methodology = self._context(methodology, "methodology")
        if not segment or not dataset_version or not methodology:
            return {"status": "UNVERIFIED", "reason": "comparison_context_missing"}
        if baseline_denominator == 0 or current_denominator == 0:
            return {"status": "UNVERIFIED", "reason": "invalid_denominator"}

        baseline_rate = baseline_events / baseline_denominator
        current_rate = current_events / current_denominator
        return {
            "status": "MEASURED",
            "baseline_rate": baseline_rate,
            "current_rate": current_rate,
            "change": current_rate - baseline_rate,
            "denominator": {
                "baseline": baseline_denominator,
                "current": current_denominator,
            },
            "segment": segment,
            "dataset_version": dataset_version,
            "methodology": methodology,
            "causal_claim": False,
            "limitation": "Observed rate change alone does not establish causal impact.",
        }
