class ImpactHarmReduction:
    """Compute transparent outcome-rate comparisons without unsupported causal claims."""

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
        if not segment or not dataset_version:
            return {"status": "UNVERIFIED", "reason": "comparison_context_missing"}
        if baseline_denominator <= 0 or current_denominator <= 0:
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
