from finzanjir_ai.bank_integration_readiness import BankIntegrationReadiness


def test_integration_is_ready_only_when_all_prerequisites_are_confirmed():
    result = BankIntegrationReadiness().assess(
        legal_approved=True,
        partner_approved=True,
        specification_ready=True,
        security_approved=True,
        authentication_ready=True,
        sandbox_ready=True,
    )

    assert result["ready"] is True
    assert result["status"] == "READY_FOR_CONTROLLED_INTEGRATION"
    assert result["blockers"] == []


def test_missing_prerequisites_block_integration_and_are_named():
    result = BankIntegrationReadiness().assess(
        legal_approved=True,
        partner_approved=False,
        specification_ready=True,
        security_approved=False,
        authentication_ready=True,
        sandbox_ready=False,
    )

    assert result["ready"] is False
    assert result["status"] == "BLOCKED"
    assert set(result["blockers"]) == {"partner_approval", "security_approval", "sandbox"}


def test_readiness_does_not_claim_real_bank_connection():
    result = BankIntegrationReadiness().assess(
        legal_approved=True,
        partner_approved=True,
        specification_ready=True,
        security_approved=True,
        authentication_ready=True,
        sandbox_ready=True,
    )

    assert result["real_bank_connected"] is False


def test_authentication_is_a_distinct_readiness_gate():
    result = BankIntegrationReadiness().assess(
        legal_approved=True,
        partner_approved=True,
        specification_ready=True,
        security_approved=True,
        authentication_ready=False,
        sandbox_ready=True,
    )

    assert result["ready"] is False
    assert "authentication" in result["blockers"]
