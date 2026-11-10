from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping

_TOKEN_RE = re.compile(r"[^\\W_]+", re.UNICODE)


@dataclass(frozen=True)
class NormalizedKnowledgeRecord:
    record_id: str
    concept_id: str
    statement: str
    aliases: tuple[str, ...]
    evidence: Any
    provenance: tuple[Any, ...]
    reconciliation: Any

    @property
    def searchable_text(self) -> str:
        return " ".join((self.statement, *self.aliases))


@dataclass(frozen=True)
class KnowledgeIndex:
    records: tuple[NormalizedKnowledgeRecord, ...]
    _term_to_record_ids: dict[str, tuple[str, ...]]
    _concept_to_record_ids: dict[str, tuple[str, ...]]

    def record_ids_for_term(self, term: str) -> tuple[str, ...]:
        return self._term_to_record_ids.get(_normalize_text(term), ())

    def record_ids_for_concept(self, concept_id: str) -> tuple[str, ...]:
        return self._concept_to_record_ids.get(str(concept_id), ())

    def get_record(self, record_id: str) -> NormalizedKnowledgeRecord | None:
        for record in self.records:
            if record.record_id == record_id:
                return record
        return None


def _normalize_text(value: str) -> str:
    return " ".join(str(value).strip().casefold().split())


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(_normalize_text(token) for token in _TOKEN_RE.findall(value))


def _as_aliases(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if item is not None and str(item).strip())
    return (str(value),)


def _as_provenance(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def normalize_record(record: Mapping[str, Any]) -> NormalizedKnowledgeRecord:
    """Create the stable runtime representation without changing source semantics."""
    record_id = str(record["id"])
    concept_id = str(record.get("canonical_concept_id") or record.get("concept_id"))
    statement = str(record.get("statement") or "").strip()
    aliases = _as_aliases(record.get("aliases"))
    return NormalizedKnowledgeRecord(
        record_id=record_id,
        concept_id=concept_id,
        statement=statement,
        aliases=aliases,
        evidence=record.get("evidence"),
        provenance=_as_provenance(record.get("provenance")),
        reconciliation=record.get("reconciliation"),
    )


def build_knowledge_index(records: Iterable[Mapping[str, Any]]) -> KnowledgeIndex:
    """Build deterministic lexical and canonical-concept indexes in source order."""
    normalized = tuple(normalize_record(record) for record in records)
    term_ids: dict[str, list[str]] = {}
    concept_ids: dict[str, list[str]] = {}

    for record in normalized:
        concept_ids.setdefault(record.concept_id, []).append(record.record_id)
        for token in _tokens(record.searchable_text):
            if token:
                term_ids.setdefault(token, []).append(record.record_id)

    return KnowledgeIndex(
        records=normalized,
        _term_to_record_ids={key: tuple(value) for key, value in term_ids.items()},
        _concept_to_record_ids={key: tuple(value) for key, value in concept_ids.items()},
    )


def build_index_from_document(document: Mapping[str, Any]) -> KnowledgeIndex:
    """Build the runtime index from a validated canonical corpus document."""
    records = document.get("records")
    if not isinstance(records, list):
        raise ValueError("Canonical knowledge records must be a list")
    return build_knowledge_index(records)
