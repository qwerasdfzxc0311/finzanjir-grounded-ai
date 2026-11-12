from finzanjir_ai.citizen_transparency import CitizenTransparency

def test_case_view_exposes_process_status():
    view = CitizenTransparency().build_view(
        case={"status": "OPEN", "reason": "risk signal requires review"}
    )

    assert view["status"] == "OPEN"


def test_case_view_contains_understandable_explanation():
    view = CitizenTransparency().build_view(
        case={"status": "OPEN", "reason": "risk signal requires review"}
    )

    assert view["explanation"]
    assert "review" in view["explanation"].lower()


def test_case_view_provides_appeal_and_correction_path():
    view = CitizenTransparency().build_view(
        case={"status": "OPEN", "reason": "risk signal requires review"}
    )

    assert view["appeal_available"] is True
    assert view["appeal_path"]


def test_case_view_does_not_expose_internal_case_data():
    view = CitizenTransparency().build_view(
        case={
            "status": "OPEN",
            "reason": "risk signal requires review",
            "internal_rule_id": "RULE-SECRET",
            "account_number": "1234567890",
        }
    )

    assert "internal_rule_id" not in view
    assert "account_number" not in view
