from pathlib import Path


def test_frontend_shell_exposes_unified_windows_and_synthetic_mode():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert "FINZANJIR" in html
    assert 'data mode: <span id="mode">synthetic</span>' in html
    assert 'id="flow"' in html
    assert 'id="windows"' in html
    assert 'id="layers"' in html
    assert "JavaScript yoqilgan bo‘lsa" in html
    assert 'id="scenarioSelector"' in html
    assert 'id="runSyntheticScenario"' in html
    assert 'id="runHistory"' in html
