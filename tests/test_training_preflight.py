import pytest

from finzanjir_ai.training.data_governance import TrainingDatasetBuilder, TrainingExample
from finzanjir_ai.training.preflight import (
    ModelTrainingConfig,
    build_source_grouped_split,
    training_preflight,
    validate_no_source_leakage,
)


def _example(index, source_id=None, language="kaa-Latn"):
    return TrainingExample(
        input_text=f"question {index}",
        target_text=f"answer {index}",
        language=language,
        task_type="qa",
        source_id=source_id or f"source-{index}",
        source_uri=f"local://approved/{source_id or f'source-{index}'}",
        license_id="author-granted",
        verified=True,
        permission_ref="written-grant-001",
        data_class="licensed_nonpersonal",
        source_type="author_provided",
    )


def _ready_builder(count=6):
    builder = TrainingDatasetBuilder(dataset_version="0.2.0")
    for index in range(count):
        assert builder.add(_example(index)) is True
    return builder


def test_source_grouped_split_is_deterministic_and_leakage_free():
    builder = _ready_builder()
    first = build_source_grouped_split(builder.accepted_examples, seed=42)
    second = build_source_grouped_split(builder.accepted_examples, seed=42)
    assert first == second
    validate_no_source_leakage(first)
    assert first.train.examples
    assert first.validation.examples
    assert first.test.examples


def test_all_examples_from_one_source_stay_in_one_partition():
    builder = TrainingDatasetBuilder(dataset_version="0.2.0")
    assert builder.add(_example(1, source_id="book-A")) is True
    assert builder.add(_example(2, source_id="book-A")) is True
    assert builder.add(_example(3, source_id="book-B")) is True
    assert builder.add(_example(4, source_id="book-C")) is True
    plan = build_source_grouped_split(builder.accepted_examples, seed=7)
    partitions = {
        split.name: {item.source_id for item in split.examples}
        for split in (plan.train, plan.validation, plan.test)
    }
    appearances = sum("book-A" in source_ids for source_ids in partitions.values())
    assert appearances == 1


def test_split_requires_three_distinct_source_groups():
    builder = TrainingDatasetBuilder(dataset_version="0.2.0")
    assert builder.add(_example(1, source_id="same")) is True
    assert builder.add(_example(2, source_id="same")) is True
    assert builder.add(_example(3, source_id="same")) is True
    with pytest.raises(ValueError, match="three distinct source groups"):
        build_source_grouped_split(builder.accepted_examples)


def test_preflight_requires_dataset_readiness_and_human_split_review():
    builder = _ready_builder()
    readiness = builder.readiness(
        required_languages=("kaa-Latn",),
        minimum_per_language=1,
        reviewer_approved=True,
    )
    plan = build_source_grouped_split(builder.accepted_examples, seed=11)
    not_approved = training_preflight(
        readiness,
        plan,
        required_languages=("kaa-Latn",),
        human_split_review_approved=False,
    )
    assert not_approved.ready is False
    assert "human_split_review_not_approved" in not_approved.reasons

    approved = training_preflight(
        readiness,
        plan,
        required_languages=("kaa-Latn",),
        human_split_review_approved=True,
    )
    assert approved.ready is True
    assert approved.total_examples == 6


def test_preflight_blocks_missing_validation_or_test_language_coverage():
    builder = _ready_builder()
    readiness = builder.readiness(
        required_languages=("kaa-Latn",),
        minimum_per_language=1,
        reviewer_approved=True,
    )
    plan = build_source_grouped_split(builder.accepted_examples, seed=3)
    result = training_preflight(
        readiness,
        plan,
        required_languages=("kaa-Latn", "uz-Latn"),
        human_split_review_approved=True,
    )
    assert result.ready is False
    assert "validation_language_coverage_incomplete" in result.reasons
    assert "test_language_coverage_incomplete" in result.reasons


def test_model_config_is_random_initialized_and_validated():
    config = ModelTrainingConfig()
    config.validate()
    assert config.pretrained_weights is False
    with pytest.raises(ValueError, match="random initialization"):
        ModelTrainingConfig(pretrained_weights=True).validate()


def test_model_config_rejects_incompatible_attention_dimensions():
    with pytest.raises(ValueError, match="divisible"):
        ModelTrainingConfig(hidden_size=510, attention_heads=8).validate()


def test_model_config_rejects_zero_attention_heads_without_division_error():
    with pytest.raises(ValueError, match="must be positive"):
        ModelTrainingConfig(attention_heads=0).validate()


def test_preflight_rejects_mismatched_split_count():
    builder = _ready_builder()
    readiness = builder.readiness(
        required_languages=("kaa-Latn",),
        minimum_per_language=1,
        reviewer_approved=True,
    )
    plan = build_source_grouped_split(builder.accepted_examples, seed=5)
    from dataclasses import replace
    shortened = replace(plan, test=replace(plan.test, examples=()))
    result = training_preflight(
        readiness,
        shortened,
        required_languages=("kaa-Latn",),
        human_split_review_approved=True,
    )
    assert result.ready is False
    assert "dataset_split_count_mismatch" in result.reasons
    assert "empty_dataset_partition" in result.reasons
