import json
from pathlib import Path


def test_canonical_v06_release_is_present_and_reconciled():
    path = Path("data/canonical_knowledge_v0.6.json")
    assert path.is_file(), "Canonical v0.6 release file is required at runtime data path"

    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["stats"]["records_after_semantic_reconciliation"] == 8804
    assert document["stats"]["canonical_concept_count_v0_5"] == 2060
    assert document["stats"]["chapter_count"] == 15
    assert document["stats"]["layer_node_count"] == 16
    assert len(document["records"]) == 8804
