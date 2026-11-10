REQUIRED_TOP_LEVEL_KEYS = {
    "corpus_id",
    "schema_version",
    "runtime_policy",
    "stats",
    "knowledge_graph",
    "records",
}


def validate_top_level_shape(document: object) -> None:
    if not isinstance(document, dict):
        raise ValueError("Canonical knowledge must be a JSON object")
    missing = REQUIRED_TOP_LEVEL_KEYS.difference(document)
    if missing:
        raise ValueError(f"Missing canonical knowledge keys: {sorted(missing)}")
