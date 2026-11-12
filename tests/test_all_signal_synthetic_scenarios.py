import json
from pathlib import Path

from finzanjir_ai.risk.pipeline import process_transaction
from finzanjir_ai.risk.registry import SIGNAL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]


def _observation(scenario, signal_id, evidence_id, corroborating=None):
    return {
        "signal_id": signal_id,
        "condition_met": True,
        "evidence_id": evidence_id,
        "source": "synthetic-scenario-catalog",
        "observed_at": "2026-11-12T09:00:00Z",
        "evidence_quality": 1.0,
        "recency_factor": 1.0,
        "corroborating_signal_ids": corroborating or [],
        "rule_version": "scenario-rule-v1",
        "detector_version": "scenario-adapter-v1",
        "scope": "bank_internal",
        "data_mode": "synthetic",
    }


def test_synthetic_scenario_catalog_covers_all_40_registry_signals():
    catalog = json.loads(
        (ROOT / "contracts" / "signal_synthetic_scenarios_v1.json").read_text(encoding="utf-8")
    )
    scenario_ids = {item["signal_id"] for item in catalog["scenarios"]}

    assert catalog["scenario_count"] == 40
    assert len(catalog["scenarios"]) == 40
    assert scenario_ids == set(SIGNAL_REGISTRY)


def test_each_of_40_signals_runs_through_observation_adapter_and_scoring():
    catalog = json.loads(
        (ROOT / "contracts" / "signal_synthetic_scenarios_v1.json").read_text(encoding="utf-8")
    )

    for scenario in catalog["scenarios"]:
        target_id = scenario["signal_id"]
        observations = [
            _observation(
                scenario,
                target_id,
                f"evidence-{target_id}",
                [scenario["corroborator_signal_id"]] if scenario["corroborator_signal_id"] else [],
            )
        ]
        if scenario["corroborator_signal_id"]:
            corroborator = scenario["corroborator_signal_id"]
            observations.append(_observation(
                scenario,
                corroborator,
                f"evidence-{target_id}-corroborator",
            ))

        result = process_transaction(
            {
                "transaction_id": f"TX-{scenario['scenario_id']}",
                "bank_id": "bank-synthetic",
                "actor_id": "actor-synthetic",
                "amount": 2500,
                "occurred_at": "2026-11-12T09:00:00Z",
                "synthetic": True,
                "signal_observations": observations,
                "shadow_mode": True,
            },
            signal_amount_threshold=1000,
            escalation_threshold=0.75,
        )

        target_contribution = next(
            item for item in result.risk["contributions"]
            if item["signal_id"] == target_id
        )
        assert target_contribution["base_weight"] == scenario["expected_base_weight"]
        assert target_contribution["raw_contribution"] == scenario["expected_target_contribution"]
        assert target_contribution["score_eligible"] is scenario["expected_score_eligible"]
        assert result.risk["score"] == scenario["expected_total_score"]
        assert result.risk["evidence_count"] == scenario["expected_evidence_count"]
        assert result.risk["independent_families"] == scenario["expected_independent_families"]
        assert result.risk["case_eligible"] is scenario["expected_case_eligible"]
        assert result.case is None
        assert result.risk["shadow_mode"] is True


def test_all_single_signal_scenarios_are_blocked_from_opening_a_case():
    catalog = json.loads(
        (ROOT / "contracts" / "signal_synthetic_scenarios_v1.json").read_text(encoding="utf-8")
    )
    assert all(item["expected_case_eligible"] is False for item in catalog["scenarios"])
