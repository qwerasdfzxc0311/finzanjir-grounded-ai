import asyncio
from datetime import datetime, timedelta, timezone

from finzanjir_ai.intel.cycle_supervisor import (
    AutonomousCycleSupervisor,
    WorkCyclePolicy,
    WorkStep,
)
from finzanjir_ai.intel.runtime_store import LocalResearchRuntimeStore


NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def make_store(tmp_path):
    return LocalResearchRuntimeStore(tmp_path / "autonomy.sqlite")


def test_checkpoint_is_persisted_and_bounded(tmp_path):
    store = make_store(tmp_path)
    store.register_job("job-a", "source-a", enabled=True, now=NOW)
    store.save_checkpoint("job-a", {"cursor": "page-4", "items": 17}, now=NOW)
    assert store.get_checkpoint("job-a") == {"cursor": "page-4", "items": 17}
    try:
        store.save_checkpoint("job-a", {"payload": "x" * 70000}, now=NOW)
    except ValueError as exc:
        assert "64 KiB" in str(exc)
    else:
        raise AssertionError("oversized checkpoint was accepted")


def test_heartbeat_extends_only_an_active_unpaused_lease(tmp_path):
    store = make_store(tmp_path)
    store.register_job("job-a", "source-a", enabled=True, now=NOW)
    assert store.claim_job("job-a", now=NOW, lease_seconds=60)
    assert store.heartbeat_job("job-a", now=NOW + timedelta(seconds=10), lease_seconds=90)
    store.pause("job-a")
    assert not store.heartbeat_job("job-a", now=NOW + timedelta(seconds=20), lease_seconds=90)


def test_supervisor_runs_steps_then_takes_ten_minute_rest(tmp_path):
    store = make_store(tmp_path)
    store.register_job("job-a", "source-a", enabled=True, now=NOW)
    supervisor = AutonomousCycleSupervisor(
        store,
        WorkCyclePolicy(work_seconds=5, rest_minutes=10, lease_seconds=60),
        clock=lambda: NOW,
    )
    calls = []

    async def worker(checkpoint, remaining):
        calls.append(dict(checkpoint))
        if not checkpoint:
            return WorkStep({"cursor": "next"}, done=False, items=1, bytes_processed=10)
        return WorkStep({}, done=True, items=1, bytes_processed=20)

    result = asyncio.run(supervisor.run_cycle("job-a", worker))
    assert result["status"] == "completed"
    assert result["items"] == 2
    assert len(calls) == 2
    assert store.get_checkpoint("job-a") == {}
    assert store.get_job("job-a").next_run_at == (NOW + timedelta(minutes=10)).isoformat(timespec="seconds")


def test_failed_cycle_keeps_checkpoint_and_next_cycle_resumes(tmp_path):
    store = make_store(tmp_path)
    store.register_job("job-a", "source-a", enabled=True, now=NOW)
    current = [NOW]
    supervisor = AutonomousCycleSupervisor(
        store,
        WorkCyclePolicy(work_seconds=5, rest_minutes=10, lease_seconds=60),
        clock=lambda: current[0],
    )

    async def fails_after_checkpoint(checkpoint, remaining):
        if not checkpoint:
            return WorkStep({"cursor": "saved-page-9"}, items=9, bytes_processed=900)
        raise RuntimeError("simulated worker crash")

    first = asyncio.run(supervisor.run_cycle("job-a", fails_after_checkpoint))
    assert first["status"] == "failed"
    assert store.get_checkpoint("job-a") == {"cursor": "saved-page-9"}

    current[0] = NOW + timedelta(minutes=11)

    async def resume(checkpoint, remaining):
        assert checkpoint == {"cursor": "saved-page-9"}
        return WorkStep({}, done=True, items=1, bytes_processed=100)

    second = asyncio.run(supervisor.run_cycle("job-a", resume))
    assert second["status"] == "completed"
    assert store.get_checkpoint("job-a") == {}


def test_supervisor_does_not_claim_disabled_job(tmp_path):
    store = make_store(tmp_path)
    store.register_job("job-a", "source-a", enabled=False, now=NOW)
    supervisor = AutonomousCycleSupervisor(
        store, WorkCyclePolicy(work_seconds=1, lease_seconds=60), clock=lambda: NOW
    )

    async def worker(checkpoint, remaining):
        raise AssertionError("disabled job must not run")

    result = asyncio.run(supervisor.run_cycle("job-a", worker))
    assert result["status"] == "not_claimed"
