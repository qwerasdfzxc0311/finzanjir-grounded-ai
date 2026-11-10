from pathlib import Path


def test_frontend_shell_references_manifest_and_styles():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert 'rel="stylesheet"' in html
    assert "styles.css" in html
    assert "prototype_manifest.json" in html
    assert "Synthetic DATA MODE" not in html
    assert "SYNTHETIC DATA MODE" in html


def test_prototype_manifest_exposes_all_work_windows_and_layers():
    import json
    manifest = json.loads(Path("frontend/prototype_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["windows"]) == 9
    assert len(manifest["layers"]) == 16
