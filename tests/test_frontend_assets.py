from pathlib import Path


def test_frontend_prototype_has_presentation_assets():
    assert Path("frontend/index.html").is_file()
    assert Path("frontend/styles.css").is_file()
    assert Path("frontend/app.js").is_file()
