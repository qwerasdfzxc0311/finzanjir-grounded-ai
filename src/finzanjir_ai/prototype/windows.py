from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrototypeWindow:
    window_id: str
    purpose: str


@dataclass(frozen=True)
class PrototypeWindowRegistry:
    windows: tuple[PrototypeWindow, ...]
    layers: tuple[str, ...]
    shared_event_flow: str
    cross_bank_scope: str


def build_window_registry() -> PrototypeWindowRegistry:
    windows = (
        PrototypeWindow("dashboard", "system overview"),
        PrototypeWindow("citizen", "citizen-facing safety state"),
        PrototypeWindow("human_case", "authorized human case review"),
        PrototypeWindow("synthetic_bank", "synthetic source and transaction demo"),
        PrototypeWindow("signal_risk", "signal, evidence, risk and threshold view"),
        PrototypeWindow("cross_bank_fraud", "authorized cross-bank analysis"),
        PrototypeWindow("audit_kpi", "audit trail and synthetic KPI"),
        PrototypeWindow("finzanjir_ai", "grounded AI explanation"),
        PrototypeWindow("layers_16", "sixteen-layer architecture view"),
    )
    layers = tuple(f"layer_{index:02d}" for index in range(1, 17))
    return PrototypeWindowRegistry(
        windows=windows,
        layers=layers,
        shared_event_flow="Transaction→Signal→Evidence→Risk→Threshold→Case→HumanDecision→Audit/KPI→AI",
        cross_bank_scope="separate_access_boundary",
    )
