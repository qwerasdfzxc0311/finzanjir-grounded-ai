REQUIRED_TOP_LEVEL_KEYS = {
    "corpus_id",
    "schema_version",
    "runtime_policy",
    "stats",
    "knowledge_graph",
    "records",
}

REQUIRED_RECORD_KEYS = {
    "id",
    "concept_id",
    "statement",
    "aliases",
    "evidence",
    "provenance",
    "reconciliation",
    "canonical_concept_id",
}


def validate_top_level_shape(document: object) -> None:
    if not isinstance(document, dict):
        raise ValueError("Canonical knowledge must be a JSON object")
    missing = REQUIRED_TOP_LEVEL_KEYS.difference(document)
    if missing:
        raise ValueError(f"Missing canonical knowledge keys: {sorted(missing)}")


def validate_canonical_v06(document: object) -> None:
    validate_top_level_shape(document)

    assert isinstance(document, dict)
    stats = document["stats"]
    if not isinstance(stats, dict):
        raise ValueError("Canonical knowledge stats must be an object")

    expected_stats = {
        "records_after_semantic_reconciliation": 8804,
        "concept_count": 2060,
        "canonical_concept_count_v0_5": 2060,
        "chapter_count": 15,
        "layer_node_count": 16,
    }
    for key, expected in expected_stats.items():
        if stats.get(key) != expected:
            raise ValueError(f"Unexpected canonical v0.6 stat {key}: {stats.get(key)!r}")

    if stats.get("architecture_manifest_version") != "0.6":
        raise ValueError("Canonical v0.6 architecture manifest is missing")

    records = document["records"]
    if not isinstance(records, list) or len(records) != 8804:
        raise ValueError("Canonical v0.6 must contain exactly 8804 records")

    ids = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} must be an object")
        missing = REQUIRED_RECORD_KEYS.difference(record)
        if missing:
            raise ValueError(f"Record {index} is missing keys: {sorted(missing)}")
        record_id = record["id"]
        if record_id in ids:
            raise ValueError(f"Duplicate canonical record id: {record_id}")
        ids.add(record_id)

    manifest = document.get("finzanjir_architecture_manifest")
    if not isinstance(manifest, dict) or manifest.get("version") != "0.6":
        raise ValueError("FINZANJIR architecture manifest v0.6 is required")
