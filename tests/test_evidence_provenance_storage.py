import json
import sqlite3

import pytest

from finzanjir_ai.evidence.storage import SQLiteSyntheticEvidenceProvenanceStore


def _append(store, *, chain_id="chain-1", evidence_id="evidence-1", event_id="event-1"):
    return store.append(
        chain_id=chain_id,
        evidence_id=evidence_id,
        event_id=event_id,
        source="synthetic-source",
        observed_at="2026-11-13T09:00:00Z",
        acquisition_method="synthetic_fixture",
        source_version="source-schema-v1",
        payload_digest="a" * 64,
    )


def test_sqlite_store_replays_verified_provenance_after_store_reopen(tmp_path):
    database = tmp_path / "synthetic-evidence.sqlite3"
    first_store = SQLiteSyntheticEvidenceProvenanceStore(database)
    first = _append(first_store)
    second = _append(
        first_store,
        evidence_id="evidence-2",
        event_id="event-2",
    )

    reopened = SQLiteSyntheticEvidenceProvenanceStore(database)
    records = reopened.get_records("chain-1")
    report = reopened.verify("chain-1")

    assert [item["record_hash"] for item in records] == [
        first["record_hash"],
        second["record_hash"],
    ]
    assert report["valid"] is True
    assert report["record_count"] == 2
    assert report["durable"] is True
    assert report["storage_backend"] == "sqlite_local_file"
    assert report["durability_scope"] == "local_filesystem_only"
    assert report["at_rest_encryption"] is False
    assert report["external_trust_anchor"] is False


def test_sqlite_store_refuses_to_extend_a_tampered_existing_chain(tmp_path):
    database = tmp_path / "tampered-evidence.sqlite3"
    store = SQLiteSyntheticEvidenceProvenanceStore(database)
    _append(store)

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT record_json FROM synthetic_evidence_provenance WHERE chain_id = ?",
            ("chain-1",),
        ).fetchone()
        record = json.loads(row[0])
        record["source"] = "tampered-source"
        connection.execute(
            "UPDATE synthetic_evidence_provenance SET record_json = ? WHERE chain_id = ?",
            (json.dumps(record), "chain-1"),
        )

    assert store.verify("chain-1")["valid"] is False
    with pytest.raises(ValueError, match="integrity verification"):
        _append(store, evidence_id="evidence-2", event_id="event-2")
    assert len(store.get_records("chain-1")) == 1


def test_sqlite_store_rejects_duplicate_evidence_ids_and_non_synthetic_data(tmp_path):
    store = SQLiteSyntheticEvidenceProvenanceStore(tmp_path / "synthetic-evidence.sqlite3")
    _append(store)

    with pytest.raises(ValueError, match="duplicate evidence_id"):
        _append(store, evidence_id="evidence-1", event_id="event-2")

    with pytest.raises(ValueError, match="synthetic data only"):
        store.append(
            chain_id="chain-1",
            evidence_id="evidence-2",
            event_id="event-2",
            source="source",
            observed_at="2026-11-13T09:00:00Z",
            acquisition_method="fixture",
            source_version="v1",
            payload_digest="b" * 64,
            data_mode="real",
        )


def test_sqlite_store_keeps_only_metadata_and_isolates_chains(tmp_path):
    database = tmp_path / "synthetic-evidence.sqlite3"
    store = SQLiteSyntheticEvidenceProvenanceStore(database)
    _append(store, chain_id="chain-a")
    _append(store, chain_id="chain-b", evidence_id="evidence-1", event_id="event-1")

    chain_a = store.get_records("chain-a")
    chain_b = store.get_records("chain-b")

    assert len(chain_a) == len(chain_b) == 1
    assert set(chain_a[0]) == {
        "sequence", "evidence_id", "event_id", "source", "observed_at",
        "acquisition_method", "source_version", "payload_digest", "data_mode",
        "previous_record_hash", "record_hash",
    }
    assert "raw_payload" not in chain_a[0]
    assert store.verify("chain-a")["valid"] is True
    assert store.verify("chain-b")["valid"] is True
