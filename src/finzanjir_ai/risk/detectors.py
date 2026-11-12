from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any

from .registry import SIGNAL_REGISTRY


_OPERATORS = frozenset({"eq", "ne", "gt", "gte", "lt", "lte", "in"})


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _matches(actual: Any, condition: dict[str, Any]) -> bool:
    operator = condition["op"]
    expected = condition["value"]
    if operator in {"eq", "ne"}:
        if isinstance(expected, bool):
            same_type_value = isinstance(actual, bool) and actual is expected
        elif isinstance(expected, str):
            same_type_value = isinstance(actual, str) and actual == expected
        elif _is_finite_number(expected):
            same_type_value = _is_finite_number(actual) and actual == expected
        else:
            same_type_value = actual == expected
        return same_type_value if operator == "eq" else not same_type_value
    if operator == "in":
        if not isinstance(expected, list):
            return False
        return any(
            (isinstance(item, bool) and isinstance(actual, bool) and actual is item)
            or (isinstance(item, str) and isinstance(actual, str) and actual == item)
            or (_is_finite_number(item) and _is_finite_number(actual) and actual == item)
            for item in expected
        )
    if not _is_finite_number(actual) or not _is_finite_number(expected):
        return False
    if operator == "gt":
        return actual > expected
    if operator == "gte":
        return actual >= expected
    if operator == "lt":
        return actual < expected
    if operator == "lte":
        return actual <= expected
    return False


class SyntheticSignalDetector:
    """Evaluate candidate detector rules against synthetic, bank-internal feature bundles only."""

    def __init__(self, rules_path: str | Path | None = None) -> None:
        path = Path(rules_path) if rules_path else (
            Path(__file__).resolve().parents[3] / "contracts" / "signal_detector_rules_v1.json"
        )
        document = json.loads(path.read_text(encoding="utf-8"))
        if (
            document.get("contract_id") != "signal-detector-rules-v1"
            or document.get("data_mode") != "synthetic_only"
            or document.get("scope") != "bank_internal_only"
        ):
            raise ValueError("detector rules contract must be synthetic and bank-internal only")
        rules = document.get("detectors")
        if not isinstance(rules, list) or len(rules) != len(SIGNAL_REGISTRY):
            raise ValueError("detector rules must cover every registered signal exactly once")
        self._rules: dict[str, dict[str, Any]] = {}
        self._allowed_features: set[str] = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError("each detector rule must be an object")
            signal_id = rule.get("signal_id")
            if signal_id not in SIGNAL_REGISTRY or signal_id in self._rules:
                raise ValueError(f"unknown or duplicate detector signal_id: {signal_id}")
            if rule.get("status") != "synthetic_test_only" or rule.get("cross_bank_data_enabled") is not False:
                raise ValueError(f"{signal_id} must remain synthetic-only and cross-bank disabled")
            if rule.get("legal_gate") != "unverified_bank_internal_lawful_purpose_required":
                raise ValueError(f"{signal_id} is missing the bank-internal legal gate")
            required = rule.get("required_features")
            optional = rule.get("optional_features", [])
            all_of = rule.get("all_of")
            benign_if = rule.get("benign_if", [])
            if not isinstance(required, list) or not required or not isinstance(optional, list) or not isinstance(all_of, list) or not all_of:
                raise ValueError(f"{signal_id} must declare required_features and all_of conditions")
            if not isinstance(benign_if, list):
                raise ValueError(f"{signal_id}.benign_if must be a list")
            condition_fields: set[str] = set()
            for condition in [*all_of, *benign_if]:
                if not isinstance(condition, dict):
                    raise ValueError(f"{signal_id} contains a malformed condition")
                field = condition.get("field")
                operator = condition.get("op")
                if not isinstance(field, str) or not field.strip() or operator not in _OPERATORS or "value" not in condition:
                    raise ValueError(f"{signal_id} contains an invalid condition")
                if operator == "in" and not isinstance(condition["value"], list):
                    raise ValueError(f"{signal_id} in-condition requires a list")
                condition_fields.add(field)
            if any(not isinstance(field, str) or not field.strip() for field in [*required, *optional]):
                raise ValueError(f"{signal_id} required/optional feature names must be non-empty strings")
            if not set(required).issubset({item["field"] for item in all_of}):
                raise ValueError(f"{signal_id} required_features must be covered by all_of conditions")
            self._allowed_features.update(condition_fields)
            self._allowed_features.update(optional)
            self._rules[signal_id] = rule
        if set(self._rules) != set(SIGNAL_REGISTRY):
            raise ValueError("detector rules and signal registry IDs do not match")

    def catalogue(self) -> list[dict[str, Any]]:
        return [
            {
                "signal_id": rule["signal_id"],
                "name": rule["name"],
                "status": rule["status"],
                "required_features": list(rule["required_features"]),
                "legal_gate": rule["legal_gate"],
                "scope": rule["scope"],
                "cross_bank_data_enabled": rule["cross_bank_data_enabled"],
                "note": rule["note"],
            }
            for rule in self._rules.values()
        ]

    def evaluate(
        self,
        *,
        scenario_id: str,
        observed_at: str,
        features: dict[str, Any],
        evidence_quality: float = 1.0,
        recency_factor: float = 1.0,
    ) -> dict[str, Any]:
        if not isinstance(scenario_id, str) or not scenario_id.strip() or len(scenario_id) > 128:
            raise ValueError("scenario_id must be a non-empty string of at most 128 characters")
        if not isinstance(observed_at, str) or not observed_at.strip():
            raise ValueError("observed_at must be a non-empty timestamp")
        try:
            timestamp = datetime.fromisoformat(observed_at.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("observed_at must be an ISO-8601 timestamp") from exc
        if timestamp.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        for field, value in (("evidence_quality", evidence_quality), ("recency_factor", recency_factor)):
            if not _is_finite_number(value) or not 0 <= value <= 1:
                raise ValueError(f"{field} must be a finite number between 0 and 1")
        if not isinstance(features, dict):
            raise ValueError("features must be an object")
        if len(features) > 100:
            raise ValueError("features cannot contain more than 100 fields")
        extra_fields = set(features) - self._allowed_features
        if extra_fields:
            raise ValueError(f"unsupported feature fields: {', '.join(sorted(extra_fields))}")
        for field, value in features.items():
            if not isinstance(field, str) or not field.strip():
                raise ValueError("feature names must be non-empty strings")
            if isinstance(value, (dict, list)) or value is None:
                raise ValueError(f"feature {field} must be a scalar value")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"feature {field} must be finite")
            if isinstance(value, str) and len(value) > 256:
                raise ValueError(f"feature {field} exceeds the 256-character limit")

        outcomes: list[dict[str, Any]] = []
        detected_ids: list[str] = []
        for signal_id, rule in self._rules.items():
            conditions = rule["all_of"]
            missing = sorted({item["field"] for item in conditions if item["field"] not in features})
            if missing:
                status = "INSUFFICIENT_DATA"
                reason = "missing_required_features"
                matched = []
            else:
                matched = [item["field"] for item in conditions if _matches(features[item["field"]], item)]
                if len(matched) != len(conditions):
                    status = "NOT_DETECTED"
                    reason = "rule_conditions_not_met"
                else:
                    benign = [
                        item["field"]
                        for item in rule.get("benign_if", [])
                        if item["field"] in features and _matches(features[item["field"]], item)
                    ]
                    if benign:
                        status = "SUPPRESSED_BENIGN"
                        reason = "benign_counter_evidence"
                    else:
                        status = "DETECTED"
                        reason = "all_rule_conditions_met"
                        detected_ids.append(signal_id)
            outcomes.append({
                "signal_id": signal_id,
                "name": rule["name"],
                "status": status,
                "reason_code": reason,
                "matched_features": matched,
                "missing_features": missing,
                "observed_optional_features": [
                    field for field in rule.get("optional_features", []) if field in features
                ],
                "rule_version": rule["rule_version"],
                "detector_version": rule["detector_version"],
                "legal_gate": rule["legal_gate"],
            })

        corroborating_ids = [value for value in detected_ids]
        observations = []
        for outcome in outcomes:
            if outcome["status"] != "DETECTED":
                continue
            signal_id = outcome["signal_id"]
            rule = self._rules[signal_id]
            observations.append({
                "signal_id": signal_id,
                "condition_met": True,
                "evidence_id": f"{scenario_id.strip()}:{signal_id}",
                "source": "synthetic-feature-detector",
                "observed_at": timestamp.isoformat().replace("+00:00", "Z"),
                "evidence_quality": float(evidence_quality),
                "recency_factor": float(recency_factor),
                "corroborating_signal_ids": [value for value in corroborating_ids if value != signal_id],
                "rule_version": rule["rule_version"],
                "detector_version": rule["detector_version"],
                "scope": "bank_internal",
                "data_mode": "synthetic",
            })
        return {
            "scenario_id": scenario_id.strip(),
            "data_mode": "synthetic",
            "scope": "bank_internal",
            "detector_version": "synthetic-feature-engine-v1",
            "rule_set": "signal-detector-rules-v1",
            "detected_count": len(detected_ids),
            "detected_signal_ids": detected_ids,
            "detections": outcomes,
            "signal_observations": observations,
            "limitations": [
                "Candidate engineering rules are evaluated against supplied synthetic feature values only.",
                "The feature engine does not connect to or inspect bank source systems.",
                "Thresholds are not statistically calibrated and do not establish fraud probability or guilt.",
                "No cross-bank data, real customer action, payment block or authoritative decision is enabled.",
            ],
        }


@lru_cache(maxsize=1)
def synthetic_signal_detector() -> SyntheticSignalDetector:
    return SyntheticSignalDetector()
