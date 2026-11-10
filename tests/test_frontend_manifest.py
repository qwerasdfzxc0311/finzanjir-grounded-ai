import json
from pathlib import Path


def test_frontend_manifest_contains_unified_windows_and_sixteen_layers():
    manifest = json.loads(Path("frontend/prototype_manifest.json").read_text(encoding="utf-8"))
    assert manifest["data_mode"] == "synthetic"
    assert len(manifest["windows"]) == 9
    assert len(manifest["layers"]) == 16
    assert manifest["windows"][7] == "FINZANJIR AI"
