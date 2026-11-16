from datetime import datetime, timedelta, timezone

import pytest

from finzanjir_ai.intel.autonomous_learning import CandidateStatus, ResearchCandidate
from finzanjir_ai.intel.runtime_store import LocalResearchRuntimeStore


NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def store(tmp_path):
    return LocalResearchRuntimeStore(tmp_path / "runtime.sqlite")


def test_jobs_are_disabled_by_default_and_hourly_minimum_enforced(tmp_path):
    ledger = store(tmp_path)
    job = ledger.register_job("job-1", "source-1", now=NOW)
    assert not job.enabled
    assert ledger.due_jobs(now=NOW) == []
    with pytest.raises(ValueError):
        ledger.register_job("too-fast", "source-1", interval_minutes=30, now=NOW)


def test_due_job_claim_is_exclusive_and_pause_resume_preserves_active_lease(tmp_path):
    ledger = store(tmp_path)
    ledger.register_job("job-1", "source-1", enabled=True, now=NOW)
    assert len(ledger.due_jobs(now=NOW)) == 1
    assert ledger.claim_job("job-1", now=NOW, lease_seconds=600)
    assert not ledger.claim_job("job-1", now=NOW)
    ledger.pause("job-1")
    assert ledger.due_jobs(now=NOW + timedelta(hours=1)) == []
    ledger.resume("job-1", now=NOW + timedelta(hours=1))
    assert ledger.due_jobs(now=NOW + timedelta(hours=1)) == []
    assert len(ledger.due_jobs(now=NOW + timedelta(hours=1, seconds=1))) == 1


def test_expired_lease_can_be_reclaimed(tmp_path):
    ledger = store(tmp_path)
    ledger.register_job("job-1", "source-1", enabled=True, now=NOW)
    assert ledger.claim_job("job-1", now=NOW, lease_seconds=60)
    assert ledger.claim_job("job-1", now=NOW + timedelta(seconds=61))


def test_finish_job_persists_audit_and_moves_next_run(tmp_path):
    ledger = store(tmp_path)
    ledger.register_job("job-1", "source-1", interval_minutes=120,
                        enabled=True, now=NOW)
    assert ledger.claim_job("job-1", now=NOW)
    next_job = ledger.finish_job(
        "job-1", started_at=NOW, finished_at=NOW + timedelta(minutes=5),
        status="completed", items=3, bytes_processed=900,
    )
    assert next_job.next_run_at == (NOW + timedelta(minutes=125)).isoformat(timespec="seconds")
    events = ledger.audit_events("job-1")
    assert events[0]["items"] == 3
    assert events[0]["bytes"] == 900


def test_finish_rejects_bad_status_and_negative_counters(tmp_path):
    ledger = store(tmp_path)
    ledger.register_job("job-1", "source-1", enabled=True, now=NOW)
    with pytest.raises(ValueError):
        ledger.finish_job("job-1", started_at=NOW, status="unknown")
    with pytest.raises(ValueError):
        ledger.finish_job("job-1", started_at=NOW, status="failed", items=-1)


def test_quarantined_candidate_round_trip(tmp_path):
    ledger = store(tmp_path)
    candidate = ResearchCandidate(
        candidate_id="candidate-1", source_id="source-1",
        url="https://example.org/advisory", title="Public advisory",
        text="Untrusted text retained for review", content_hash="abc",
        discovered_at=NOW.isoformat(), status=CandidateStatus.QUARANTINED,
        review_reasons=("human review required",),
    )
    ledger.save_candidate(candidate, source_mode="offline_cache")
    stored = ledger.get_candidate("candidate-1")
    assert stored.text == candidate.text
    assert stored.status == "quarantined"
    assert stored.source_mode == "offline_cache"
    ledger.save_candidate(candidate, source_mode="online")
    assert ledger.get_candidate("candidate-1").source_mode == "offline_cache"


def test_job_registration_does_not_reenable_existing_disabled_job(tmp_path):
    ledger = store(tmp_path)
    ledger.register_job("job-1", "source-1", enabled=True, now=NOW)
    ledger.set_enabled("job-1", False)
    updated = ledger.register_job("job-1", "source-1", enabled=True, now=NOW)
    assert not updated.enabled


def test_in_memory_database_is_rejected_to_preserve_runtime_state():
    with pytest.raises(ValueError):
        LocalResearchRuntimeStore(":memory:")
