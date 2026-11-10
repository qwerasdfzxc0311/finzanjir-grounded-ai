import json
from pathlib import Path

import pytest

from finzanjir_ai.knowledge.loader import load_canonical_knowledge


def test_loader_rejects_invalid_canonical_document(tmp_path: Path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"corpus_id": "bad"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_canonical_knowledge(path)
