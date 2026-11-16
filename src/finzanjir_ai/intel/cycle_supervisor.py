"""Crash-resumable bounded work-cycle supervisor.

The host supplies a task handler and starts run_forever only after explicit
operator enablement. Each worker step must return a JSON-safe checkpoint.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Mapping, Any
import time

from .runtime_store import LocalResearchRuntimeStore


@dataclass(frozen=True)
class WorkCyclePolicy:
    work_seconds: int = 3600
    rest_minutes: int = 10
    lease_seconds: int = 300
    poll_seconds: float = 5.0
    max_steps_per_cycle: int = 500

    def __post_init__(self):
        if not 1 <= self.work_seconds <= 3600:
            raise ValueError("work_seconds must be between 1 and 3600")
        if not 1 <= self.rest_minutes <= 1440:
            raise ValueError("rest_minutes must be between 1 and 1440")
        if not 10 <= self.lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 10 and 3600")
        if self.poll_seconds <= 0 or not 1 <= self.max_steps_per_cycle <= 10000:
            raise ValueError("invalid scheduler polling or step limit")


@dataclass(frozen=True)
class WorkStep:
    checkpoint: dict[str, Any]
    done: bool = False
    items: int = 0
    bytes_processed: int = 0
    detail: str = ""


Worker = Callable[[dict[str, Any], float], Awaitable[WorkStep]]


class AutonomousCycleSupervisor:
    """Leased, checkpointed work cycles with a fixed rest period."""

    def __init__(
        self,
        store: LocalResearchRuntimeStore,
        policy: WorkCyclePolicy | None = None,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.store = store
        self.policy = policy or WorkCyclePolicy()
        self.clock = clock
        self.monotonic = monotonic
        self.sleeper = sleeper

    async def run_cycle(self, job_id: str, worker: Worker) -> dict[str, Any]:
        started = self.clock()
        if not self.store.claim_job(
            job_id, now=started, lease_seconds=self.policy.lease_seconds
        ):
            return {"status": "not_claimed", "job_id": job_id}

        checkpoint = self.store.get_checkpoint(job_id)
        deadline = self.monotonic() + self.policy.work_seconds
        items = 0
        byte_count = 0
        steps = 0
        status = "partial"
        detail = "Ish vaqti yoki bosqich limiti tugadi."
        while self.monotonic() < deadline and steps < self.policy.max_steps_per_cycle:
            job = self.store.get_job(job_id)
            if not job.enabled or job.paused:
                detail = "Vazifa operator tomonidan to‘xtatildi."
                break
            remaining = max(0.01, deadline - self.monotonic())
            step_timeout = min(remaining, self.policy.lease_seconds / 2)
            try:
                result = await asyncio.wait_for(worker(checkpoint, remaining), timeout=step_timeout)
            except asyncio.TimeoutError:
                detail = "Ishchi bosqich vaqt chegarasidan oshdi; checkpoint saqlandi."
                break
            except Exception as exc:
                status = "failed"
                detail = f"Ishchi xatosi: {type(exc).__name__}"
                break
            if not isinstance(result, WorkStep):
                status = "failed"
                detail = "Ishchi noto‘g‘ri natija formatini qaytardi."
                break
            if result.items < 0 or result.bytes_processed < 0:
                status = "failed"
                detail = "Ishchi manfiy hisoblagich qaytardi."
                break
            self.store.save_checkpoint(job_id, result.checkpoint, now=self.clock())
            checkpoint = result.checkpoint
            items += result.items
            byte_count += result.bytes_processed
            steps += 1
            detail = result.detail[:2000]
            if not self.store.heartbeat_job(
                job_id, now=self.clock(), lease_seconds=self.policy.lease_seconds
            ):
                status = "failed"
                detail = "Ishchi ijarasi yo‘qoldi; boshqa jarayon vazifani egallagan bo‘lishi mumkin."
                break
            if result.done:
                status = "completed"
                self.store.clear_checkpoint(job_id)
                break
            await self.sleeper(0)

        finished = self.clock()
        self.store.finish_job(
            job_id, started_at=started, finished_at=finished, status=status,
            items=items, bytes_processed=byte_count, detail=detail,
            next_run_delay_minutes=self.policy.rest_minutes,
        )
        return {
            "job_id": job_id, "status": status, "steps": steps,
            "items": items, "bytes_processed": byte_count,
            "checkpoint_retained": status != "completed",
            "next_cycle_after_minutes": self.policy.rest_minutes,
            "detail": detail,
        }

    async def run_forever(
        self,
        handlers: Mapping[str, Worker],
        stop_event: asyncio.Event,
    ) -> None:
        """Run due jobs serially; host must opt in and provide safe handlers."""
        while not stop_event.is_set():
            for job in self.store.due_jobs(now=self.clock(), limit=20):
                if stop_event.is_set():
                    break
                worker = handlers.get(job.source_id)
                if worker is None:
                    continue
                await self.run_cycle(job.job_id, worker)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.policy.poll_seconds)
            except asyncio.TimeoutError:
                pass
