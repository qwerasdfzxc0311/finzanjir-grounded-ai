from finzanjir_ai.risk.pipeline import process_transaction


def _transaction(*, shadow_mode=True):
    return {
        "transaction_id": "syn-multi-001",
        "bank_id": "bank-demo",
        "actor_id": "actor-demo",
        "amount": 2500,
        "occurred_at": "2026-11-12T09:00:00Z",
        "synthetic": True,
        "shadow_mode": shadow_mode,
        "signal_events": [
            {"signal_id": "SIG-018", "evidence_id": "ev-auth", "source": "synthetic-auth", "observed_at": "2026-11-12T08:59:00Z", "evidence_quality": 1.0, "recency_factor": 1.0},
            {"signal_id": "SIG-006", "evidence_id": "ev-device", "source": "synthetic-device", "observed_at": "2026-11-12T08:59:10Z", "evidence_quality": 1.0, "recency_factor": 1.0},
            {"signal_id": "SIG-012", "evidence_id": "ev-account", "source": "synthetic-auth", "observed_at": "2026-11-12T08:59:20Z", "evidence_quality": 1.0, "recency_factor": 1.0},
            {"signal_id": "SIG-004", "evidence_id": "ev-beneficiary", "source": "synthetic-payments", "observed_at": "2026-11-12T08:59:30Z", "evidence_quality": 1.0, "recency_factor": 1.0},
            {"signal_id": "SIG-002", "evidence_id": "ev-velocity", "source": "synthetic-payments", "observed_at": "2026-11-12T08:59:40Z", "evidence_quality": 1.0, "recency_factor": 1.0},
        ],
    }


def test_multi_signal_pipeline_records_high_risk_but_shadow_mode_does_not_open_case():
    result = process_transaction(
        _transaction(),
        signal_amount_threshold=1000,
        escalation_threshold=0.75,
    )

    assert len(result.signals) == 5
    assert len(result.evidences) == 5
    assert result.risk["score"] == 80
    assert result.risk["case_eligible"] is True
    assert result.risk["case_suppressed_reason"] == "shadow_mode"
    assert result.case is None


def test_multi_signal_pipeline_opens_synthetic_case_only_when_shadow_mode_is_explicitly_disabled():
    result = process_transaction(
        _transaction(shadow_mode=False),
        signal_amount_threshold=1000,
        escalation_threshold=0.75,
    )

    assert result.risk["score"] == 80
    assert result.case is not None
    assert len(result.case["signal_ids"]) == 5
    assert result.case["data_mode"] == "synthetic"


def test_multi_signal_pipeline_with_one_family_does_not_open_case():
    transaction = _transaction(shadow_mode=False)
    transaction["signal_events"] = [
        {"signal_id": "SIG-016", "evidence_id": "ev-1", "source": "synthetic-auth", "observed_at": transaction["occurred_at"], "evidence_quality": 1.0, "recency_factor": 1.0},
        {"signal_id": "SIG-017", "evidence_id": "ev-2", "source": "synthetic-auth", "observed_at": transaction["occurred_at"], "evidence_quality": 1.0, "recency_factor": 1.0},
        {"signal_id": "SIG-018", "evidence_id": "ev-3", "source": "synthetic-auth", "observed_at": transaction["occurred_at"], "evidence_quality": 1.0, "recency_factor": 1.0},
    ]

    result = process_transaction(
        transaction,
        signal_amount_threshold=1000,
        escalation_threshold=0.75,
    )

    assert result.risk["score"] == 30
    assert result.risk["case_eligible"] is False
    assert result.case is None
