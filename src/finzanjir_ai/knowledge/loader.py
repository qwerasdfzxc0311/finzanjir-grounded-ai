from pathlib import Path
import json

from .schema import validate_canonical_v06

DEFAULT_KNOWLEDGE_PATH = Path("data/canonical_knowledge_v0.6.json")


def knowledge_path() -> Path:
    return DEFAULT_KNOWLEDGE_PATH


def load_canonical_knowledge(path: Path | None = None) -> dict:
    target = path or knowledge_path()
    with target.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    validate_canonical_v06(document)
    return document
