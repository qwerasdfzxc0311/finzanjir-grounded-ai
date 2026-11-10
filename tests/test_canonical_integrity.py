import json
from pathlib import Path

import pytest

from finzanjir_ai.knowledge.schema import validate_canonical_v06


@pytest.fixture
def canonical_document():
    path = Path("data/canonical_knowledge_v0.6.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_canonical_v06_integrity_contract(canonical_document):
    validate_canonical_v06(canonical_document)
