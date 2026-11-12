from __future__ import annotations

import math
from typing import Any


class PerformanceCapacity:
    """Evaluate measured capacity only against explicit, approved thresholds."""

    @staticmethod
    def _finite_number(value: Any, field: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError(f"{field} must be a finite number")
        return float(value)

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value.strip()

    def _validate_thresholds(self, thresholds: dict | None) -> dict | None:
        if thresholds is None:
            return None
        if not isinstance(thresholds, dict):
            raise ValueError("thresholds must be an object or None")
        required = {"latency_ms", "error_rate", "resource_utilization"}
        if set(thresholds) != required:
            raise ValueError("thresholds must contain exactly latency_ms, error_rate and resource_utilization")
        validated = {
            key: self._finite_number(value, f"thresholds.{key}")
            for key, value in thresholds.items()
        }
        if validated["latency_ms"] < 0:
            raise ValueError("thresholds.latency_ms must be non-negative")
        for key in ("error_rate", "resource_utilization"):
            if not 0 <= validated[key] <= 1:
                raise ValueError(f"thresholds.{key} must be between 0 and 1")
        return validated

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
        latency = self._finite_number(latency_ms, "latency_ms")
        errors = self._finite_number(error_rate, "error_rate")
        utilization = self._finite_number(resource_utilization, "resource_utilization")
        if latency < 0:
            raise ValueError("latency_ms must be non-negative")
        if not 0 <= errors <= 1:
            raise ValueError("error_rate must be between 0 and 1")
        if not 0 <= utilization <= 1:
            raise ValueError("resource_utilization must be between 0 and 1")
        if not isinstance(recovered, bool):
            raise ValueError("recovered must be boolean")
        profile = self._required_text(load_profile, "load_profile")
        env = self._required_text(environment, "environment")
        approved = self._validate_thresholds(thresholds)

        result = {
            "latency_ms": latency,
            "error_rate": errors,
            "resource_utilization": utilization,
            "recovered": recovered,
            "load_profile": profile,
            "environment": env,
            "recovery_required": not recovered,
        }
        if approved is None:
            result.update({"result": "UNVERIFIED", "reason": "thresholds_unapproved"})
            return result

        passed = (
            latency <= approved["latency_ms"]
            and errors <= approved["error_rate"]
            and utilization <= approved["resource_utilization"]
            and recovered
        )
        result["result"] = "PASS" if passed else "FAIL"
        result["reason"] = "thresholds_met" if passed else "capacity_or_recovery_threshold_exceeded"
        return result

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        ordered = sorted(values)
        index = max(0, math.ceil(percentile * len(ordered)) - 1)
        return ordered[index]

    def evaluate_samples(
        self,
        *,
        latencies_ms: list[float],
        error_count: int,
        request_count: int,
        duration_seconds: float,
        resource_utilization_samples: list[float],
        recovered: bool,
        thresholds: dict | None,
        load_profile: str,
        environment: str = "unknown",
    ) -> dict:
        if not isinstance(latencies_ms, list) or not latencies_ms:
            raise ValueError("latencies_ms must be a non-empty list")
        latencies = [self._finite_number(value, "latencies_ms[]") for value in latencies_ms]
        if any(value < 0 for value in latencies):
            raise ValueError("latencies_ms values must be non-negative")
        if not isinstance(request_count, int) or isinstance(request_count, bool) or request_count <= 0:
            raise ValueError("request_count must be a positive integer")
        if request_count != len(latencies):
            raise ValueError("request_count must equal the number of latency samples")
        if not isinstance(error_count, int) or isinstance(error_count, bool) or not 0 <= error_count <= request_count:
            raise ValueError("error_count must be an integer between zero and request_count")
        duration = self._finite_number(duration_seconds, "duration_seconds")
        if duration <= 0:
            raise ValueError("duration_seconds must be positive")
        if not isinstance(resource_utilization_samples, list) or not resource_utilization_samples:
            raise ValueError("resource_utilization_samples must be a non-empty list")
        utilization_samples = [
            self._finite_number(value, "resource_utilization_samples[]")
            for value in resource_utilization_samples
        ]
        if any(not 0 <= value <= 1 for value in utilization_samples):
            raise ValueError("resource utilization samples must be between 0 and 1")

        percentiles = {
            "p50": self._percentile(latencies, 0.50),
            "p95": self._percentile(latencies, 0.95),
            "p99": self._percentile(latencies, 0.99),
        }
        summary = self.evaluate(
            latency_ms=percentiles["p95"],
            error_rate=error_count / request_count,
            resource_utilization=max(utilization_samples),
            recovered=recovered,
            thresholds=thresholds,
            load_profile=load_profile,
            environment=environment,
        )
        summary.update({
            "sample_count": request_count,
            "error_count": error_count,
            "duration_seconds": duration,
            "throughput_rps": request_count / duration,
            "latency_percentiles_ms": percentiles,
            "peak_resource_utilization": max(utilization_samples),
            "measurement_scope": "provided_samples_not_a_live_load_test",
        })
        return summary
