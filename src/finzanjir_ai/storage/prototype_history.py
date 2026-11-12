from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
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
        with closing(self._connect()) as connection:
            with connection:
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
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS prototype_cases (
                        case_ref TEXT PRIMARY KEY,
                        run_id TEXT NOT NULL REFERENCES prototype_run_history(run_id) ON DELETE CASCADE,
                        created_at TEXT NOT NULL,
                        data_mode TEXT NOT NULL CHECK (data_mode = 'synthetic'),
                        risk_score REAL NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
                        risk_level TEXT NOT NULL CHECK (risk_level IN ('CRITICAL','HIGH','ELEVATED','MEDIUM','LOW','OBSERVE')),
                        threshold REAL NOT NULL CHECK (threshold >= 0 AND threshold <= 100),
                        signal_ids_json TEXT NOT NULL,
                        evidence_count INTEGER NOT NULL CHECK (evidence_count >= 0),
                        independent_families INTEGER NOT NULL CHECK (independent_families >= 0),
                        case_status TEXT NOT NULL CHECK (case_status IN ('OPEN','IN_REVIEW','BANK_REVIEW_SIMULATED','CLOSED_DEMO')),
                        review_decision TEXT,
                        reviewed_at TEXT,
                        is_authoritative INTEGER NOT NULL DEFAULT 0 CHECK (is_authoritative = 0)
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_prototype_case_created_at ON prototype_cases(created_at DESC)"
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS prototype_audit_events (
                        event_id TEXT PRIMARY KEY,
                        run_id TEXT NOT NULL REFERENCES prototype_run_history(run_id) ON DELETE CASCADE,
                        case_ref TEXT REFERENCES prototype_cases(case_ref) ON DELETE CASCADE,
                        occurred_at TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        actor_role TEXT NOT NULL,
                        decision TEXT,
                        scope TEXT NOT NULL CHECK (scope = 'bank_internal'),
                        data_mode TEXT NOT NULL CHECK (data_mode = 'synthetic'),
                        is_authoritative INTEGER NOT NULL DEFAULT 0 CHECK (is_authoritative = 0),
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_prototype_audit_occurred_at ON prototype_audit_events(occurred_at DESC)"
                )
        if os.name == "posix":
            self.database_path.chmod(0o600)

    @staticmethod
    def _finite_number(value: Any, field: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError(f"{field} must be a finite number")
        return float(value)

    def save(self, summary: dict[str, Any], *, case_summary: dict[str, Any] | None = None) -> dict[str, Any]:
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
        case_record = None
        case_opened_event = None
        if case_summary is not None:
            if not isinstance(case_summary, dict) or case_summary.get("data_mode") != "synthetic":
                raise ValueError("only synthetic case summaries may be stored")
            signal_ids = case_summary.get("signal_ids")
            if (
                not isinstance(signal_ids, list)
                or not signal_ids
                or len(signal_ids) > 40
                or any(not isinstance(item, str) or not item.strip() for item in signal_ids)
            ):
                raise ValueError("case signal_ids must contain 1 to 40 non-empty signal IDs")
            case_evidence_count = case_summary.get("evidence_count")
            case_families = case_summary.get("independent_families")
            for field, value in (("evidence_count", case_evidence_count), ("independent_families", case_families)):
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ValueError(f"case {field} must be a non-negative integer")
            case_record = {
                "case_ref": f"case-{uuid4().hex}",
                "run_id": run["run_id"],
                "created_at": run["created_at"],
                "data_mode": "synthetic",
                "risk_score": run["risk_score"],
                "risk_level": run["risk_level"],
                "threshold": run["threshold"],
                "signal_ids_json": json.dumps(signal_ids, separators=(",", ":")),
                "evidence_count": case_evidence_count,
                "independent_families": case_families,
                "case_status": "OPEN",
                "review_decision": None,
                "reviewed_at": None,
                "is_authoritative": 0,
            }
            case_opened_event = {
                "event_id": f"event-{uuid4().hex}",
                "run_id": run["run_id"],
                "case_ref": case_record["case_ref"],
                "occurred_at": run["created_at"],
                "event_type": "SYNTHETIC_CASE_OPENED",
                "actor_role": "synthetic_system",
                "decision": None,
                "scope": "bank_internal",
                "data_mode": "synthetic",
                "is_authoritative": 0,
                "payload_json": json.dumps({
                    "risk_score": run["risk_score"],
                    "risk_level": run["risk_level"],
                    "signal_ids": signal_ids,
                    "evidence_count": case_evidence_count,
                    "independent_families": case_families,
                    "case_status": "OPEN",
                }, separators=(",", ":")),
            }

        with closing(self._connect()) as connection:
            with connection:
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
                if case_record is not None and case_opened_event is not None:
                    connection.execute(
                        """
                        INSERT INTO prototype_cases (
                            case_ref, run_id, created_at, data_mode, risk_score, risk_level,
                            threshold, signal_ids_json, evidence_count, independent_families,
                            case_status, review_decision, reviewed_at, is_authoritative
                        ) VALUES (
                            :case_ref, :run_id, :created_at, :data_mode, :risk_score, :risk_level,
                            :threshold, :signal_ids_json, :evidence_count, :independent_families,
                            :case_status, :review_decision, :reviewed_at, :is_authoritative
                        )
                        """,
                        case_record,
                    )
                    connection.execute(
                        """
                        INSERT INTO prototype_audit_events (
                            event_id, run_id, case_ref, occurred_at, event_type, actor_role,
                            decision, scope, data_mode, is_authoritative, payload_json
                        ) VALUES (
                            :event_id, :run_id, :case_ref, :occurred_at, :event_type, :actor_role,
                            :decision, :scope, :data_mode, :is_authoritative, :payload_json
                        )
                        """,
                        case_opened_event,
                    )
                connection.execute("DELETE FROM prototype_run_history WHERE created_at < ?", (cutoff,))
        if case_record is not None:
            run["case_ref"] = case_record["case_ref"]
        return run

    def list_recent(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer between 1 and 100")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat().replace("+00:00", "Z")
        with closing(self._connect()) as connection:
            with connection:
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

    @staticmethod
    def _case_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["signal_ids"] = json.loads(item.pop("signal_ids_json"))
        item["is_authoritative"] = bool(item["is_authoritative"])
        return item

    def get_case(self, case_ref: str) -> dict[str, Any]:
        if not isinstance(case_ref, str) or not case_ref.startswith("case-"):
            raise ValueError("case_ref is invalid")
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT case_ref, run_id, created_at, data_mode, risk_score, risk_level,
                       threshold, signal_ids_json, evidence_count, independent_families,
                       case_status, review_decision, reviewed_at, is_authoritative
                FROM prototype_cases WHERE case_ref = ?
                """,
                (case_ref,),
            ).fetchone()
        if row is None:
            raise ValueError("unknown synthetic case")
        return self._case_row(row)

    def list_cases(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer between 1 and 100")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat().replace("+00:00", "Z")
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("DELETE FROM prototype_run_history WHERE created_at < ?", (cutoff,))
                rows = connection.execute(
                    """
                    SELECT case_ref, run_id, created_at, data_mode, risk_score, risk_level,
                           threshold, signal_ids_json, evidence_count, independent_families,
                           case_status, review_decision, reviewed_at, is_authoritative
                    FROM prototype_cases
                    ORDER BY created_at DESC, case_ref DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [self._case_row(row) for row in rows]

    def review_case(self, case_ref: str, *, decision: str) -> dict[str, Any]:
        transitions = {
            "REQUEST_MORE_EVIDENCE": "IN_REVIEW",
            "REFER_TO_BANK_REVIEW": "BANK_REVIEW_SIMULATED",
            "CLOSE_AS_BENIGN_DEMO": "CLOSED_DEMO",
        }
        if decision not in transitions:
            raise ValueError("decision must be REQUEST_MORE_EVIDENCE, REFER_TO_BANK_REVIEW or CLOSE_AS_BENIGN_DEMO")
        if not isinstance(case_ref, str) or not case_ref.startswith("case-"):
            raise ValueError("case_ref is invalid")
        reviewed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        event = {
            "event_id": f"event-{uuid4().hex}",
            "occurred_at": reviewed_at,
            "event_type": "SYNTHETIC_CASE_REVIEWED",
            "actor_role": "demo_reviewer",
            "decision": decision,
            "scope": "bank_internal",
            "data_mode": "synthetic",
            "is_authoritative": 0,
        }
        with closing(self._connect()) as connection:
            with connection:
                row = connection.execute(
                    "SELECT run_id, case_status FROM prototype_cases WHERE case_ref = ?",
                    (case_ref,),
                ).fetchone()
                if row is None:
                    raise ValueError("unknown synthetic case")
                if row["case_status"] == "CLOSED_DEMO":
                    raise ValueError("synthetic case is already closed")
                event["run_id"] = row["run_id"]
                event["case_ref"] = case_ref
                event["payload_json"] = json.dumps(
                    {"case_ref": case_ref, "case_status": transitions[decision], "decision": decision},
                    separators=(",", ":"),
                )
                connection.execute(
                    """
                    UPDATE prototype_cases
                    SET case_status = ?, review_decision = ?, reviewed_at = ?, is_authoritative = 0
                    WHERE case_ref = ?
                    """,
                    (transitions[decision], decision, reviewed_at, case_ref),
                )
                connection.execute(
                    """
                    INSERT INTO prototype_audit_events (
                        event_id, run_id, case_ref, occurred_at, event_type, actor_role,
                        decision, scope, data_mode, is_authoritative, payload_json
                    ) VALUES (
                        :event_id, :run_id, :case_ref, :occurred_at, :event_type, :actor_role,
                        :decision, :scope, :data_mode, :is_authoritative, :payload_json
                    )
                    """,
                    event,
                )
        return self.get_case(case_ref)

    def list_audit_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200:
            raise ValueError("limit must be an integer between 1 and 200")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).isoformat().replace("+00:00", "Z")
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("DELETE FROM prototype_run_history WHERE created_at < ?", (cutoff,))
                rows = connection.execute(
                    """
                    SELECT event_id, run_id, case_ref, occurred_at, event_type, actor_role,
                           decision, scope, data_mode, is_authoritative, payload_json
                    FROM prototype_audit_events
                    ORDER BY occurred_at DESC, event_id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["is_authoritative"] = bool(item["is_authoritative"])
            item["payload"] = json.loads(item.pop("payload_json"))
            results.append(item)
        return results



def default_database_path() -> Path:
    configured = os.getenv("FINZANJIR_PROTOTYPE_DB_PATH")
    return Path(configured) if configured else Path("var/finzanjir-prototype.sqlite3")
