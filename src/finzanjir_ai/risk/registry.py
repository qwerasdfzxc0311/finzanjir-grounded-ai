from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalDefinition:
    signal_id: str
    name: str
    family: str
    weight: float
    source_status: str = "legacy"


# Legacy SIG-001..015 weights are initial engineering defaults, not calibrated
# probabilities. SIG-016..035 are candidate additions awaiting expert/legal
# approval and shadow-mode evaluation.
_DEFINITIONS = (
    SignalDefinition("SIG-001", "Unusual transaction amount", "TRANSACTION_AMOUNT", 10),
    SignalDefinition("SIG-002", "High transaction velocity", "TRANSACTION_VELOCITY", 15),
    SignalDefinition("SIG-003", "Rapid pass-through flow", "FLOW_CHAIN", 20),
    SignalDefinition("SIG-004", "New beneficiary", "BENEFICIARY", 10),
    SignalDefinition("SIG-005", "Structuring / limit avoidance", "STRUCTURING", 15),
    SignalDefinition("SIG-006", "New device", "DEVICE", 15),
    SignalDefinition("SIG-007", "Geographic anomaly", "GEO", 15),
    SignalDefinition("SIG-008", "Multiple cards on one device", "DEVICE_NETWORK", 20),
    SignalDefinition("SIG-009", "VPN / proxy / Tor context", "NETWORK_REPUTATION", 5),
    SignalDefinition("SIG-010", "Unusual activity time", "TIME_BEHAVIOR", 5),
    SignalDefinition("SIG-011", "Rushed session", "SESSION", 10),
    SignalDefinition("SIG-012", "Password reset followed by transfer", "ACCOUNT_SECURITY", 20),
    SignalDefinition("SIG-013", "Known suspicious beneficiary", "BENEFICIARY_REPUTATION", 20),
    SignalDefinition("SIG-014", "Shared device / phone attributes", "GRAPH_ATTRIBUTES", 15),
    SignalDefinition("SIG-015", "Circular transaction flow", "FLOW_GRAPH", 25),
    SignalDefinition("SIG-016", "Repeated failed authentication", "AUTH", 15, "candidate"),
    SignalDefinition("SIG-017", "Unusual OTP challenge retry cycle", "AUTH", 10, "candidate"),
    SignalDefinition("SIG-018", "MFA protection downgrade", "AUTH", 20, "candidate"),
    SignalDefinition("SIG-019", "Trusted-device binding removed", "DEVICE", 15, "candidate"),
    SignalDefinition("SIG-020", "Existing beneficiary details changed", "BENEFICIARY", 15, "candidate"),
    SignalDefinition("SIG-021", "Beneficiary name-match discrepancy", "BENEFICIARY", 15, "candidate"),
    SignalDefinition("SIG-022", "Dormant account reactivated", "ACCOUNT_BEHAVIOR", 10, "candidate"),
    SignalDefinition("SIG-023", "Multiple independent senders then outflow", "FLOW_GRAPH", 20, "candidate"),
    SignalDefinition("SIG-024", "Rapid multi-hop transfer chain", "FLOW_GRAPH", 20, "candidate"),
    SignalDefinition("SIG-025", "Near-total balance drained after inflow", "FLOW_BEHAVIOR", 15, "candidate"),
    SignalDefinition("SIG-026", "Unusual reversal / refund pattern", "PAYMENT_LIFECYCLE", 10, "candidate"),
    SignalDefinition("SIG-027", "Repeated cancel-and-retry payment pattern", "PAYMENT_LIFECYCLE", 10, "candidate"),
    SignalDefinition("SIG-028", "Channel switch after security event", "SESSION", 10, "candidate"),
    SignalDefinition("SIG-029", "Conflicting parallel active sessions", "SESSION", 15, "candidate"),
    SignalDefinition("SIG-030", "Digital-to-ATM cash-out sequence", "CASH_OUT", 15, "candidate"),
    SignalDefinition("SIG-031", "Many small outbound transfers to related nodes", "OUTBOUND_PATTERN", 10, "candidate"),
    SignalDefinition("SIG-032", "Unusual inflow / outflow ratio shift", "FLOW_BEHAVIOR", 10, "candidate"),
    SignalDefinition("SIG-033", "Fan-in / fan-out graph topology", "FLOW_GRAPH", 20, "candidate"),
    SignalDefinition("SIG-034", "Contact detail change followed by transfer", "PROFILE_SECURITY", 15, "candidate"),
    SignalDefinition("SIG-035", "New app registration followed by transfer", "DEVICE", 10, "candidate"),
)

SIGNAL_REGISTRY = {item.signal_id: item for item in _DEFINITIONS}

FAMILY_CAPS = {
    "TRANSACTION_AMOUNT": 20,
    "TRANSACTION_VELOCITY": 25,
    "FLOW_CHAIN": 35,
    "BENEFICIARY": 25,
    "STRUCTURING": 20,
    "DEVICE": 25,
    "GEO": 20,
    "DEVICE_NETWORK": 25,
    "NETWORK_REPUTATION": 10,
    "TIME_BEHAVIOR": 10,
    "SESSION": 20,
    "ACCOUNT_SECURITY": 30,
    "BENEFICIARY_REPUTATION": 25,
    "GRAPH_ATTRIBUTES": 30,
    "FLOW_GRAPH": 35,
    "AUTH": 30,
    "ACCOUNT_BEHAVIOR": 15,
    "FLOW_BEHAVIOR": 20,
    "PAYMENT_LIFECYCLE": 15,
    "CASH_OUT": 15,
    "OUTBOUND_PATTERN": 20,
    "PROFILE_SECURITY": 20,
}
