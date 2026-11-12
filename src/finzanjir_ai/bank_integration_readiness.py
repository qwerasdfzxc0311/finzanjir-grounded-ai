class BankIntegrationReadiness:
    """Keep bank integration claims behind explicit readiness gates."""

    def assess(
        self,
        *,
        legal_approved: bool,
        partner_approved: bool,
        specification_ready: bool,
        security_approved: bool,
        authentication_ready: bool,
        sandbox_ready: bool,
    ) -> dict:
        gates = {
            "legal_approval": legal_approved,
            "partner_approval": partner_approved,
            "specification": specification_ready,
            "security_approval": security_approved,
            "authentication": authentication_ready,
            "sandbox": sandbox_ready,
        }
        blockers = [name for name, passed in gates.items() if not passed]
        ready = not blockers
        return {
            "ready": ready,
            "status": "READY_FOR_CONTROLLED_INTEGRATION" if ready else "BLOCKED",
            "blockers": blockers,
            "real_bank_connected": False,
        }
