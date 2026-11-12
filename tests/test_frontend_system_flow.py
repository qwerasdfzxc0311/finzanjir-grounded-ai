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
    assert "/api/prototype/shadow-evaluate" in script
    assert "buildShadowScenarios" in script
    assert "synthetic: true" in script
    assert "real fraud precision/recall" in script
    assert "Shadow Mode: Case ochilmaydi" in script
