"""Synthetic-only live SSE integration test for the eight-window progress flow."""

import asyncio
import json
import threading

import pytest

import finzanjir_api.app as api_module
from finzanjir_api.app import app
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events

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

TERMINAL_STATUS = {
    "synthetic_bank": {"COMPLETED"},
    "signal_risk": {"COMPLETED"},
    "cross_bank_fraud": {"DISABLED"},
    "human_case": {"SYNTHETIC_REVIEW_ONLY", "SHADOW_ONLY", "NOT_ELIGIBLE"},
    "audit_kpi": {"COMPLETED"},
    "finzanjir_ai": {"COMPLETED", "ABSTAINED"},
    "citizen": {"SYNTHETIC_STATUS_ONLY"},
    "layers_16": {"PARTIAL"},
}


@pytest.mark.parametrize(
    ("scenario", "shadow_mode", "expected_human_status"),
    [
        ("normal-case", False, "SYNTHETIC_REVIEW_ONLY"),
        ("shadow-mode", True, "SHADOW_ONLY"),
        ("not-eligible", False, "NOT_ELIGIBLE"),
    ],
)
def test_sse_delivers_all_eight_window_updates_progressively(
    monkeypatch, scenario, shadow_mode, expected_human_status
):
    # Hold the worker after each window's terminal event. The ASGI send callback
    # releases it only after that event has reached the response stream.
    gates = {window_id: threading.Event() for window_id in WINDOWS}
    gate_timeouts = []
    late_terminal_events = []
    worker_finished = threading.Event()
    persisted = threading.Event()

    class RecordingRunStore:
        def save(self, _summary):
            persisted.set()
            return {"run_id": "run-eight-window-live-progress-test"}

    monkeypatch.setattr(api_module, "prototype_run_store", lambda: RecordingRunStore())
    original_execute = api_module._execute_prototype

    def gated_execute(transaction, *, on_stage=None):
        def gated_on_stage(event):
            if on_stage is not None:
                on_stage(event)
            if event.get("status") not in {"RUNNING", "FAILED", "NOT_RUN"}:
                window_id = event["window_id"]
                if not gates[window_id].wait(3):
                    gate_timeouts.append(window_id)

        result = original_execute(transaction, on_stage=gated_on_stage)
        worker_finished.set()
        return result

    monkeypatch.setattr(api_module, "_execute_prototype", gated_execute)

    async def exercise_stream():
        transaction_id = f"TX-EIGHT-WINDOW-LIVE-SSE-{scenario.upper()}-001"
        occurred_at = "2026-11-18T09:00:00Z"
        payload = {
            "transaction_id": transaction_id,
            "bank_id": "bank-synthetic-a",
            "actor_id": "actor-live-progress",
            "amount": 2500,
            "occurred_at": occurred_at,
            "synthetic": True,
            "signal_events": (
                build_synthetic_case_signal_events(
                    transaction_id=transaction_id,
                    observed_at=occurred_at,
                )[:1]
                if scenario == "not-eligible"
                else build_synthetic_case_signal_events(
                    transaction_id=transaction_id,
                    observed_at=occurred_at,
                )
            ),
            "shadow_mode": shadow_mode,
        }
        body = json.dumps(payload).encode()
        request_sent = False
        disconnect = asyncio.Event()
        stage_events = []
        result_events = []
        error_events = []
        response_status = None

        async def receive():
            nonlocal request_sent
            if not request_sent:
                request_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            await disconnect.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            if message["type"] != "http.response.body":
                return

            chunk = message.get("body", b"")
            if chunk:
                for frame in chunk.decode().split("\n\n"):
                    lines = frame.splitlines()
                    event_line = next((line for line in lines if line.startswith("event: ")), None)
                    data_line = next((line for line in lines if line.startswith("data: ")), None)
                    if not event_line or not data_line:
                        continue
                    event_name = event_line[7:]
                    data = json.loads(data_line[6:])
                    if event_name == "stage":
                        stage_events.append(data)
                        if data.get("status") not in {"RUNNING", "FAILED", "NOT_RUN"}:
                            window_id = data["window_id"]
                            if worker_finished.is_set():
                                late_terminal_events.append(window_id)
                            gates[window_id].set()
                    elif event_name == "result":
                        result_events.append(data)
                    elif event_name == "error":
                        error_events.append(data)

            if not message.get("more_body", False):
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
            await asyncio.wait_for(app(scope, receive, send), timeout=20)
        finally:
            for gate in gates.values():
                gate.set()
            disconnect.set()

        assert response_status == 200
        assert len(stage_events) == 16
        assert [event["window_id"] for event in stage_events] == [
            window_id for window_id in WINDOWS for _ in range(2)
        ]
        assert [event["status"] for event in stage_events[::2]] == ["RUNNING"] * 8
        expected_terminal_statuses = dict(TERMINAL_STATUS)
        expected_terminal_statuses["human_case"] = {expected_human_status}
        for window_id, event in zip(WINDOWS, stage_events[1::2]):
            assert event["window_id"] == window_id
            assert event["status"] in expected_terminal_statuses[window_id]
        assert not gate_timeouts
        assert not late_terminal_events
        assert not error_events
        assert len(result_events) == 1
        assert persisted.is_set()
        trace = result_events[0]["window_trace"]
        assert len(trace) == len(WINDOWS) == 8
        available_refs = set()
        for index, window_id in enumerate(WINDOWS):
            running, terminal = stage_events[index * 2:index * 2 + 2]
            trace_stage = trace[index]
            assert running["window_id"] == terminal["window_id"] == trace_stage["window_id"] == window_id
            assert running["sequence"] == terminal["sequence"] == trace_stage["sequence"] == index + 1
            assert running["input_refs"] == terminal["input_refs"] == trace_stage["input_refs"]
            assert terminal["output_refs"] == trace_stage["output_refs"]
            assert set(running["input_refs"]) <= available_refs
            assert set(terminal["input_refs"]) <= available_refs
            assert all(isinstance(ref, str) and ref for ref in running["input_refs"] + terminal["output_refs"])
            available_refs.update(terminal["output_refs"])

    asyncio.run(exercise_stream())
