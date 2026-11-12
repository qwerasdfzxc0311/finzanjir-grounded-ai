from typing import Any


class IndependentEvaluation:
    """Record reproducible evaluation evidence without treating unsupported results as success."""

    def record_test(
        self,
        *,
        requirement_id: str,
        test_id: str,
        expected: Any,
        actual: Any,
        evidence: str | None,
        data_version: str,
    ) -> dict[str, Any]:
        if evidence is None:
            result = "UNVERIFIED"
        else:
            result = "PASS" if actual == expected else "FAIL"
        return {
            "requirement_id": requirement_id,
            "test_id": test_id,
            "expected": expected,
            "actual": actual,
            "evidence": evidence,
            "data_version": data_version,
            "result": result,
        }

    def check_replay(
        self,
        *,
        expected_version: str,
        actual_version: str,
        expected_result: Any,
        actual_result: Any,
    ) -> dict[str, Any]:
        if expected_version != actual_version:
            return {
                "reproducible": False,
                "reason": "version_mismatch",
                "difference_recorded": True,
            }
        return {
            "reproducible": expected_result == actual_result,
            "reason": "same_version" if expected_result == actual_result else "result_mismatch",
            "difference_recorded": expected_result != actual_result,
        }
