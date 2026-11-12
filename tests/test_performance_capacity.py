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
