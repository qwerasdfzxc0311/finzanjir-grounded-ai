from finzanjir_ai.synthetic.generator import generate_demo_scenario


def test_synthetic_scenario_is_deterministic_and_explicitly_synthetic():
    first = generate_demo_scenario(seed=7, scenario="suspicious")
    second = generate_demo_scenario(seed=7, scenario="suspicious")

    assert first == second
    assert first["synthetic"] is True
    assert first["transaction"]["synthetic"] is True
    assert first["actor"]["synthetic"] is True
    assert first["card"]["synthetic"] is True
    assert first["device"]["synthetic"] is True
    assert first["bank"]["synthetic"] is True
    assert first["network"]["synthetic"] is True
    assert first["transaction"]["network_id"] == first["network"]["id"]


def test_synthetic_scenario_contains_a_valid_event_envelope():
    scenario = generate_demo_scenario(seed=11, scenario="normal")

    envelope = scenario["event"]
    assert envelope["scope"] == "bank_internal"
    assert envelope["object_type"] == "Transaction"
    assert envelope["object_id"] == scenario["transaction"]["id"]
    assert envelope["payload"] == scenario["transaction"]
    assert scenario["expected_escalation"] is False


def test_suspicious_scenario_is_marked_for_later_escalation_evaluation():
    scenario = generate_demo_scenario(seed=11, scenario="suspicious")

    assert scenario["expected_escalation"] is True
    assert scenario["transaction"]["amount"] > 100000
    assert scenario["event"]["payload"]["synthetic"] is True
