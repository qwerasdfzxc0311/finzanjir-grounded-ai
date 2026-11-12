from __future__ import annotations

from typing import Any

from .registry import SIGNAL_REGISTRY


_ALLOWED_FIELDS = frozenset({
    "signal_id",
    "condition_met",
    "evidence_id",
    "event_key",
    "source",
    "observed_at",
    "evidence_quality",
    "recency_factor",
    "corroborating_signal_ids",
    "rule_version",
    "detector_version",
    "scope",
    "data_mode",
})


def normalize_signal_observations(
    observations: list[dict[str, Any]],
    *,
    data_mode: str = "synthetic",
) -> list[dict[str, Any]]:
    """Normalize trusted bank-side detector facts into scoring events.

    This adapter does not inspect raw bank records or infer fraud by itself.
    A source-side detector must evaluate the rule and provide condition_met.
    The current prototype accepts synthetic, bank-internal observations only.
    """
    if not isinstance(observations, list):
        raise ValueError("signal_observations must be a list")
    if len(observations) > 100:
        raise ValueError("signal_observations cannot contain more than 100 items")
    if data_mode != "synthetic":
        raise ValueError("signal observation adapter currently accepts synthetic data only")

    normalized: list[dict[str, Any]] = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise ValueError(f"signal_observations[{index}] must be an object")
        extra_fields = set(observation) - _ALLOWED_FIELDS
        if extra_fields:
            raise ValueError(
                f"signal_observations[{index}] contains unsupported fields: {', '.join(sorted(extra_fields))}"
            )

        signal_id = observation.get("signal_id")
        if not isinstance(signal_id, str) or signal_id not in SIGNAL_REGISTRY:
            raise ValueError(f"signal_observations[{index}] has an unknown signal_id")
        condition_met = observation.get("condition_met")
        if not isinstance(condition_met, bool):
            raise ValueError(f"signal_observations[{index}].condition_met must be boolean")
        scope = observation.get("scope", "bank_internal")
        if scope != "bank_internal":
            raise ValueError("cross-bank signal observations are disabled pending legal and security approval")
        observed_mode = observation.get("data_mode", data_mode)
        if observed_mode != "synthetic":
            raise ValueError("signal observation data_mode must be synthetic")

        if not condition_met:
            continue

        for field in ("evidence_id", "source", "observed_at", "rule_version", "detector_version"):
            value = observation.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"signal_observations[{index}].{field} must be a non-empty string")

        quality = observation.get("evidence_quality")
        recency = observation.get("recency_factor")
        for field, value in (("evidence_quality", quality), ("recency_factor", recency)):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"signal_observations[{index}].{field} must be numeric")
            if not 0 <= value <= 1:
                raise ValueError(f"signal_observations[{index}].{field} must be between 0 and 1")

        corroborating = observation.get("corroborating_signal_ids", [])
        if not isinstance(corroborating, list) or any(
            not isinstance(item, str) or item not in SIGNAL_REGISTRY for item in corroborating
        ):
            raise ValueError(f"signal_observations[{index}].corroborating_signal_ids must contain known signal IDs")

        event_key = observation.get("event_key", observation["evidence_id"])
        if not isinstance(event_key, str) or not event_key.strip():
            raise ValueError(f"signal_observations[{index}].event_key must be a non-empty string")
        normalized.append({
            "signal_id": signal_id,
            "evidence_id": observation["evidence_id"].strip(),
            "event_key": event_key.strip(),
            "source": observation["source"].strip(),
            "observed_at": observation["observed_at"].strip(),
            "evidence_quality": float(quality),
            "recency_factor": float(recency),
            "corroborating_signal_ids": list(corroborating),
            "rule_version": observation["rule_version"].strip(),
            "detector_version": observation["detector_version"].strip(),
            "data_mode": "synthetic",
        })

    return normalized
