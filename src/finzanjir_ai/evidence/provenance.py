from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
from typing import Any


_OPAQUE_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_RECORD_FIELDS = (
    "sequence",
    "evidence_id",
    "event_id",
    "source",
    "observed_at",
    "acquisition_method",
    "source_version",
    "payload_digest",
    "data_mode",
    "previous_record_hash",
)


def _required_opaque(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value.strip()):
        raise ValueError(f"{field} must be a 1-128 character opaque identifier")
    return value.strip()


def _required_text(value: Any, field: str, *, max_length: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
        raise ValueError(f"{field} must be a non-empty string up to {max_length} characters")
    return value.strip()


def _aware_timestamp(value: Any, field: str) -> str:
    text = _required_text(value, field, max_length=64)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return text


def _record_hash(record: dict[str, Any]) -> str:
    canonical = {field: record[field] for field in _RECORD_FIELDS}
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class SyntheticEvidenceProvenanceChain:
    """In-memory, synthetic-only hash chain for evidence metadata.

    This provides tamper-evident ordering inside the current process only.
    It is not a digital signature, source authentication, durable storage,
    or proof that a source or evidence item is truthful. The caller-supplied
    payload digest and opaque token values are not independently verified.
    """

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._evidence_ids: set[str] = set()

    def append(
        self,
        *,
        evidence_id: str,
        event_id: str,
        source: str,
        observed_at: str,
        acquisition_method: str,
        source_version: str,
        payload_digest: str,
        data_mode: str = "synthetic",
    ) -> dict[str, Any]:
        if data_mode != "synthetic":
            raise ValueError("provenance chain accepts synthetic data only")
        normalized_evidence_id = _required_opaque(evidence_id, "evidence_id")
        normalized_event_id = _required_opaque(event_id, "event_id")
        if normalized_evidence_id in self._evidence_ids:
            raise ValueError("duplicate evidence_id")
        if not isinstance(payload_digest, str) or not _SHA256.fullmatch(payload_digest):
            raise ValueError("payload_digest must be a lowercase SHA-256 hex digest")

        record = {
            "sequence": len(self._records) + 1,
            "evidence_id": normalized_evidence_id,
            "event_id": normalized_event_id,
            "source": _required_text(source, "source"),
            "observed_at": _aware_timestamp(observed_at, "observed_at"),
            "acquisition_method": _required_text(acquisition_method, "acquisition_method"),
            "source_version": _required_text(source_version, "source_version"),
            "payload_digest": payload_digest,
            "data_mode": "synthetic",
            "previous_record_hash": self._records[-1]["record_hash"] if self._records else None,
        }
        record["record_hash"] = _record_hash(record)
        self._records.append(record)
        self._evidence_ids.add(normalized_evidence_id)
        return deepcopy(record)

    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(record) for record in self._records)

    def verify(self, records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        candidate = list(self.records()) if records is None else records
        errors: list[dict[str, Any]] = []
        if not isinstance(candidate, list):
            raise ValueError("records must be a list")

        expected_fields = set((*_RECORD_FIELDS, "record_hash"))
        seen_evidence_ids: set[str] = set()
        previous_hash: str | None = None
        for index, record in enumerate(candidate):
            if not isinstance(record, dict):
                errors.append({"index": index, "reason": "record_not_object"})
                continue
            missing = sorted(expected_fields - set(record))
            extra = sorted(set(record) - expected_fields)
            if missing:
                errors.append({"index": index, "reason": "missing_fields", "fields": missing})
                continue
            if extra:
                errors.append({"index": index, "reason": "unexpected_fields", "fields": extra})
            sequence = record["sequence"]
            if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence != index + 1:
                errors.append({"index": index, "reason": "sequence_mismatch"})
            if record["previous_record_hash"] != previous_hash:
                errors.append({"index": index, "reason": "previous_hash_mismatch"})

            evidence_id = record["evidence_id"]
            if not isinstance(evidence_id, str) or not _OPAQUE_ID.fullmatch(evidence_id):
                errors.append({"index": index, "reason": "invalid_evidence_id"})
            elif evidence_id in seen_evidence_ids:
                errors.append({"index": index, "reason": "duplicate_evidence_id"})
            else:
                seen_evidence_ids.add(evidence_id)

            if record["data_mode"] != "synthetic":
                errors.append({"index": index, "reason": "non_synthetic_record"})
            for field in ("event_id", "source", "acquisition_method", "source_version"):
                if not isinstance(record[field], str) or not record[field].strip():
                    errors.append({"index": index, "reason": f"invalid_{field}"})
            try:
                _aware_timestamp(record["observed_at"], f"records[{index}].observed_at")
            except ValueError:
                errors.append({"index": index, "reason": "invalid_timestamp"})
            if not isinstance(record["payload_digest"], str) or not _SHA256.fullmatch(record["payload_digest"]):
                errors.append({"index": index, "reason": "invalid_payload_digest"})
            try:
                calculated_hash = _record_hash(record)
            except (KeyError, TypeError, ValueError):
                errors.append({"index": index, "reason": "invalid_record_shape"})
                calculated_hash = None
            if not isinstance(record["record_hash"], str) or not _SHA256.fullmatch(record["record_hash"]):
                errors.append({"index": index, "reason": "invalid_record_hash"})
                previous_hash = None
            else:
                if calculated_hash is not None and record["record_hash"] != calculated_hash:
                    errors.append({"index": index, "reason": "record_hash_mismatch"})
                previous_hash = record["record_hash"]

        return {
            "valid": not errors,
            "record_count": len(candidate),
            "errors": errors,
            "data_mode": "synthetic",
            "signature_verified": False,
            "source_authenticated": False,
            "payload_digest_verified": False,
            "opaque_ids_semantically_verified": False,
            "durable": False,
            "truthfulness_proven": False,
        }
