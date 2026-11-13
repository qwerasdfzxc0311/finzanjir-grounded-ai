"""Synthetic-only failure injection matrix for the eight-window streaming flow."""

import json

from fastapi.testclient import TestClient

from finzanjir_api.app import app
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events


client = TestClient(app)
WINDOWS = (
    "synthetic_bank",
    "signal_risk",
    "cross_bank_fraud",
    "human_case",
    "audit_kpi",
    "finzanjir_ai",
    "citizen",
    "layers_16",
)


def _payload(transaction_id: str, *, shadow_mode: bool = False) -> dict:
    occurred_at = "2026-11-12T09:00:00Z"
    return {
        "transaction_id": transaction_id,
        "bank_id": "bank-synthetic-a",
        "actor_id": "actor-failure-matrix",
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
    parsed = []
    for frame in response.text.strip().split("\n\n"):
        lines = frame.splitlines()
        if len(lines) >= 2 and lines[0].startswith("event: ") and lines[1].startswith("data: "):
            parsed.append((lines[0][7:], json.loads(lines[1][6:])))
    return parsed


def _assert_stopped_at(response, failed_window: str, expected_status_code: int = 500):
    frames = _frames(response)
    stages = [data for name, data in frames if name == "stage"]
    errors = [data for name, data in frames if name == "error"]
    results = [data for name, data in frames if name == "result"]
    index = WINDOWS.index(failed_window)
    expected_windows = [
        window
        for position, window in enumerate(WINDOWS)
        for _ in range(2 if position <= index else 1)
    ]

    assert response.status_code == 200
    assert [item["window_id"] for item in stages] == expected_windows
    failed = [item for item in stages if item["status"] == "FAILED"]
    assert len(failed) == 1
    assert failed[0]["window_id"] == failed_window
    assert failed[0]["sequence"] == index + 1
    assert [item["status"] for item in stages if item["sequence"] > index + 1] == [
        "NOT_RUN"
    ] * (len(WINDOWS) - index - 1)
    assert errors == [{"status_code": expected_status_code, "detail": "Prototype flow failed safely."}]
    assert results == []


def test_stream_threshold_manager_failure_marks_signal_risk_failed_and_later_windows_not_run(monkeypatch):
    def fail_threshold(*_args, **_kwargs):
        raise RuntimeError("synthetic threshold registry unavailable")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.ThresholdManager.get_active", fail_threshold)
    response = client.post("/api/prototype/run/stream", json=_payload("TX-FAIL-THRESHOLD-001"))
    _assert_stopped_at(response, "signal_risk")


def test_stream_cross_bank_matcher_exception_fails_closed_and_stops_later_windows(monkeypatch):
    def fail_match(*_args, **_kwargs):
        raise RuntimeError("synthetic cross-bank matcher failure")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.CrossBankMatcher.match", fail_match)
    response = client.post("/api/prototype/run/stream", json=_payload("TX-FAIL-CROSS-BANK-001"))
    _assert_stopped_at(response, "cross_bank_fraud")


def test_stream_kpi_failure_marks_audit_window_failed_in_shadow_path(monkeypatch):
    def fail_kpi(*_args, **_kwargs):
        raise RuntimeError("synthetic KPI calculation failure")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.calculate_kpis", fail_kpi)
    response = client.post(
        "/api/prototype/run/stream",
        json=_payload("TX-FAIL-KPI-001", shadow_mode=True),
    )
    _assert_stopped_at(response, "audit_kpi")


def test_audit_kpi_window_records_complete_runtime_provenance_in_both_modes(monkeypatch):
    class InMemoryRunStore:
        def save(self, _summary):
            return {"run_id": "run-audit-provenance-test"}

    monkeypatch.setattr("finzanjir_api.app.prototype_run_store", lambda: InMemoryRunStore())

    for shadow_mode in (False, True):
        transaction_id = f"TX-AUDIT-PROVENANCE-{'SHADOW' if shadow_mode else 'CASE'}"
        response = client.post(
            "/api/prototype/run/stream",
            json=_payload(transaction_id, shadow_mode=shadow_mode),
        )
        assert response.status_code == 200
        frames = _frames(response)
        stage_events = [data for name, data in frames if name == "stage"]
        result_events = [data for name, data in frames if name == "result"]
        assert len(result_events) == 1

        audit_events = [item for item in stage_events if item["window_id"] == "audit_kpi"]
        assert [item["status"] for item in audit_events] == ["RUNNING", "COMPLETED"]
        trace = result_events[0]["window_trace"]
        audit_trace = next(item for item in trace if item["window_id"] == "audit_kpi")

        previously_emitted_refs = {
            ref
            for item in trace
            if item["sequence"] < audit_trace["sequence"]
            for ref in item["output_refs"]
        }
        assert transaction_id in previously_emitted_refs
        assert set(audit_events[0]["input_refs"]) == previously_emitted_refs
        assert set(audit_events[1]["input_refs"]) == previously_emitted_refs
        assert set(audit_trace["input_refs"]) == previously_emitted_refs
        assert audit_events[1]["output_refs"] == audit_trace["output_refs"]
        assert audit_trace["output_refs"]
