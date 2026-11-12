from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import os
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4


class PrototypeRunStore:
    """Persist privacy-minimized summaries of explicitly synthetic prototype runs."""

    RISK_LEVELS = frozenset({"CRITICAL", "HIGH", "ELEVATED", "MEDIUM", "LOW", "OBSERVE"})

    def __init__(self, database_path: str | Path, *, retention_days: int = 30) -> None:
        if not isinstance(retention_days, int) or isinstance(retention_days, bool) or not 1 <= retention_days <= 365:
            raise ValueError("retention_days must be an integer between 1 and 365")
        self.database_path = Path(database_path)
        self.retention_days = retention_days
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prototype_run_history (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    data_mode TEXT NOT NULL CHECK (data_mode = 'synthetic'),
                    risk_score REAL NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
                    risk_level TEXT NOT NULL CHECK (risk_level IN ('CRITICAL','HIGH','ELEVATED','MEDIUM','LOW','OBSERVE')),
                    threshold REAL NOT NULL CHECK (threshold >= 0 AND threshold <= 100),
                    signal_count INTEGER NOT NULL CHECK (signal_count >= 0),
                    evidence_count INTEGER NOT NULL CHECK (evidence_count >= 0),
                    independent_families INTEGER NOT NULL CHECK (independent_families >= 0),
                    case_eligible INTEGER NOT NULL CHECK (case_eligible IN (0,1)),
                    case_opened INTEGER NOT NULL CHECK (case_opened IN (0,1)),
                    shadow_mode INTEGER NOT NULL CHECK (shadow_mode IN (0,1)),
                    engine_version TEXT NOT NULL,
                    registry_version TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_prototype_run_created_at ON prototype_run_history(created_at DESC)"
            )

    @staticmethod
    def _finite_number(value: Any, field: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError(f"{field} must be a finite number")
        return float(value)

    def save(self, summary: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(summary, dict):
            raise ValueError("summary must be an object")
        if summary.get("data_mode") != "synthetic":
            raise ValueError("only synthetic prototype summaries may be stored")
        score = self._finite_number(summary.get("risk_score"), "risk_score")
        threshold = self._finite_number(summary.get("threshold"), "threshold")
        if not 0 <= score <= 100 or not 0 <= threshold <= 100:
            raise ValueError("risk_score and threshold must be between 0 and 100")
        risk_level = summary.get("risk_level")
        if risk_level not in self.RISK_LEVELS:
            raise ValueError("risk_level is invalid")
        counts: dict[str, int] = {}
        for field in ("signal_count", "evidence_count", "independent_families"):
            value = summary.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
            counts[field] = value
        flags: dict[str, int] = {}
        for field in ("case_eligible", "case_opened", "shadow_mode"):
            value = summary.get(field)
            if not isinstance(value, bool):
                raise ValueError(f"{field} must be boolean")
            flags[field] = int(value)
        versions: dict[str, str] = {}
        for field in ("engine_version", "registry_version"):
            value = summary.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
            versions[field] = value.strip()

        run = {
            "run_id": f"run-{uuid4().hex}",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "data_mode": "synthetic",
            "risk_score": round(score, 2),
            "risk_level": risk_level,
            "threshold": round(threshold, 2),
            **counts,
            **flags,
            **versions,
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO prototype_run_history (
                    run_id, created_at, data_mode, risk_score, risk_level, threshold,
                    signal_count, evidence_count, independent_families,
                    case_eligible, case_opened, shadow_mode, engine_version, registry_version
                ) VALUES (
                    :run_id, :created_at, :data_mode, :risk_score, :risk_level, :threshold,
                    :signal_count, :evidence_count, :independent_families,
                    :case_eligible, :case_opened, :shadow_mode, :engine_version, :registry_version
                )
                """,
                run,
            )
            cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat().replace("+00:00", "Z")
            connection.execute("DELETE FROM prototype_run_history WHERE created_at < ?", (cutoff,))
        return run

    def list_recent(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer between 1 and 100")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat().replace("+00:00", "Z")
        with self._connect() as connection:
            connection.execute("DELETE FROM prototype_run_history WHERE created_at < ?", (cutoff,))
            rows = connection.execute(
                """
                SELECT run_id, created_at, data_mode, risk_score, risk_level, threshold,
                       signal_count, evidence_count, independent_families,
                       case_eligible, case_opened, shadow_mode, engine_version, registry_version
                FROM prototype_run_history
                ORDER BY created_at DESC, run_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            for field in ("case_eligible", "case_opened", "shadow_mode"):
                item[field] = bool(item[field])
            results.append(item)
        return results


def default_database_path() -> Path:
    configured = os.getenv("FINZANJIR_PROTOTYPE_DB_PATH")
    return Path(configured) if configured else Path("var/finzanjir-prototype.sqlite3")
