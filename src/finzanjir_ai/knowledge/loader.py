from pathlib import Path
import json

from .schema import validate_canonical_v06

DEFAULT_KNOWLEDGE_PATH = Path("data/canonical_knowledge_v0.6.json")
DEFAULT_AUTHOR_PROFILE_PATH = Path("data/author_profile_v1.json")
DEFAULT_PROJECT_PRINCIPLES_PATH = Path("data/project_principles_v1.json")


def knowledge_path() -> Path:
    return DEFAULT_KNOWLEDGE_PATH


def load_author_profile_records(path: Path | None = None) -> list[dict]:
    """Load the separately governed, author-confirmed biography layer."""
    target = path or DEFAULT_AUTHOR_PROFILE_PATH
    if not target.exists():
        return []
    with target.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict) or document.get("profile_type") != "author_biography":
        raise ValueError("Author profile must declare profile_type=author_biography")
    records = document.get("records")
    if not isinstance(records, list):
        raise ValueError("Author profile records must be a list")
    required = {
        "id", "concept_id", "canonical_concept_id", "statement", "aliases",
        "evidence", "provenance", "reconciliation",
    }
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or required.difference(record):
            raise ValueError(f"Author profile record {index} is incomplete")
        if not str(record["id"]).startswith("author_"):
            raise ValueError(f"Author profile record {index} must use an author_ ID")
        if record["id"] in seen:
            raise ValueError(f"Duplicate author profile record ID: {record['id']}")
        seen.add(record["id"])
        if record["evidence"].get("verification") != "author_confirmed":
            raise ValueError(f"Author profile record {record['id']} is not author-confirmed")
    return records


def load_project_principle_records(path: Path | None = None) -> list[dict]:
    """Load author-confirmed project principles and future requirements separately from canonical v0.6."""
    target = path or DEFAULT_PROJECT_PRINCIPLES_PATH
    if not target.exists():
        return []
    with target.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict) or document.get("profile_type") != "project_principles":
        raise ValueError("Project principles must declare profile_type=project_principles")
    records = document.get("records")
    if not isinstance(records, list):
        raise ValueError("Project principle records must be a list")
    required = {
        "id", "concept_id", "canonical_concept_id", "statement", "aliases",
        "evidence", "provenance", "reconciliation",
    }
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or required.difference(record):
            raise ValueError(f"Project principle record {index} is incomplete")
        if not str(record["id"]).startswith("project_"):
            raise ValueError(f"Project principle record {index} must use a project_ ID")
        if record["id"] in seen:
            raise ValueError(f"Duplicate project principle record ID: {record['id']}")
        seen.add(record["id"])
        evidence = record.get("evidence")
        if not isinstance(evidence, dict) or evidence.get("verification") != "author_confirmed":
            raise ValueError(f"Project principle record {record['id']} is not author-confirmed")
    return records


def load_canonical_knowledge(path: Path | None = None) -> dict:
    target = path or knowledge_path()
    with target.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    validate_canonical_v06(document)
    return document
