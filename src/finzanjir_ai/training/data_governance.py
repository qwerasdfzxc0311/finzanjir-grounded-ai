from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
import unicodedata
from typing import Iterable


SUPPORTED_LANGUAGES = frozenset({
    "uz-Latn", "uz-Cyrl", "kaa-Latn", "kaa-Cyrl", "kk", "ru", "en",
})
APPROVED_LICENSES = frozenset({
    "CC0-1.0", "CC-BY-4.0", "public-domain",
    "author-granted", "custom-training-grant",
})
APPROVED_DATA_CLASSES = frozenset({"public", "licensed_nonpersonal"})
APPROVED_SOURCE_TYPES = frozenset({"public_domain", "licensed_corpus", "author_provided"})


@dataclass(frozen=True)
class TrainingExample:
    input_text: str
    target_text: str
    language: str
    task_type: str
    source_id: str
    source_uri: str
    license_id: str
    verified: bool
    permission_ref: str | None = None
    contains_personal_data: bool = False
    contains_financial_data: bool = False
    data_class: str = "unknown"
    source_type: str = "unknown"


@dataclass(frozen=True)
class AcceptedExample:
    example_id: str
    input_text: str
    target_text: str
    language: str
    task_type: str
    source_id: str
    source_uri: str
    license_id: str
    permission_ref: str | None
    data_class: str
    source_type: str


@dataclass(frozen=True)
class DatasetReadiness:
    ready: bool
    total_examples: int
    counts_by_language: dict[str, int]
    missing_languages: tuple[str, ...]
    rejected_examples: int
    reviewer_approved: bool
    reasons: tuple[str, ...]


def _normalize_for_dedup(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(text.split())


def _contains_sensitive_identifier(value: str) -> bool:
    # This is only a conservative screening layer, not complete PII detection.
    patterns = (
        r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)",
        r"(?<!\w)[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?!\w)",
        r"(?<!\d)\+?998[\s().-]?(?:\d[\s().-]?){9}(?!\d)",
        r"(?<!\d)\+\d{1,3}(?:[\s().-]?\d){7,14}(?!\d)",
        r"(?<![A-Z0-9])[A-Z]{2}[\s-]?\d{7}(?![A-Z0-9])",
    )
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


class TrainingDatasetBuilder:
    """Collects reviewed, licensed examples; it does not train or persist a model."""

    def __init__(self, *, dataset_version: str) -> None:
        if not dataset_version.strip():
            raise ValueError("dataset_version is required")
        self.dataset_version = dataset_version.strip()
        self._accepted: list[AcceptedExample] = []
        self._seen: set[str] = set()
        self._rejected: list[str] = []

    def add(self, example: TrainingExample) -> bool:
        if not example.input_text.strip() or not example.target_text.strip():
            return self._reject("empty_input_or_target")
        if example.language not in SUPPORTED_LANGUAGES:
            return self._reject("unsupported_language")
        if example.license_id not in APPROVED_LICENSES:
            return self._reject("license_not_approved")
        if not example.source_id.strip() or not example.source_uri.strip():
            return self._reject("missing_source_provenance")
        if not example.source_uri.startswith(("https://", "local://")):
            return self._reject("unsupported_source_uri")
        if example.data_class not in APPROVED_DATA_CLASSES:
            return self._reject("data_class_not_approved")
        if example.source_type not in APPROVED_SOURCE_TYPES:
            return self._reject("source_type_not_approved")
        if not example.verified:
            return self._reject("source_not_verified")
        if example.contains_personal_data or example.contains_financial_data:
            return self._reject("personal_or_financial_data_forbidden")
        if example.license_id in {"author-granted", "custom-training-grant"} and not (example.permission_ref or "").strip():
            return self._reject("missing_training_permission_reference")

        combined = example.input_text + "\n" + example.target_text
        if _contains_sensitive_identifier(combined):
            return self._reject("sensitive_identifier_detected")

        fingerprint = sha256(
            (_normalize_for_dedup(example.input_text) + "\n" + _normalize_for_dedup(example.target_text)).encode("utf-8")
        ).hexdigest()
        if fingerprint in self._seen:
            return self._reject("duplicate_example")

        example_id = fingerprint[:20]
        self._accepted.append(AcceptedExample(
            example_id=example_id,
            input_text=example.input_text.strip(),
            target_text=example.target_text.strip(),
            language=example.language,
            task_type=example.task_type.strip() or "general",
            source_id=example.source_id.strip(),
            source_uri=example.source_uri.strip(),
            license_id=example.license_id,
            permission_ref=example.permission_ref,
            data_class=example.data_class,
            source_type=example.source_type,
        ))
        self._seen.add(fingerprint)
        return True

    def _reject(self, reason: str) -> bool:
        self._rejected.append(reason)
        return False

    def readiness(
        self,
        *,
        required_languages: Iterable[str],
        minimum_per_language: int,
        reviewer_approved: bool = False,
    ) -> DatasetReadiness:
        if minimum_per_language < 1:
            raise ValueError("minimum_per_language must be at least 1")
        required = tuple(dict.fromkeys(required_languages))
        if not required:
            raise ValueError("required_languages must not be empty")
        counts = Counter(item.language for item in self._accepted)
        missing = tuple(
            language for language in required
            if language not in SUPPORTED_LANGUAGES or counts[language] < minimum_per_language
        )
        reasons: list[str] = []
        if missing:
            reasons.append("minimum_language_coverage_not_met")
        if self._rejected:
            reasons.append("rejected_examples_require_review")
        if not reviewer_approved:
            reasons.append("human_dataset_review_not_approved")
        return DatasetReadiness(
            ready=not reasons,
            total_examples=len(self._accepted),
            counts_by_language=dict(sorted(counts.items())),
            missing_languages=missing,
            rejected_examples=len(self._rejected),
            reviewer_approved=reviewer_approved,
            reasons=tuple(reasons),
        )

    def export_jsonl(self) -> str:
        """Return a provenance-preserving staging export; caller decides where to save it."""
        rows = []
        for item in self._accepted:
            rows.append(json.dumps(asdict(item), ensure_ascii=False, sort_keys=True))
        return "\n".join(rows)

    def manifest(self) -> dict[str, object]:
        counts = Counter(item.language for item in self._accepted)
        return {
            "dataset_version": self.dataset_version,
            "total_examples": len(self._accepted),
            "counts_by_language": dict(sorted(counts.items())),
            "rejected_examples": len(self._rejected),
            "rejection_reasons": dict(sorted(Counter(self._rejected).items())),
            "training_started": False,
            "model_training_enabled": False,
        }
