from finzanjir_ai.validation.release import validate_release


def test_release_validation_report_is_clean():
    report = validate_release()
    print(report)
    assert report["ok"] is True
    assert report["checks_failed"] == []
    assert report["canonical_records"] == 8804
    assert report["canonical_concepts"] == 2060
    assert report["layers"] == 16
