import json
from pathlib import Path


def test_frontend_manifest_contains_unified_windows_and_sixteen_layers():
    manifest = json.loads(Path("frontend/prototype_manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.2"
    assert manifest["data_mode"] == "synthetic"
    assert len(manifest["window_ids"]) == 9
    assert len(manifest["windows"]) == 9
    assert [item[1] for item in manifest["windows"]] == [
        "Dashboard", "Citizen", "Human+Case", "Synthetic Bank", "Signal/Risk",
        "Cross-Bank Fraud", "Audit/KPI", "FINZANJIR AI", "16 Layers",
    ]
    assert len(manifest["layers"]) == 16
    assert manifest["system_flow"]["entry"] == "synthetic_bank"
    assert manifest["system_flow"]["final"] == "layers_16"
