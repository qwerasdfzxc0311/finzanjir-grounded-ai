import json
from pathlib import Path


def test_frozen_architecture_contract_declares_required_objects_and_boundaries():
    path = Path("contracts/architecture_v1.json")
    assert path.is_file(), "Frozen architecture contract is required"

    contract = json.loads(path.read_text(encoding="utf-8"))

    required_objects = {
        "Transaction", "Signal", "Evidence", "Risk", "Threshold",
        "Case", "HumanDecision", "BankStatus", "CitizenStatus", "AuditEvent"
    }
    assert required_objects.issubset(set(contract["data_objects"]))

    assert contract["flow"] == [
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
    ]

    assert contract["access_boundaries"]["bank_internal"]["cross_bank_data"] is False
    assert contract["access_boundaries"]["cross_bank"]["requires_explicit_scope"] is True
    assert contract["synthetic_data"]["is_real_bank_data"] is False
