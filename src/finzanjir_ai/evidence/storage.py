from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from .provenance import SyntheticEvidenceProvenanceChain, _required_opaque


class SQLiteSyntheticEvidenceProvenanceStore:
    """Local SQLite persistence for synthetic provenance metadata only.

    This supports process-restart replay on a persistent local filesystem.
    It does not provide encryption at rest, backups, remote durability,
    source authentication, or a production retention policy.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        if os.name == "posix":
            self.database_path.chmod(0o600)

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
                    CREATE TABLE IF NOT EXISTS synthetic_evidence_provenance (
                        chain_id TEXT NOT NULL,
                        sequence INTEGER NOT NULL CHECK (sequence >= 1),
                        record_hash TEXT NOT NULL,
                        data_mode TEXT NOT NULL CHECK (data_mode = 'synthetic'),
                        record_json TEXT NOT NULL,
                        PRIMARY KEY (chain_id, sequence),
                        UNIQUE (chain_id, record_hash)
                    )
                    """
                )

    def get_records(self, chain_id: str) -> list[dict[str, Any]]:
        normalized_chain_id = _required_opaque(chain_id, "chain_id")
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT record_json
                FROM synthetic_evidence_provenance
                WHERE chain_id = ?
                ORDER BY sequence ASC
                """,
                (normalized_chain_id,),
            ).fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            try:
                record = json.loads(row["record_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError("stored provenance record is not valid JSON") from exc
            if not isinstance(record, dict):
                raise ValueError("stored provenance record must be an object")
            records.append(record)
        return records

    def append(
        self,
        *,
        chain_id: str,
        evidence_id: str,
        event_id: str,
        source: str,
        observed_at: str,
        acquisition_method: str,
        source_version: str,
        payload_digest: str,
        data_mode: str = "synthetic",
    ) -> dict[str, Any]:
        normalized_chain_id = _required_opaque(chain_id, "chain_id")
        if data_mode != "synthetic":
            raise ValueError("provenance store accepts synthetic data only")

        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT record_json
                FROM synthetic_evidence_provenance
                WHERE chain_id = ?
                ORDER BY sequence ASC
                """,
                (normalized_chain_id,),
            ).fetchall()
            existing: list[dict[str, Any]] = []
            for row in rows:
                try:
                    record = json.loads(row["record_json"])
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValueError("stored provenance record is not valid JSON") from exc
                if not isinstance(record, dict):
                    raise ValueError("stored provenance record must be an object")
                existing.append(record)

            chain = SyntheticEvidenceProvenanceChain()
            verification = chain.verify(existing)
            if not verification["valid"]:
                raise ValueError("stored provenance chain failed integrity verification")

            for record in existing:
                chain.append(
                    evidence_id=record["evidence_id"],
                    event_id=record["event_id"],
                    source=record["source"],
                    observed_at=record["observed_at"],
                    acquisition_method=record["acquisition_method"],
                    source_version=record["source_version"],
                    payload_digest=record["payload_digest"],
                    data_mode=record["data_mode"],
                )

            new_record = chain.append(
                evidence_id=evidence_id,
                event_id=event_id,
                source=source,
                observed_at=observed_at,
                acquisition_method=acquisition_method,
                source_version=source_version,
                payload_digest=payload_digest,
                data_mode=data_mode,
            )
            connection.execute(
                """
                INSERT INTO synthetic_evidence_provenance (
                    chain_id, sequence, record_hash, data_mode, record_json
                ) VALUES (?, ?, ?, 'synthetic', ?)
                """,
                (
                    normalized_chain_id,
                    new_record["sequence"],
                    new_record["record_hash"],
                    json.dumps(new_record, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            connection.commit()
            return new_record

    def verify(self, chain_id: str) -> dict[str, Any]:
        records = self.get_records(chain_id)
        report = SyntheticEvidenceProvenanceChain().verify(records)
        report.update({
            "durable": True,
            "storage_backend": "sqlite_local_file",
            "durability_scope": "local_filesystem_only",
            "at_rest_encryption": False,
            "external_trust_anchor": False,
        })
        return report
