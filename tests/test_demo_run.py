from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.prototype.demo import run_full_demo
from finzanjir_ai.risk.scenarios import build_synthetic_case_signal_events


def test_full_synthetic_demo_returns_all_major_outputs():
    index = build_knowledge_index([{"id":"ck-demo","concept_id":"c-demo","canonical_concept_id":"c-demo","statement":"Evidence supports risk assessment and case escalation.","aliases":["case escalation"],"evidence":{"status":"supported"},"provenance":[{"source":"canonical-v0.6"}],"reconciliation":{}}])
    tx = {"transaction_id":"syn-demo-1","bank_id":"bank-a","actor_id":"actor-1","amount":2500,"currency":"UZS","occurred_at":"2026-11-11T00:00:01Z","channel":"mobile","status":"AUTHORIZED","synthetic":True,"signal_events":build_synthetic_case_signal_events(transaction_id="syn-demo-1", observed_at="2026-11-11T00:00:01Z"),"shadow_mode":False}
    result = run_full_demo(tx, knowledge_index=index)
    assert result["case"] is not None
    assert result["decision"] is not None
    assert result["ai"].answer.abstained is False
    assert result["kpi"]["data_mode"] == "synthetic"
