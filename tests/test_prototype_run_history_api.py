from fastapi.testclient import TestClient

import finzanjir_api.app as api_module
from finzanjir_api.app import app
from finzanjir_ai.storage.prototype_history import PrototypeRunStore


client = TestClient(app)


def test_prototype_run_endpoint_persists_only_sanitized_aggregate_history(monkeypatch, tmp_path):
    database_path = tmp_path / "prototype.sqlite3"
    monkeypatch.setattr(
        api_module,
        "prototype_run_store",
        lambda: PrototypeRunStore(database_path),
    )

    response = client.post(
        "/api/prototype/run",
        json={
            "transaction_id": "TX-HISTORY-PRIVATE-001",
            "bank_id": "bank-synthetic-a",
            "actor_id": "synthetic-person-001",
            "amount": 2500,
            "occurred_at": "2026-11-12T09:00:00Z",
            "synthetic": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["prototype_run_id"].startswith("run-")

    history = client.get("/api/prototype/runs")
    assert history.status_code == 200
    body = history.json()
    assert body["data_mode"] == "synthetic"
    assert body["count"] == 1
    assert body["runs"][0]["signal_count"] == 1
    assert body["runs"][0]["risk_score"] == 0
    assert "TX-HISTORY-PRIVATE-001" not in history.text
    assert "bank-synthetic-a" not in history.text
    assert "synthetic-person-001" not in history.text
    assert "privacy_note" in body


def test_prototype_run_history_endpoint_bounds_requested_limit():
    response = client.get("/api/prototype/runs?limit=101")
    assert response.status_code == 422
