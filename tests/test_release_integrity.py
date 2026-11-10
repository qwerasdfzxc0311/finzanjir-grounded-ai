import json
from pathlib import Path

from finzanjir_ai.knowledge.schema import validate_canonical_v06


def test_canonical_v06_integrity():
    document = json.loads(
        Path("data/canonical_knowledge_v0.6.json").read_text(encoding="utf-8")
    )
    validate_canonical_v06(document)
