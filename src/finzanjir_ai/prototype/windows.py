from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrototypeWindow:
    window_id: str
    purpose: str


@dataclass(frozen=True)
class PrototypeWindowRegistry:
    windows: tuple[PrototypeWindow, ...]
    layers: tuple[tuple[str, str], ...]
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
    layers = (
        ("layer_01", "Dalil va ma’lumot kelib chiqishini kuzatish"),
        ("layer_02", "Ma’lumot sifati va ishonchliligi"),
        ("layer_03", "Xavf va noaniqlikni boshqarish"),
        ("layer_04", "Inson nazorati va xatoni tuzatish"),
        ("layer_05", "Qoidalar va modellarni boshqarish"),
        ("layer_06", "Ma’lumotni oshkor qilish va almashish nazorati"),
        ("layer_07", "Avtomatik jarayonlar xavfsizligi"),
        ("layer_08", "Tranzaksiya zanjiri va Case bog‘liqligi"),
        ("layer_09", "Fuqaro shaffofligi va e’tiroz"),
        ("layer_10", "Maxfiylik va ma’lumotlar hayotiy sikli"),
        ("layer_11", "Xavfsizlik hodisasiga javob"),
        ("layer_12", "Bilimlar bazasi va AI ishonchliligi"),
        ("layer_13", "Sinov va mustaqil baholash"),
        ("layer_14", "Bank integratsiyasiga tayyorlik"),
        ("layer_15", "Samaradorlik va quvvat"),
        ("layer_16", "Ta’sir va zarar kamayishini o‘lchash"),
    )
    return PrototypeWindowRegistry(
        windows=windows,
        layers=layers,
        shared_event_flow="Transaction→Signal→Evidence→Risk→Threshold→Case→HumanDecision→Audit/KPI→AI",
        cross_bank_scope="separate_access_boundary",
    )
