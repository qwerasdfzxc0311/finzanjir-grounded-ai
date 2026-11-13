from __future__ import annotations

from typing import Any
from datetime import datetime
import re

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
        if (
            not isinstance(event_key, str)
            or not re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", event_key.strip())
        ):
            raise ValueError(f"signal_observations[{index}].event_key must be a 1-256 character opaque identifier")
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


def _parse_aware_observation_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def assess_observation_quality(
    observations: list[dict[str, Any]],
    *,
    reference_time: str,
    max_age_seconds: int = 86_400,
) -> dict[str, Any]:
    """Report synthetic observation freshness, ordering and duplicate conflicts.

    The monitor is diagnostic only: it never drops observations, changes scores,
    or makes a fraud determination. The caller supplies a fixed reference time so
    results are deterministic and replayable.
    """
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    if len(observations) > 100:
        raise ValueError("observations cannot contain more than 100 items")
    if (
        not isinstance(max_age_seconds, int)
        or isinstance(max_age_seconds, bool)
        or not 0 <= max_age_seconds <= 31_536_000
    ):
        raise ValueError("max_age_seconds must be an integer between 0 and 31536000")

    reference = _parse_aware_observation_time(reference_time, "reference_time")
    seen_event_keys: dict[str, tuple[str, str, str, str]] = {}
    seen_evidence_ids: set[str] = set()
    previous_time: datetime | None = None
    assessed: list[dict[str, Any]] = []

    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise ValueError(f"observations[{index}] must be an object")
        if observation.get("data_mode") != "synthetic":
            raise ValueError("observation quality monitor accepts synthetic data only")

        event_key = observation.get("event_key")
        evidence_id = observation.get("evidence_id")
        signal_id = observation.get("signal_id")
        source = observation.get("source")
        if not isinstance(event_key, str) or not event_key.strip():
            raise ValueError(f"observations[{index}].event_key must be non-empty")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError(f"observations[{index}].evidence_id must be non-empty")
        if not isinstance(signal_id, str) or not signal_id.strip():
            raise ValueError(f"observations[{index}].signal_id must be non-empty")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"observations[{index}].source must be non-empty")

        observed = _parse_aware_observation_time(
            observation.get("observed_at"),
            f"observations[{index}].observed_at",
        )
        age_seconds = (reference - observed).total_seconds()
        flags: list[str] = []
        if age_seconds < 0:
            flags.append("FUTURE_TIMESTAMP")
        elif age_seconds > max_age_seconds:
            flags.append("STALE")

        if previous_time is not None and observed < previous_time:
            flags.append("OUT_OF_ORDER")
        previous_time = observed

        normalized_key = event_key.strip()
        normalized_evidence = evidence_id.strip()
        fingerprint = (
            signal_id.strip(),
            normalized_evidence,
            source.strip(),
            observation["observed_at"].strip(),
        )
        if normalized_key in seen_event_keys:
            if seen_event_keys[normalized_key] == fingerprint:
                flags.append("DUPLICATE_EVENT")
            else:
                flags.append("CONFLICTING_EVENT_KEY")
        else:
            seen_event_keys[normalized_key] = fingerprint

        if normalized_evidence in seen_evidence_ids:
            flags.append("DUPLICATE_EVIDENCE_ID")
        else:
            seen_evidence_ids.add(normalized_evidence)

        assessed.append({
            "index": index,
            "event_key": normalized_key,
            "evidence_id": normalized_evidence,
            "signal_id": signal_id.strip(),
            "age_seconds": round(age_seconds, 3),
            "quality_flags": flags,
            "quality_status": "REVIEW_REQUIRED" if flags else "ACCEPTABLE",
        })

    flag_counts: dict[str, int] = {}
    for item in assessed:
        for flag in item["quality_flags"]:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

    return {
        "data_mode": "synthetic",
        "reference_time": reference_time.strip(),
        "max_age_seconds": max_age_seconds,
        "observation_count": len(assessed),
        "review_required_count": sum(item["quality_status"] == "REVIEW_REQUIRED" for item in assessed),
        "flag_counts": dict(sorted(flag_counts.items())),
        "observations": assessed,
        "diagnostic_only": True,
        "score_changed": False,
        "fraud_determination": False,
    }
