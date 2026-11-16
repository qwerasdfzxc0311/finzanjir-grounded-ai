"""Encrypted, owner-scoped quarantine store for imported personal cloud content."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


MAX_TEXT_BYTES = 2_000_000


class PersonalMemoryStore:
    """Stores extracted text encrypted and isolated by the configured owner."""

    def __init__(self, path: str, encryption_key: str):
        if not Path(path).is_absolute():
            raise ValueError("personal memory database path must be absolute")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.cipher = Fernet(encryption_key.encode())
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS personal_memory_sources (
                    source_id TEXT PRIMARY KEY,
                    owner_email TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    remote_file_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    modified_time TEXT,
                    content_sha256 TEXT NOT NULL,
                    extracted_text_ciphertext BLOB NOT NULL,
                    metadata_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'quarantined',
                    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(owner_email, provider, account_id, remote_file_id)
                );
                CREATE INDEX IF NOT EXISTS idx_personal_memory_owner_status
                ON personal_memory_sources(owner_email, status, imported_at);
            """)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def quarantine(
        self, *, owner_email: str, account_id: str, remote_file_id: str,
        file_name: str, mime_type: str, modified_time: str | None,
        extracted_text: str, metadata: dict[str, Any] | None = None,
        provider: str = "google_drive",
    ) -> dict[str, Any]:
        if provider not in {"google_drive", "google_gmail", "google_photos"}:
            raise ValueError("unsupported personal memory provider")
        if not all((owner_email, account_id, remote_file_id, file_name, mime_type)):
            raise ValueError("source identity fields are required")
        encoded = extracted_text.encode("utf-8")
        if not encoded or len(encoded) > MAX_TEXT_BYTES:
            raise ValueError("extracted text must be between 1 byte and 2 MB")
        digest = hashlib.sha256(encoded).hexdigest()
        encrypted = self.cipher.encrypt(encoded)
        source_id = hashlib.sha256(
            f"{owner_email.casefold()}|{provider}|{account_id}|{remote_file_id}".encode()
        ).hexdigest()
        safe_meta = {
            "source": provider,
            "account_id": account_id,
            "remote_file_id": remote_file_id,
            "file_name": file_name[:255],
            "mime_type": mime_type[:200],
            "modified_time": modified_time,
            **(metadata or {}),
        }
        with self._db() as db:
            db.execute("""
                INSERT INTO personal_memory_sources
                    (source_id, owner_email, provider, account_id, remote_file_id,
                     file_name, mime_type, modified_time, content_sha256,
                     extracted_text_ciphertext, metadata_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'quarantined')
                ON CONFLICT(owner_email, provider, account_id, remote_file_id)
                DO UPDATE SET
                    file_name=excluded.file_name,
                    mime_type=excluded.mime_type,
                    modified_time=excluded.modified_time,
                    content_sha256=excluded.content_sha256,
                    extracted_text_ciphertext=excluded.extracted_text_ciphertext,
                    metadata_json=excluded.metadata_json,
                    status='quarantined',
                    imported_at=CURRENT_TIMESTAMP
            """, (
                source_id, owner_email.casefold(), provider, account_id, remote_file_id,
                file_name[:255], mime_type[:200], modified_time, digest,
                encrypted, json.dumps(safe_meta, ensure_ascii=False, sort_keys=True),
            ))
        return {
            "source_id": source_id, "content_sha256": digest,
            "status": "quarantined", "requires_owner_review": True,
        }

    def list_sources(self, owner_email: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        with self._db() as db:
            rows = db.execute("""
                SELECT source_id, provider, account_id, file_name, mime_type,
                       modified_time, content_sha256, status, imported_at
                FROM personal_memory_sources
                WHERE owner_email=? ORDER BY imported_at DESC LIMIT ?
            """, (owner_email.casefold(), limit)).fetchall()
        return [dict(row) for row in rows]

    def read_source(self, owner_email: str, source_id: str) -> dict[str, Any] | None:
        with self._db() as db:
            row = db.execute("""
                SELECT * FROM personal_memory_sources
                WHERE owner_email=? AND source_id=?
            """, (owner_email.casefold(), source_id)).fetchone()
        if row is None:
            return None
        try:
            text = self.cipher.decrypt(bytes(row["extracted_text_ciphertext"])).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError("Personal memory source failed integrity/decryption check") from exc
        return {
            "source_id": row["source_id"], "file_name": row["file_name"],
            "mime_type": row["mime_type"], "content_sha256": row["content_sha256"],
            "status": row["status"], "metadata": json.loads(row["metadata_json"]),
            "text": text,
        }
