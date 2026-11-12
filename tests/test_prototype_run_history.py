from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from finzanjir_ai.storage.prototype_history import PrototypeRunStore


def _summary(**overrides):
    result = {
        "data_mode": "synthetic",
        "risk_score": 82.5,
        "risk_level": "HIGH",
        "threshold": 75,
        "signal_count": 5,
        "evidence_count": 5,
        "independent_families": 4,
        "case_eligible": True,
        "case_opened": True,
        "shadow_mode": False,
        "engine_version": "multi-signal-shadow-v1",
        "registry_version": "signal-registry-v1",
    }
    result.update(overrides)
    return result


def test_run_history_persists_aggregate_summaries_across_store_instances(tmp_path):
    path = tmp_path / "nested" / "prototype.sqlite3"
    first_store = PrototypeRunStore(path)
    saved = first_store.save(_summary())

    reopened_store = PrototypeRunStore(path)
    runs = reopened_store.list_recent()

    assert len(runs) == 1
    assert runs[0]["run_id"] == saved["run_id"]
    assert runs[0]["risk_score"] == 82.5
    assert runs[0]["case_opened"] is True
    assert runs[0]["data_mode"] == "synthetic"


def test_run_history_never_persists_raw_transaction_or_identity_fields(tmp_path):
    store = PrototypeRunStore(tmp_path / "prototype.sqlite3")
    saved = store.save({
        **_summary(),
        "transaction_id": "TX-REAL-LIKE-123",
        "citizen_id": "citizen-secret",
        "device_id": "device-secret",
        "account_number": "account-secret",
        "raw_evidence": {"recipient": "person"},
    })

    runs = store.list_recent()
    assert runs[0]["run_id"] == saved["run_id"]
    forbidden = {"transaction_id", "citizen_id", "device_id", "account_number", "raw_evidence"}
    assert forbidden.isdisjoint(runs[0])
    with sqlite3.connect(store.database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(prototype_run_history)")}
    assert forbidden.isdisjoint(columns)


@pytest.mark.parametrize(
    "overrides",
    [
        {"data_mode": "real"},
        {"risk_score": float("nan")},
        {"risk_score": 101},
        {"threshold": -1},
        {"signal_count": True},
        {"case_opened": 1},
        {"risk_level": "GUILTY"},
        {"engine_version": ""},
    ],
)
def test_run_history_rejects_invalid_or_non_synthetic_summaries(tmp_path, overrides):
    store = PrototypeRunStore(tmp_path / "prototype.sqlite3")
    with pytest.raises(ValueError):
        store.save(_summary(**overrides))


@pytest.mark.parametrize("limit", [0, 101, True, "10"])
def test_run_history_validates_list_limit(tmp_path, limit):
    store = PrototypeRunStore(tmp_path / "prototype.sqlite3")
    with pytest.raises(ValueError):
        store.list_recent(limit=limit)


def test_run_history_enforces_retention_window(tmp_path):
    store = PrototypeRunStore(tmp_path / "prototype.sqlite3", retention_days=1)
    store.save(_summary())
    old_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(store.database_path) as connection:
        connection.execute(
            "UPDATE prototype_run_history SET created_at = ?",
            (old_time,),
        )

    assert store.list_recent() == []


def test_run_history_rejects_invalid_retention_configuration(tmp_path):
    with pytest.raises(ValueError, match="retention_days"):
        PrototypeRunStore(tmp_path / "prototype.sqlite3", retention_days=0)
