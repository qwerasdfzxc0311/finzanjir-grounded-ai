from pathlib import Path


def test_canonical_knowledge_file_exists_at_runtime_path():
    knowledge_path = Path("data/canonical_knowledge_v0.6.json")
    assert knowledge_path.is_file(), (
        "Canonical FINZANJIR knowledge must be present at "
        "data/canonical_knowledge_v0.6.json"
    )
