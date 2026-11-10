import json
from pathlib import Path


def test_event_contract_defines_core_objects_and_relationships():
    path = Path("contracts/event_contracts_v1.json")
    assert path.is_file(), "Event contract is required"

    contract = json.loads(path.read_text(encoding="utf-8"))

    required_objects = {
        "Transaction",
        "Signal",
        "Evidence",
        "Risk",
        "Threshold",
        "Case",
        "HumanDecision",
        "BankStatus",
        "CitizenStatus",
        "AuditEvent",
    }
    assert required_objects == set(contract["objects"])

    assert contract["relationships"] == [
        ["Transaction", "Signal"],
        ["Signal", "Evidence"],
        ["Signal", "Risk"],
        ["Risk", "Threshold"],
        ["Threshold", "Case"],
        ["Case", "HumanDecision"],
        ["HumanDecision", "BankStatus"],
        ["HumanDecision", "CitizenStatus"],
        ["Case", "AuditEvent"],
    ]

    for name in required_objects:
        assert contract["schemas"][name]["required"]
