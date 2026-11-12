from finzanjir_ai.independent_evaluation import IndependentEvaluation


def test_evaluation_records_requirement_expected_actual_and_evidence():
    record = IndependentEvaluation().record_test(
        requirement_id="REQ-012",
        test_id="TEST-012",
        expected="claim is source-bound",
        actual="claim is source-bound",
        evidence="run-277",
        data_version="dataset-v1",
    )

    assert record["requirement_id"] == "REQ-012"
    assert record["test_id"] == "TEST-012"
    assert record["expected"] == "claim is source-bound"
    assert record["actual"] == "claim is source-bound"
    assert record["evidence"] == "run-277"
    assert record["data_version"] == "dataset-v1"
    assert record["result"] == "PASS"


def test_evaluation_fails_when_actual_differs_from_expected():
    record = IndependentEvaluation().record_test(
        requirement_id="REQ-012",
        test_id="TEST-013",
        expected="claim is source-bound",
        actual="claim is unsupported",
        evidence="run-278",
        data_version="dataset-v1",
    )

    assert record["result"] == "FAIL"


def test_replay_requires_same_version_and_records_difference():
    result = IndependentEvaluation().check_replay(
        expected_version="dataset-v1",
        actual_version="dataset-v2",
        expected_result="PASS",
        actual_result="PASS",
    )

    assert result["reproducible"] is False
    assert result["reason"] == "version_mismatch"
    assert result["difference_recorded"] is True


def test_evaluation_record_cannot_claim_success_without_evidence():
    record = IndependentEvaluation().record_test(
        requirement_id="REQ-013",
        test_id="TEST-014",
        expected="safe",
        actual="safe",
        evidence=None,
        data_version="dataset-v1",
    )

    assert record["result"] == "UNVERIFIED"
