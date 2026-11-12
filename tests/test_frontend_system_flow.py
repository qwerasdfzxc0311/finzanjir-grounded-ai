import json
from pathlib import Path


def test_frontend_manifest_declares_one_connected_flow():
    manifest = json.loads(Path("frontend/prototype_manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.2"
    assert manifest["data_mode"] == "synthetic"
    assert manifest["system_flow"]["entry"] == "synthetic_bank"
    assert manifest["system_flow"]["final"] == "layers_16"
    assert len(manifest["system_flow"]["transitions"]) == 7
    assert manifest["system_flow"]["transitions"][0] == ["synthetic_bank", "signal_risk"]
    assert manifest["system_flow"]["transitions"][1] == ["signal_risk", "cross_bank_fraud"]
    assert manifest["system_flow"]["transitions"][2] == ["cross_bank_fraud", "human_case"]
    assert manifest["system_flow"]["transitions"][-1] == ["citizen", "layers_16"]


def test_frontend_manifest_explains_each_window_role():
    manifest = json.loads(Path("frontend/prototype_manifest.json").read_text(encoding="utf-8"))
    roles = manifest["window_roles"]
    assert set(roles) == set(manifest["window_ids"])
    assert all(roles[window]["input"] for window in roles)
    assert all(roles[window]["output"] for window in roles)


def test_frontend_bootstraps_from_real_runtime_demo_endpoint():
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    assert "/api/prototype/demo" in script
    assert "prototypeResult" in script
    assert "transaction_id" in script


def test_frontend_runs_synthetic_detector_and_reads_persisted_history():
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    assert "/api/prototype/run" in script
    assert "/api/prototype/runs?limit=10" in script
    assert "signal_features" in script
    assert "synthetic: true" in script
    assert "clipboard" not in script.lower()


def test_frontend_connects_synthetic_shadow_evaluation_api():
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    assert "/api/prototype/detector-shadow-evaluate" in script
    assert "buildShadowScenarios" in script
    assert "target_signal_ids" in script
    assert "synthetic: true" in script
    assert "abstention rate" in script.lower()
    assert "real fraud precision/recall" in script
    assert "Shadow Mode: Case ochilmaydi" in script


def test_frontend_displays_all_connected_system_module_outputs():
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    for module in [
        "Synthetic Bank → Signal / Evidence / Risk",
        "Human + Case",
        "Cross-Bank Fraud",
        "Audit / KPI",
        "FINZANJIR AI",
        "Citizen",
        "16 Layers",
    ]:
        assert module in script
    assert "body.decision" in script
    assert "body.cross_bank" in script
    assert "body.citizen_status" in script
    assert "body.layers_16" in script



def test_work_windows_are_interactive_and_show_shared_latest_runtime_output():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    styles = Path("frontend/styles.css").read_text(encoding="utf-8")

    assert 'id="windowWorkspace"' in html
    assert 'id="activeWindowTitle"' in html
    assert 'id="activeWindowData"' in html
    assert 'element("button", "window-card")' in script
    assert 'button.addEventListener("click", () => {' in script
    assert "selectWindow(id);" in script
    assert 'if (id === "synthetic_bank") runSyntheticScenario();' in script
    assert 'function selectWindow(windowId)' in script
    assert "function windowSummaryLines(windowId)" in script
    assert "lastExecution = body" in script
    assert 'setAttribute("aria-pressed"' in script
    assert '.window-card[aria-pressed="true"]' in styles
    assert "innerHTML" not in script



def test_synthetic_bank_window_click_starts_a_synthetic_run():
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    assert 'if (id === "synthetic_bank") runSyntheticScenario();' in script
    assert 'if (button.disabled) return;' in script
    assert 'synthetic: true' in script


def test_each_window_exposes_truthful_shared_execution_status():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    styles = Path("frontend/styles.css").read_text(encoding="utf-8")

    assert 'id="activeWindowStatus"' in html
    assert 'element("small", "window-status", windowExecutionStatus(id))' in script
    assert "function windowExecutionStatus(windowId)" in script
    assert "function refreshWindowStatuses()" in script
    assert 'executionStatus = "running"' in script
    assert 'executionStatus = "success"' in script
    assert 'executionStatus = "failed"' in script
    assert '.window-status[data-state="running"]' in styles



def test_signal_risk_window_shows_signal_reasons_evidence_and_threshold_explanation():
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    styles = Path("frontend/styles.css").read_text(encoding="utf-8")
    for field in [
        "risk.contributions",
        "signal_name",
        "score_suppressed_reason",
        "family_contributions",
        "provenance.source",
        "evidence_quality",
        "recency_factor",
        "threshold?.reason",
        "case_block_reason",
        "case_suppressed_reason",
    ]:
        assert field in script
    assert "priority score" not in script.lower()
    assert "ustuvorlik balli" in script
    assert "#activeWindowData{max-height:560px;overflow-y:auto;overscroll-behavior:contain;padding-right:12px}" in styles



def test_cross_bank_window_never_claims_a_check_without_authorized_exchange():
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    assert 'snapshot.runtime?.cross_bank_authorized !== true' in script
    assert 'Cross-bank almashinuvi o‘chiq · ruxsat yo‘q' in script
    assert 'Ruxsatli scope tekshirildi · moslik topilmadi' in script



def test_frontend_renders_backend_execution_trace_for_each_window():
    script = Path("frontend/app.js").read_text(encoding="utf-8")
    assert "function windowTraceFor(windowId)" in script
    assert "function windowTraceLines(windowId)" in script
    assert "snapshot.window_trace" in script
    assert "[...windowTraceLines(windowId), ...windowSummaryLines(windowId)]" in script
    assert "Bosqich #" in script
    assert "Kirish refs:" in script
    assert "Chiqish refs:" in script
    assert 'fetch("/api/prototype/run/stream"' in script



def test_frontend_uses_server_sent_events_for_real_window_progress():
    script = Path("frontend/app.js").read_text(encoding="utf-8")

    assert 'fetch("/api/prototype/run/stream"' in script
    assert "async function readPrototypeProgress(response)" in script
    assert 'eventName === "stage"' in script
    assert "liveWindowTrace" in script
    assert 'trace.status === "RUNNING"' in script
    assert 'trace.status === "PENDING"' in script



def test_frontend_preserves_backend_failed_and_not_run_states_after_stream_error():
    script = Path("frontend/app.js").read_text(encoding="utf-8")

    assert 'executionStatus === "failed" && liveWindowTrace.length' in script
    assert 'trace?.status === "FAILED"' in script
    assert 'trace?.status === "NOT_RUN"' in script
