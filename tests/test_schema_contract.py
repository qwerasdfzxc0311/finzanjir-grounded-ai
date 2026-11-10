import json
from pathlib import Path

from finzanjir_ai.knowledge.schema import validate_top_level_shape


def test_canonical_knowledge_has_required_top_level_shape():
    path = Path("data/canonical_knowledge_v0.6.json")
    assert path.is_file(), "Canonical knowledge file is required"
    document = json.loads(path.read_text(encoding="utf-8"))
    validate_top_level_shape(document)
