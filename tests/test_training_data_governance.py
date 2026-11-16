import json

from finzanjir_ai.training.data_governance import (
    TrainingDatasetBuilder,
    TrainingExample,
)


def _example(**overrides):
    values = {
        "input_text": "Salom",
        "target_text": "Assalawma aleykum",
        "language": "kaa-Latn",
        "task_type": "greeting",
        "source_id": "author-reviewed-001",
        "source_uri": "local://approved-language-pack/001",
        "license_id": "author-granted",
        "verified": True,
        "permission_ref": "written-permission-001",
        "data_class": "licensed_nonpersonal",
        "source_type": "author_provided",
    }
    values.update(overrides)
    return TrainingExample(**values)


def test_builder_accepts_licensed_verified_nonpersonal_example_and_keeps_provenance():
    builder = TrainingDatasetBuilder(dataset_version="0.1.0")
    assert builder.add(_example()) is True
    rows = [json.loads(line) for line in builder.export_jsonl().splitlines()]
    assert len(rows) == 1
    assert rows[0]["language"] == "kaa-Latn"
    assert rows[0]["source_id"] == "author-reviewed-001"
    assert rows[0]["license_id"] == "author-granted"
    assert rows[0]["permission_ref"] == "written-permission-001"
    assert rows[0]["data_class"] == "licensed_nonpersonal"


def test_builder_rejects_unapproved_license_and_missing_permission():
    builder = TrainingDatasetBuilder(dataset_version="0.1.0")
    assert builder.add(_example(license_id="unknown-license")) is False
    assert builder.add(_example(permission_ref=None)) is False
    assert builder.manifest()["rejected_examples"] == 2


def test_builder_rejects_personal_financial_and_unknown_data_classes():
    builder = TrainingDatasetBuilder(dataset_version="0.1.0")
    assert builder.add(_example(contains_personal_data=True)) is False
    assert builder.add(_example(contains_financial_data=True)) is False
    assert builder.add(_example(data_class="unknown")) is False
    assert builder.manifest()["total_examples"] == 0


def test_builder_rejects_sensitive_identifiers_even_when_metadata_is_incorrect():
    builder = TrainingDatasetBuilder(dataset_version="0.1.0")
    assert builder.add(_example(target_text="Contact user@example.com")) is False
    assert builder.add(_example(target_text="Card 4111 1111 1111 1111")) is False


def test_builder_rejects_unverified_or_untraceable_sources():
    builder = TrainingDatasetBuilder(dataset_version="0.1.0")
    assert builder.add(_example(verified=False)) is False
    assert builder.add(_example(source_uri="file:///tmp/source.txt")) is False
    assert builder.add(_example(source_id="")) is False


def test_builder_deduplicates_examples_and_records_rejection_reason():
    builder = TrainingDatasetBuilder(dataset_version="0.1.0")
    assert builder.add(_example()) is True
    assert builder.add(_example(input_text="  SALOM  ", target_text="Assalawma aleykum")) is False
    manifest = builder.manifest()
    assert manifest["total_examples"] == 1
    assert manifest["rejection_reasons"] == {"duplicate_example": 1}


def test_readiness_requires_language_coverage_and_human_approval():
    builder = TrainingDatasetBuilder(dataset_version="0.1.0")
    builder.add(_example(language="kaa-Latn"))
    not_ready = builder.readiness(
        required_languages=("kaa-Latn", "uz-Latn"),
        minimum_per_language=1,
        reviewer_approved=False,
    )
    assert not_ready.ready is False
    assert not_ready.missing_languages == ("uz-Latn",)
    assert "human_dataset_review_not_approved" in not_ready.reasons

    ready = builder.readiness(
        required_languages=("kaa-Latn",),
        minimum_per_language=1,
        reviewer_approved=True,
    )
    assert ready.ready is True


def test_readiness_rejects_invalid_thresholds():
    builder = TrainingDatasetBuilder(dataset_version="0.1.0")
    try:
        builder.readiness(required_languages=("uz-Latn",), minimum_per_language=0)
    except ValueError:
        pass
    else:
        raise AssertionError("minimum_per_language=0 must be rejected")


def test_manifest_never_claims_training_has_started():
    manifest = TrainingDatasetBuilder(dataset_version="0.1.0").manifest()
    assert manifest["training_started"] is False
    assert manifest["model_training_enabled"] is False


def test_builder_rejects_hosted_model_outputs_as_training_sources():
    builder = TrainingDatasetBuilder(dataset_version="0.1.0")
    assert builder.add(_example(source_type="hosted_model_output")) is False
    assert builder.add(_example(source_type="unknown")) is False
    assert builder.manifest()["total_examples"] == 0
