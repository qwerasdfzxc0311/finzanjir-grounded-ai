import json
from pathlib import Path

import pytest

from finzanjir_ai.knowledge.loader import load_canonical_knowledge, load_project_principle_records


def test_loader_rejects_invalid_canonical_document(tmp_path: Path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"corpus_id": "bad"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_canonical_knowledge(path)


def test_project_principles_loader_rejects_wrong_profile_type(tmp_path: Path):
    path = tmp_path / "principles.json"
    path.write_text(json.dumps({"profile_type": "author_biography", "records": []}), encoding="utf-8")

    from finzanjir_ai.knowledge.loader import load_project_principle_records

    with pytest.raises(ValueError):
        load_project_principle_records(path)


def test_project_principles_loader_accepts_author_confirmed_records():
    records = load_project_principle_records()
    assert len(records) >= 9
    ids = {record["id"] for record in records}
    assert "project_0001" in ids
    assert "project_0004" in ids
    assert "project_0007" in ids
