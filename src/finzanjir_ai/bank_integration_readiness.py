class BankIntegrationReadiness:
    """Keep bank integration claims behind explicit, typed readiness gates."""

    GATES = (
        "legal_approval",
        "partner_approval",
        "specification",
        "security_approval",
        "authentication",
        "sandbox",
    )

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
        invalid = [name for name, value in gates.items() if not isinstance(value, bool)]
        if invalid:
            raise ValueError("readiness gates must be strict booleans: " + ", ".join(invalid))

        blockers = [name for name, passed in gates.items() if passed is False]
        ready = not blockers
        return {
            "ready": ready,
            "status": "READY_FOR_CONTROLLED_INTEGRATION" if ready else "BLOCKED",
            "blockers": blockers,
            "gates": dict(gates),
            "real_bank_connected": False,
        }
