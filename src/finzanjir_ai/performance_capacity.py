class PerformanceCapacity:
    """Evaluate capacity only against explicit, approved thresholds and a named load."""

    def evaluate(
        self,
        *,
        latency_ms: float,
        error_rate: float,
        resource_utilization: float,
        recovered: bool,
        thresholds: dict | None,
        load_profile: str,
        environment: str = "unknown",
    ) -> dict:
        result = {
            "latency_ms": latency_ms,
            "error_rate": error_rate,
            "resource_utilization": resource_utilization,
            "recovered": recovered,
            "load_profile": load_profile,
            "environment": environment,
            "recovery_required": not recovered,
        }
        if thresholds is None:
            result.update({"result": "UNVERIFIED", "reason": "thresholds_unapproved"})
            return result

        passed = (
            latency_ms <= thresholds["latency_ms"]
            and error_rate <= thresholds["error_rate"]
            and resource_utilization <= thresholds["resource_utilization"]
            and recovered
        )
        result["result"] = "PASS" if passed else "FAIL"
        result["reason"] = "thresholds_met" if passed else "capacity_or_recovery_threshold_exceeded"
        return result
