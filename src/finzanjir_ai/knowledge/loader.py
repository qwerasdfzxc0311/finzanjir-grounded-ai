from pathlib import Path
import json

from .schema import validate_canonical_v06

DEFAULT_KNOWLEDGE_PATH = Path("data/canonical_knowledge_v0.6.json")
DEFAULT_AUTHOR_PROFILE_PATH = Path("data/author_profile_v1.json")


def knowledge_path() -> Path:
    return DEFAULT_KNOWLEDGE_PATH


def load_canonical_knowledge(path: Path | None = None) -> dict:
    target = path or knowledge_path()
    with target.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    validate_canonical_v06(document)
    # Keep author biography/motivation separate from the canonical technical corpus.
    # It is merged only into the runtime retrieval view, after canonical validation.
    if path is None and DEFAULT_AUTHOR_PROFILE_PATH.exists():
        with DEFAULT_AUTHOR_PROFILE_PATH.open("r", encoding="utf-8") as profile_handle:
            profile = json.load(profile_handle)
        supplemental = profile.get("records") if isinstance(profile, dict) else None
        if not isinstance(supplemental, list):
            raise ValueError("Author profile records must be a list")
        canonical_ids = {str(record["id"]) for record in document["records"]}
        for record in supplemental:
            if not isinstance(record, dict) or not record.get("id") or not record.get("statement"):
                raise ValueError("Author profile records require an id and statement")
            if str(record["id"]) in canonical_ids:
                raise ValueError("Author profile record ID collides with canonical knowledge")
        document["author_profile_records"] = supplemental
    return document
