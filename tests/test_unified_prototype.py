import json
from pathlib import Path


def test_unified_prototype_declares_nine_windows_and_sixteen_layers():
    config = json.loads(Path("frontend/prototype_manifest.json").read_text(encoding="utf-8"))
    assert len(config["windows"]) == 9
    assert len(config["layers"]) == 16
    assert config["data_mode"] == "synthetic"
