from finzanjir_ai.impact_harm_reduction import ImpactHarmReduction


def test_impact_metric_records_formula_denominator_segment_and_dataset_version():
    result = ImpactHarmReduction().compare_rate(
        baseline_events=10,
        baseline_denominator=1000,
        current_events=5,
        current_denominator=1000,
        segment="all_cases",
        dataset_version="dataset-v1",
        methodology="events / denominator",
    )

    assert result["baseline_rate"] == 0.01
    assert result["current_rate"] == 0.005
    assert result["change"] == -0.005
    assert result["denominator"]["baseline"] == 1000
    assert result["denominator"]["current"] == 1000
    assert result["segment"] == "all_cases"
    assert result["dataset_version"] == "dataset-v1"
    assert result["methodology"] == "events / denominator"


def test_impact_metric_requires_valid_denominator():
    result = ImpactHarmReduction().compare_rate(
        baseline_events=1,
        baseline_denominator=0,
        current_events=1,
        current_denominator=100,
        segment="test",
        dataset_version="dataset-v1",
        methodology="events / denominator",
    )

    assert result["status"] == "UNVERIFIED"
    assert result["reason"] == "invalid_denominator"


def test_causal_impact_is_not_claimed_from_rate_change_alone():
    result = ImpactHarmReduction().compare_rate(
        baseline_events=10,
        baseline_denominator=1000,
        current_events=5,
        current_denominator=1000,
        segment="all_cases",
        dataset_version="dataset-v1",
        methodology="events / denominator",
    )

    assert result["causal_claim"] is False
    assert result["limitation"]


def test_segment_and_dataset_version_are_required_for_comparison():
    result = ImpactHarmReduction().compare_rate(
        baseline_events=10,
        baseline_denominator=1000,
        current_events=5,
        current_denominator=1000,
        segment=None,
        dataset_version=None,
        methodology="events / denominator",
    )

    assert result["status"] == "UNVERIFIED"
    assert result["reason"] == "comparison_context_missing"


def test_impact_measurement_rejects_negative_or_boolean_counts():
    import pytest

    with pytest.raises(ValueError, match="non-negative"):
        ImpactHarmReduction().compare_rate(
            baseline_events=-1, baseline_denominator=100, current_events=1,
            current_denominator=100, segment="all", dataset_version="v1",
            methodology="events / denominator",
        )
    with pytest.raises(ValueError, match="integer"):
        ImpactHarmReduction().compare_rate(
            baseline_events=True, baseline_denominator=100, current_events=1,
            current_denominator=100, segment="all", dataset_version="v1",
            methodology="events / denominator",
        )


def test_impact_measurement_requires_methodology_before_claiming_measured():
    result = ImpactHarmReduction().compare_rate(
        baseline_events=1, baseline_denominator=100, current_events=1,
        current_denominator=100, segment="all", dataset_version="v1",
        methodology="",
    )

    assert result == {"status": "UNVERIFIED", "reason": "comparison_context_missing"}
