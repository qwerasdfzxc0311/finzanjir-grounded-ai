"""Synthetic-only replay, evidence-reference and stream-disconnect tests."""

import asyncio
import threading

from fastapi.testclient import TestClient

import finzanjir_api.app as api_module
from finzanjir_api.app import app
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events
from finzanjir_ai.storage.prototype_history import PrototypeRunStore


client = TestClient(app)


def _payload(transaction_id: str, *, shadow_mode: bool = False) -> dict:
    occurred_at = "2026-11-12T09:00:00Z"
    return {
        "transaction_id": transaction_id,
        "bank_id": "bank-synthetic-replay",
        "actor_id": "actor-replay-test",
        "amount": 2500,
        "occurred_at": occurred_at,
        "synthetic": True,
        "signal_events": build_synthetic_case_signal_events(
            transaction_id=transaction_id,
            observed_at=occurred_at,
        ),
        "shadow_mode": shadow_mode,
    }


def _frames(response):
    import json

    parsed = []
    for frame in response.text.strip().split("\\n\\n"):
        lines = frame.splitlines()
        if len(lines) >= 2 and lines[0].startswith("event: ") and lines[1].startswith("data: "):
            parsed.append((lines[0][7:], json.loads(lines[1][6:])))
    return parsed


def test_duplicate_evidence_replay_does_not_inflate_risk_or_evidence_count():
    payload = _payload("TX-REPLAY-EVIDENCE-001")
    payload["signal_events"].append(dict(payload["signal_events"][0]))

    response = client.post("/api/prototype/run", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["pipeline"]["risk"]["score"] == 80
    assert body["pipeline"]["risk"]["evidence_count"] == 5
    assert len(body["pipeline"]["signals"]) == 5
    assert len(body["pipeline"]["evidences"]) == 5
    assert body["pipeline"]["risk"]["deduplicated_evidence_ids"] == [
        f"TX-REPLAY-EVIDENCE-001:synthetic:auth"
    ]


def test_identical_transaction_replay_is_not_idempotent_and_creates_two_run_records(monkeypatch, tmp_path):
    database_path = tmp_path / "replay-history.sqlite3"
    store = PrototypeRunStore(database_path)
    monkeypatch.setattr(api_module, "prototype_run_store", lambda: store)
    payload = _payload("TX-REPLAY-REQUEST-001", shadow_mode=True)

    first = client.post("/api/prototype/run", json=payload)
    second = client.post("/api/prototype/run", json=payload)

    assert first.status_code == second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["pipeline"]["risk"]["id"] == second_body["pipeline"]["risk"]["id"]
    assert first_body["prototype_run_id"] != second_body["prototype_run_id"]
    assert len(store.list_recent()) == 2


def test_window_trace_preserves_evidence_references_across_all_eight_windows(monkeypatch):
    class InMemoryRunStore:
        def save(self, _summary):
            return {"run_id": "run-reference-transfer-test"}

    monkeypatch.setattr(api_module, "prototype_run_store", lambda: InMemoryRunStore())
    response = client.post("/api/prototype/run", json=_payload("TX-REF-TRANSFER-001"))

    assert response.status_code == 200
    body = response.json()
    trace = body["window_trace"]
    assert [item["window_id"] for item in trace] == [
        "synthetic_bank",
        "signal_risk",
        "cross_bank_fraud",
        "human_case",
        "audit_kpi",
        "finzanjir_ai",
        "citizen",
        "layers_16",
    ]

    bank, signal, cross_bank, human, audit, ai, citizen, layers = trace
    risk_id = body["pipeline"]["risk"]["id"]
    case_id = body["case"]["case_id"]
    decision_id = body["decision"]["human_decision"]["decision_id"]
    audit_id = body["decision"]["audit_event"]["audit_id"]
    signal_ids = {item["id"] for item in body["pipeline"]["signals"]}
    evidence_ids = {item["id"] for item in body["pipeline"]["evidences"]}

    assert bank["output_refs"] == ["TX-REF-TRANSFER-001"]
    assert signal["input_refs"] == bank["output_refs"]
    assert signal_ids.issubset(set(signal["output_refs"]))
    assert evidence_ids.issubset(set(signal["output_refs"]))
    assert risk_id in signal["output_refs"]
    assert cross_bank["status"] == "DISABLED"
    assert cross_bank["input_refs"] == []
    assert risk_id in human["input_refs"]
    assert case_id in human["output_refs"]
    assert decision_id in human["output_refs"]
    assert audit["input_refs"] == ["TX-REF-TRANSFER-001"]
    assert audit_id in audit["output_refs"]
    assert {risk_id, case_id, decision_id, audit_id}.issubset(set(ai["input_refs"]))
    assert signal_ids.issubset(set(ai["input_refs"]))
    assert evidence_ids.issubset(set(ai["input_refs"]))
    assert decision_id in citizen["input_refs"]
    assert case_id in citizen["output_refs"]
    assert layers["input_refs"] == ["TX-REF-TRANSFER-001"]
    assert len(layers["output_refs"]) == 16


def test_closing_stream_consumer_does_not_cancel_synthetic_core_run(monkeypatch):
    persisted = threading.Event()
    execution_returned = threading.Event()

    class RecordingRunStore:
        def save(self, _summary):
            persisted.set()
            return {"run_id": "run-disconnect-test"}

    monkeypatch.setattr(api_module, "prototype_run_store", lambda: RecordingRunStore())
    original_execute = api_module._execute_prototype

    def tracked_execute(*args, **kwargs):
        try:
            return original_execute(*args, **kwargs)
        finally:
            execution_returned.set()

    monkeypatch.setattr(api_module, "_execute_prototype", tracked_execute)

    async def exercise():
        request = api_module.PrototypeTransaction(**_payload("TX-STREAM-DISCONNECT-001"))
        response = await api_module.stream_prototype(request)
        iterator = response.body_iterator

        first_frame = await anext(iterator)
        assert first_frame.startswith("event: stage")
        await iterator.aclose()

        assert await asyncio.to_thread(execution_returned.wait, 5)
        assert persisted.is_set()
        await asyncio.sleep(0.05)

    asyncio.run(exercise())
