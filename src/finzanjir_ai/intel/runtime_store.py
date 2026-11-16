"""Persistent local runtime ledger for bounded autonomous research.

This module stores schedules, leases, quarantined candidates, and audit events.
It does not create threads, timers, network clients, or background workers.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import json
import sqlite3

from .autonomous_learning import ResearchCandidate


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return current.astimezone(timezone.utc)


def _stamp(value: datetime | None = None) -> str:
    return _utc(value).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ResearchJob:
    job_id: str
    source_id: str
    interval_minutes: int
    enabled: bool
    paused: bool
    next_run_at: str
    lease_until: str | None


@dataclass(frozen=True)
class StoredCandidate:
    candidate_id: str
    source_id: str
    url: str
    title: str
    text: str
    content_hash: str
    discovered_at: str
    status: str
    source_mode: str
    review_reasons: tuple[str, ...] = ()


class LocalResearchRuntimeStore:
    """SQLite-backed local-only schedule, quarantine, and audit ledger."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path == ":memory:":
            raise ValueError("a persistent filesystem path is required")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS research_jobs (
                    job_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    interval_minutes INTEGER NOT NULL CHECK(interval_minutes >= 60),
                    enabled INTEGER NOT NULL DEFAULT 0,
                    paused INTEGER NOT NULL DEFAULT 0,
                    next_run_at TEXT NOT NULL,
                    lease_until TEXT
                );
                CREATE TABLE IF NOT EXISTS research_audit (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    items INTEGER NOT NULL,
                    bytes INTEGER NOT NULL,
                    detail TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS research_checkpoints (
                    job_id TEXT PRIMARY KEY,
                    checkpoint_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS quarantined_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    text TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    discovered_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_mode TEXT NOT NULL
                );
            """)
            candidate_columns = {
                row[1] for row in db.execute("PRAGMA table_info(quarantined_candidates)").fetchall()
            }
            if "review_reasons_json" not in candidate_columns:
                db.execute(
                    "ALTER TABLE quarantined_candidates ADD COLUMN review_reasons_json TEXT NOT NULL DEFAULT '[]'"
                )
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def register_job(self, job_id: str, source_id: str, *,
                     interval_minutes: int = 360, enabled: bool = False,
                     now: datetime | None = None) -> ResearchJob:
        if not job_id.strip() or not source_id.strip():
            raise ValueError("job_id and source_id are required")
        if interval_minutes < 60:
            raise ValueError("research jobs may not run more frequently than hourly")
        next_run = _stamp(now)
        with self._connection() as db:
            db.execute("""
                INSERT INTO research_jobs
                    (job_id, source_id, interval_minutes, enabled, paused, next_run_at, lease_until)
                VALUES (?, ?, ?, ?, 0, ?, NULL)
                ON CONFLICT(job_id) DO UPDATE SET
                    source_id=excluded.source_id,
                    interval_minutes=excluded.interval_minutes
            """, (job_id, source_id, interval_minutes, int(enabled), next_run))
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> ResearchJob:
        with self._connection() as db:
            row = db.execute("""
                SELECT job_id, source_id, interval_minutes, enabled, paused, next_run_at, lease_until
                FROM research_jobs WHERE job_id=?
            """, (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return ResearchJob(row[0], row[1], row[2], bool(row[3]), bool(row[4]), row[5], row[6])

    def set_enabled(self, job_id: str, enabled: bool) -> ResearchJob:
        with self._connection() as db:
            changed = db.execute(
                "UPDATE research_jobs SET enabled=? WHERE job_id=?",
                (int(enabled), job_id),
            ).rowcount
        if not changed:
            raise KeyError(job_id)
        return self.get_job(job_id)

    def pause(self, job_id: str) -> ResearchJob:
        # Keep any active lease: the host must cancel its worker before releasing it.
        with self._connection() as db:
            changed = db.execute(
                "UPDATE research_jobs SET paused=1 WHERE job_id=?",
                (job_id,),
            ).rowcount
        if not changed:
            raise KeyError(job_id)
        return self.get_job(job_id)

    def resume(self, job_id: str, *, now: datetime | None = None) -> ResearchJob:
        # An existing lease remains effective until the worker finishes or it expires.
        with self._connection() as db:
            changed = db.execute(
                "UPDATE research_jobs SET paused=0, next_run_at=? WHERE job_id=?",
                (_stamp(now), job_id),
            ).rowcount
        if not changed:
            raise KeyError(job_id)
        return self.get_job(job_id)

    def due_jobs(self, *, now: datetime | None = None, limit: int = 20) -> list[ResearchJob]:
        if limit < 1:
            return []
        instant = _stamp(now)
        with self._connection() as db:
            rows = db.execute("""
                SELECT job_id, source_id, interval_minutes, enabled, paused, next_run_at, lease_until
                FROM research_jobs
                WHERE enabled=1 AND paused=0 AND next_run_at<=?
                  AND (lease_until IS NULL OR lease_until<=?)
                ORDER BY next_run_at, job_id LIMIT ?
            """, (instant, instant, limit)).fetchall()
        return [ResearchJob(r[0], r[1], r[2], bool(r[3]), bool(r[4]), r[5], r[6])
                for r in rows]

    def claim_job(self, job_id: str, *, now: datetime | None = None,
                  lease_seconds: int = 300) -> bool:
        if lease_seconds < 1 or lease_seconds > 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        instant = _utc(now)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""
                SELECT enabled, paused, next_run_at, lease_until
                FROM research_jobs WHERE job_id=?
            """, (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            lease_expired = row[3] is None or row[3] <= _stamp(instant)
            if not row[0] or row[1] or row[2] > _stamp(instant) or not lease_expired:
                return False
            lease_until = _stamp(instant + timedelta(seconds=lease_seconds))
            db.execute("UPDATE research_jobs SET lease_until=? WHERE job_id=?",
                       (lease_until, job_id))
        return True

    def heartbeat_job(self, job_id: str, *, now: datetime | None = None,
                      lease_seconds: int = 300) -> bool:
        if lease_seconds < 1 or lease_seconds > 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        instant = _utc(now)
        with self._connection() as db:
            changed = db.execute("""
                UPDATE research_jobs SET lease_until=?
                WHERE job_id=? AND enabled=1 AND paused=0 AND lease_until>?
            """, (_stamp(instant + timedelta(seconds=lease_seconds)),
                  job_id, _stamp(instant))).rowcount
        return changed == 1

    def save_checkpoint(self, job_id: str, checkpoint: dict,
                        *, now: datetime | None = None) -> None:
        if not isinstance(checkpoint, dict):
            raise ValueError("checkpoint must be an object")
        encoded = json.dumps(checkpoint, ensure_ascii=False, sort_keys=True)
        if len(encoded.encode("utf-8")) > 65536:
            raise ValueError("checkpoint exceeds 64 KiB")
        with self._connection() as db:
            exists = db.execute(
                "SELECT 1 FROM research_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            if not exists:
                raise KeyError(job_id)
            db.execute("""
                INSERT INTO research_checkpoints(job_id, checkpoint_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    checkpoint_json=excluded.checkpoint_json,
                    updated_at=excluded.updated_at
            """, (job_id, encoded, _stamp(now)))

    def get_checkpoint(self, job_id: str) -> dict:
        with self._connection() as db:
            row = db.execute(
                "SELECT checkpoint_json FROM research_checkpoints WHERE job_id=?",
                (job_id,),
            ).fetchone()
        if row is None:
            return {}
        value = json.loads(row[0])
        if not isinstance(value, dict):
            raise ValueError("stored checkpoint is not an object")
        return value

    def clear_checkpoint(self, job_id: str) -> None:
        with self._connection() as db:
            db.execute("DELETE FROM research_checkpoints WHERE job_id=?", (job_id,))

    def finish_job(self, job_id: str, *, started_at: datetime,
                   finished_at: datetime | None = None, status: str,
                   items: int = 0, bytes_processed: int = 0,
                   detail: str = "", next_run_delay_minutes: int | None = None) -> ResearchJob:
        if status not in {"completed", "failed", "partial", "no_items"}:
            raise ValueError("unsupported cycle status")
        if items < 0 or bytes_processed < 0:
            raise ValueError("items and bytes_processed must be non-negative")
        start = _utc(started_at)
        finish = _utc(finished_at)
        if next_run_delay_minutes is not None and not 0 <= next_run_delay_minutes <= 1440:
            raise ValueError("next_run_delay_minutes must be between 0 and 1440")
        if finish < start:
            raise ValueError("finished_at cannot precede started_at")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT interval_minutes FROM research_jobs WHERE job_id=?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            delay = row[0] if next_run_delay_minutes is None else next_run_delay_minutes
            next_run = _stamp(finish + timedelta(minutes=delay))
            db.execute("""
                INSERT INTO research_audit
                    (job_id, started_at, finished_at, status, items, bytes, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (job_id, _stamp(start), _stamp(finish), status,
                  items, bytes_processed, detail[:2000]))
            db.execute("""
                UPDATE research_jobs SET next_run_at=?, lease_until=NULL WHERE job_id=?
            """, (next_run, job_id))
        return self.get_job(job_id)

    def save_candidate(self, candidate: ResearchCandidate, *, source_mode: str) -> None:
        if source_mode not in {"offline_cache", "online"}:
            raise ValueError("source_mode must be offline_cache or online")
        with self._connection() as db:
            db.execute("""
                INSERT OR IGNORE INTO quarantined_candidates
                    (candidate_id, source_id, url, title, text, content_hash,
                     discovered_at, status, source_mode, review_reasons_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (candidate.candidate_id, candidate.source_id, candidate.url,
                  candidate.title, candidate.text, candidate.content_hash,
                  candidate.discovered_at, candidate.status.value, source_mode,
                  json.dumps(list(candidate.review_reasons), ensure_ascii=False)))

    def get_candidate(self, candidate_id: str) -> StoredCandidate | None:
        with self._connection() as db:
            row = db.execute("""
                SELECT candidate_id, source_id, url, title, text, content_hash,
                       discovered_at, status, source_mode, review_reasons_json
                FROM quarantined_candidates WHERE candidate_id=?
            """, (candidate_id,)).fetchone()
        if row is None:
            return None
        values = list(row)
        try:
            values[-1] = tuple(json.loads(values[-1]))
        except (TypeError, ValueError):
            values[-1] = ()
        return StoredCandidate(*values)

    def audit_events(self, job_id: str, *, limit: int = 50) -> list[dict]:
        with self._connection() as db:
            rows = db.execute("""
                SELECT event_id, job_id, started_at, finished_at, status, items, bytes, detail
                FROM research_audit WHERE job_id=? ORDER BY event_id DESC LIMIT ?
            """, (job_id, max(0, min(limit, 500)))).fetchall()
        keys = ("event_id", "job_id", "started_at", "finished_at",
                "status", "items", "bytes", "detail")
        return [dict(zip(keys, row)) for row in rows]
