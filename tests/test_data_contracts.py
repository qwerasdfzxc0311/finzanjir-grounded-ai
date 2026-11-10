import json
from pathlib import Path


def test_data_model_contract_declares_core_objects():
    contract = json.loads(Path("contracts/data_model_v1.json").read_text(encoding="utf-8"))
    required = {
        "Transaction", "Signal", "Evidence", "Risk", "Threshold", "Case",
        "HumanDecision", "BankStatus", "CitizenStatus", "AuditEvent", "AIContext"
    }
    assert required == set(contract["objects"])


def test_event_envelope_contract_declares_traceable_identity():
    contract = json.loads(Path("contracts/event_envelope_v1.json").read_text(encoding="utf-8"))
    assert contract["version"] == "1.0"
    assert set(contract["required"]) == {
        "event_id", "event_type", "occurred_at", "actor_id", "source",
        "correlation_id", "causation_id", "payload"
    }
