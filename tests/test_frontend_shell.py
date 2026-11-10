from pathlib import Path


def test_frontend_shell_exposes_unified_finzanjiro_windows_and_synthetic_mode():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert "FINZANJIR" in html
    assert "Synthetic data mode" in html
    for window in ("Dashboard", "Citizen", "Human+Case", "Synthetic Bank", "Signal/Risk", "Cross-Bank Fraud", "Audit/KPI", "FINZANJIR AI", "16 Layers"):
        assert window in html
