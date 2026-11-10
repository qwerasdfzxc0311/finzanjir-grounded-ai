from pathlib import Path


DEFAULT_KNOWLEDGE_PATH = Path("data/canonical_knowledge_v0.6.json")


def knowledge_path() -> Path:
    return DEFAULT_KNOWLEDGE_PATH
