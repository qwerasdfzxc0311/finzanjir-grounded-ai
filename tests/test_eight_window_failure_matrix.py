"""Synthetic-only failure injection matrix for the eight-window streaming flow."""

import asyncio
import json
import sqlite3
import threading

from fastapi.testclient import TestClient

import finzanjir_api.app as api_module
from finzanjir_api.app import app
from finzanjir_ai.case.manager import CaseManager
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

    # Assert every completed window reached its own terminal state before the
    # failure, the failing window emitted RUNNING then FAILED, and later
    # windows were never entered. The AI terminal state is intentionally
    # allowed to be either COMPLETED or ABSTAINED.
    terminal_statuses = {
        "synthetic_bank": {"COMPLETED"},
        "signal_risk": {"COMPLETED"},
        "cross_bank_fraud": {"DISABLED"},
        "human_case": {"SYNTHETIC_REVIEW_ONLY", "SHADOW_ONLY", "NOT_ELIGIBLE"},
        "audit_kpi": {"COMPLETED"},
        "finzanjir_ai": {"COMPLETED", "ABSTAINED"},
        "citizen": {"SYNTHETIC_STATUS_ONLY"},
        "layers_16": {"PARTIAL"},
    }
    expected_statuses = []
    for position, window_id in enumerate(WINDOWS):
        if position < index:
            expected_statuses.extend(["RUNNING", terminal_statuses[window_id]])
        elif position == index:
            expected_statuses.extend(["RUNNING", "FAILED"])
        else:
            expected_statuses.append("NOT_RUN")

    actual_statuses = [item["status"] for item in stages]
    assert len(actual_statuses) == len(expected_statuses)
    for actual, expected in zip(actual_statuses, expected_statuses):
        if isinstance(expected, set):
            assert actual in expected
        else:
            assert actual == expected

    failed = [item for item in stages if item["status"] == "FAILED"]
    assert len(failed) == 1
    assert failed[0]["window_id"] == failed_window
    assert failed[0]["sequence"] == index + 1
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


def test_stream_citizen_window_failure_marks_citizen_failed_and_layers_not_run(monkeypatch):
    original_apply = CaseManager.apply_human_decision

    class BrokenCitizenStatus(dict):
        def __bool__(self):
            raise RuntimeError("synthetic citizen status serialization failure")

    def fail_at_citizen_status(self, *args, **kwargs):
        result = original_apply(self, *args, **kwargs)
        result["citizen_status"] = BrokenCitizenStatus()
        return result

    monkeypatch.setattr(
        "finzanjir_ai.prototype.flow.CaseManager.apply_human_decision",
        fail_at_citizen_status,
    )
    response = client.post(
        "/api/prototype/run/stream",
        json=_payload("TX-FAIL-CITIZEN-001"),
    )
    _assert_stopped_at(response, "citizen")


def test_stream_storage_failure_is_not_automatically_retried(monkeypatch):
    class FailOnceRunStore:
        def __init__(self):
            self.calls = 0

        def save(self, _summary):
            self.calls += 1
            raise sqlite3.OperationalError("synthetic storage busy")

    store = FailOnceRunStore()
    monkeypatch.setattr(api_module, "prototype_run_store", lambda: store)
    response = client.post(
        "/api/prototype/run/stream",
        json=_payload("TX-STORAGE-NO-RETRY-001"),
    )

    frames = _frames(response)
    errors = [data for name, data in frames if name == "error"]
    results = [data for name, data in frames if name == "result"]
    assert response.status_code == 200
    assert store.calls == 1
    assert errors == [{
        "status_code": 503,
        "detail": "Prototype run could not be safely saved.",
    }]
    assert results == []


def test_asgi_http_disconnect_after_first_stage_does_not_cancel_synthetic_worker(monkeypatch):
    persisted = threading.Event()
    release_worker = threading.Event()
    first_stage_seen = threading.Event()

    class RecordingRunStore:
        def save(self, _summary):
            persisted.set()
            return {"run_id": "run-asgi-disconnect-test"}

    monkeypatch.setattr(api_module, "prototype_run_store", lambda: RecordingRunStore())
    original_execute = api_module._execute_prototype

    def gated_execute(transaction, *, on_stage=None):
        def gated_on_stage(event):
            if on_stage is not None:
                on_stage(event)
            if event.get("window_id") == "synthetic_bank" and event.get("status") == "RUNNING":
                first_stage_seen.set()
                release_worker.wait(5)

        return original_execute(transaction, on_stage=gated_on_stage)

    monkeypatch.setattr(api_module, "_execute_prototype", gated_execute)

    async def exercise():
        body = json.dumps(_payload("TX-ASGI-DISCONNECT-001")).encode()
        request_sent = False
        disconnect = asyncio.Event()
        sent_bodies = []

        async def receive():
            nonlocal request_sent
            if not request_sent:
                request_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            await disconnect.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.body" and message.get("body"):
                sent_bodies.append(message["body"])
                if len(sent_bodies) == 1:
                    release_worker.set()
                    disconnect.set()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/prototype/run/stream",
            "raw_path": b"/api/prototype/run/stream",
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"host", b"testserver"),
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }

        try:
            await asyncio.wait_for(app(scope, receive, send), timeout=5)
            assert sent_bodies
            assert b"event: stage" in sent_bodies[0]
            assert await asyncio.to_thread(first_stage_seen.wait, 5)
            assert await asyncio.to_thread(persisted.wait, 5)
        finally:
            release_worker.set()

    asyncio.run(exercise())


def test_stream_synthetic_bank_preflight_failure_marks_first_window_failed(monkeypatch):
    payload = _payload("TX-FAIL-SYNTHETIC-BANK-001")
    payload["synthetic"] = False

    response = client.post("/api/prototype/run/stream", json=payload)

    frames = _frames(response)
    stages = [data for name, data in frames if name == "stage"]
    errors = [data for name, data in frames if name == "error"]
    results = [data for name, data in frames if name == "result"]
    assert response.status_code == 200
    assert [item["window_id"] for item in stages] == list(WINDOWS)
    assert [item["status"] for item in stages] == ["FAILED"] + ["NOT_RUN"] * 7
    assert stages[0]["sequence"] == 1
    assert errors == [{
        "status_code": 400,
        "detail": "The prototype flow accepts only explicitly synthetic transactions.",
    }]
    assert results == []


def test_stream_human_case_failure_marks_case_window_failed_and_stops_later_windows(monkeypatch):
    def fail_open_case(*_args, **_kwargs):
        raise RuntimeError("synthetic case manager unavailable")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.CaseManager.open_case", fail_open_case)
    response = client.post(
        "/api/prototype/run/stream",
        json=_payload("TX-FAIL-HUMAN-CASE-001"),
    )
    _assert_stopped_at(response, "human_case")


def test_stream_finzanjir_ai_failure_marks_ai_window_failed_and_stops_later_windows(monkeypatch):
    def fail_answer(*_args, **_kwargs):
        raise RuntimeError("synthetic grounded answer unavailable")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.FINZANJIRAI.answer", fail_answer)
    response = client.post(
        "/api/prototype/run/stream",
        json=_payload("TX-FAIL-AI-001"),
    )
    _assert_stopped_at(response, "finzanjir_ai")


def test_stream_layers_16_failure_marks_architecture_window_failed(monkeypatch):
    def fail_layer_trace(*_args, **_kwargs):
        raise RuntimeError("synthetic layer registry unavailable")

    monkeypatch.setattr("finzanjir_ai.prototype.flow.SystemFlow._layer_trace", fail_layer_trace)
    response = client.post(
        "/api/prototype/run/stream",
        json=_payload("TX-FAIL-LAYERS-16-001"),
    )
    _assert_stopped_at(response, "layers_16")
