class CitizenTransparency:
    """Build a minimal citizen-facing case view without internal case data."""

    def build_view(self, case: dict) -> dict:
        status = str(case.get("status", "UNKNOWN"))
        reason = str(case.get("reason", "")).strip()

        explanation = (
            reason
            if reason
            else "The case status is available, but no further explanation is currently available."
        )

        return {
            "status": status,
            "explanation": explanation,
            "appeal_available": True,
            "appeal_path": "Request review or correction through the designated appeal channel.",
        }
