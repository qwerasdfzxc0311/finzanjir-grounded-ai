from finzanjir_ai.performance_capacity import PerformanceCapacity


def test_capacity_evaluation_records_load_and_recovery_metrics():
    result = PerformanceCapacity().evaluate(
        latency_ms=120,
        error_rate=0.01,
        resource_utilization=0.60,
        recovered=True,
        thresholds={"latency_ms": 200, "error_rate": 0.05, "resource_utilization": 0.80},
        load_profile="100_rps",
    )

    assert result["result"] == "PASS"
    assert result["load_profile"] == "100_rps"
    assert result["latency_ms"] == 120
    assert result["error_rate"] == 0.01
    assert result["resource_utilization"] == 0.60
    assert result["recovered"] is True


def test_timeout_or_queue_overflow_is_recorded_as_failure():
    result = PerformanceCapacity().evaluate(
        latency_ms=500,
        error_rate=0.10,
        resource_utilization=0.95,
        recovered=False,
        thresholds={"latency_ms": 200, "error_rate": 0.05, "resource_utilization": 0.80},
        load_profile="500_rps_timeout",
    )

    assert result["result"] == "FAIL"
    assert result["recovery_required"] is True


def test_unapproved_thresholds_do_not_produce_pass_claim():
    result = PerformanceCapacity().evaluate(
        latency_ms=100,
        error_rate=0.01,
        resource_utilization=0.50,
        recovered=True,
        thresholds=None,
        load_profile="100_rps",
    )

    assert result["result"] == "UNVERIFIED"
    assert result["reason"] == "thresholds_unapproved"


def test_environment_and_load_profile_are_part_of_the_result():
    result = PerformanceCapacity().evaluate(
        latency_ms=100,
        error_rate=0.01,
        resource_utilization=0.50,
        recovered=True,
        thresholds={"latency_ms": 200, "error_rate": 0.05, "resource_utilization": 0.80},
        load_profile="50_rps",
        environment="ci",
    )

    assert result["environment"] == "ci"
    assert result["load_profile"] == "50_rps"


def test_capacity_rejects_non_finite_or_out_of_range_measurements():
    import pytest

    with pytest.raises(ValueError, match="finite"):
        PerformanceCapacity().evaluate(
            latency_ms=float("nan"), error_rate=0.01, resource_utilization=0.5,
            recovered=True, thresholds=None, load_profile="test",
        )
    with pytest.raises(ValueError, match="between 0 and 1"):
        PerformanceCapacity().evaluate(
            latency_ms=10, error_rate=1.5, resource_utilization=0.5,
            recovered=True, thresholds=None, load_profile="test",
        )
    with pytest.raises(ValueError, match="recovered must be boolean"):
        PerformanceCapacity().evaluate(
            latency_ms=10, error_rate=0.01, resource_utilization=0.5,
            recovered="true", thresholds=None, load_profile="test",
        )


def test_capacity_rejects_incomplete_or_invalid_approved_thresholds():
    import pytest

    with pytest.raises(ValueError, match="exactly"):
        PerformanceCapacity().evaluate(
            latency_ms=10, error_rate=0.01, resource_utilization=0.5,
            recovered=True, thresholds={"latency_ms": 100}, load_profile="test",
        )
    with pytest.raises(ValueError, match="thresholds.error_rate"):
        PerformanceCapacity().evaluate(
            latency_ms=10, error_rate=0.01, resource_utilization=0.5,
            recovered=True,
            thresholds={"latency_ms": 100, "error_rate": 2, "resource_utilization": 0.8},
            load_profile="test",
        )


def test_sample_aggregator_reports_percentiles_throughput_and_scope_honestly():
    result = PerformanceCapacity().evaluate_samples(
        latencies_ms=[10, 20, 30, 40, 100],
        error_count=1,
        request_count=5,
        duration_seconds=2,
        resource_utilization_samples=[0.4, 0.7, 0.6],
        recovered=True,
        thresholds={"latency_ms": 100, "error_rate": 0.2, "resource_utilization": 0.8},
        load_profile="synthetic-ci-fixture",
        environment="ci",
    )

    assert result["result"] == "PASS"
    assert result["latency_percentiles_ms"] == {"p50": 30, "p95": 100, "p99": 100}
    assert result["throughput_rps"] == 2.5
    assert result["peak_resource_utilization"] == 0.7
    assert result["measurement_scope"] == "provided_samples_not_a_live_load_test"


def test_sample_aggregator_rejects_inconsistent_request_counts_and_invalid_utilization():
    import pytest

    with pytest.raises(ValueError, match="request_count must equal"):
        PerformanceCapacity().evaluate_samples(
            latencies_ms=[10, 20], error_count=0, request_count=3, duration_seconds=1,
            resource_utilization_samples=[0.5], recovered=True, thresholds=None, load_profile="test",
        )
    with pytest.raises(ValueError, match="between 0 and 1"):
        PerformanceCapacity().evaluate_samples(
            latencies_ms=[10], error_count=0, request_count=1, duration_seconds=1,
            resource_utilization_samples=[1.2], recovered=True, thresholds=None, load_profile="test",
        )
