"""Encrypted, owner-scoped quarantine store for imported personal cloud content."""
from __future__ import annotations

import hashlib
import json
import os
import re
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
                CREATE TABLE IF NOT EXISTS google_photos_picker_sessions (
                    session_id TEXT PRIMARY KEY,
                    owner_email TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    picker_uri_ciphertext BLOB NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'created',
                    UNIQUE(owner_email, account_id, session_id)
                );
                CREATE TABLE IF NOT EXISTS personal_memory_audit (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_email TEXT NOT NULL,
                    action TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    remote_ref_hash TEXT NOT NULL,
                    content_sha256 TEXT,
                    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    detail_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_personal_memory_audit_owner_time
                ON personal_memory_audit(owner_email, occurred_at);
                CREATE TABLE IF NOT EXISTS personal_memory_media (
                    media_id TEXT PRIMARY KEY,
                    owner_email TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    remote_media_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    media_ciphertext BLOB NOT NULL,
                    metadata_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'quarantined',
                    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(owner_email, provider, account_id, remote_media_id)
                );
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
            db.execute("""
                INSERT INTO personal_memory_audit
                    (owner_email, action, provider, account_id, remote_ref_hash,
                     content_sha256, detail_json)
                VALUES (?, 'source_quarantined', ?, ?, ?, ?, ?)
            """, (
                owner_email.casefold(), provider, account_id,
                hashlib.sha256(remote_file_id.encode()).hexdigest(),
                digest, json.dumps({"file_name": file_name[:255], "mime_type": mime_type[:200]}),
            ))
        return {
            "source_id": source_id, "content_sha256": digest,
            "status": "quarantined", "requires_owner_review": True,
        }


    def save_picker_session(self, owner_email: str, account_id: str,
                            session_id: str, picker_uri: str) -> None:
        with self._db() as db:
            db.execute("""
                INSERT INTO google_photos_picker_sessions
                    (session_id, owner_email, account_id, picker_uri_ciphertext, status)
                VALUES (?, ?, ?, ?, 'created')
            """, (session_id, owner_email.casefold(), account_id,
                  self.cipher.encrypt(picker_uri.encode("utf-8"))))
            db.execute("""
                INSERT INTO personal_memory_audit
                    (owner_email, action, provider, account_id, remote_ref_hash, detail_json)
                VALUES (?, 'photos_picker_created', 'google_photos', ?, ?, '{}')
            """, (owner_email.casefold(), account_id,
                  hashlib.sha256(session_id.encode()).hexdigest()))

    def get_picker_session(self, owner_email: str, account_id: str,
                           session_id: str) -> dict[str, Any] | None:
        with self._db() as db:
            row = db.execute("""
                SELECT session_id, picker_uri_ciphertext, status, created_at
                FROM google_photos_picker_sessions
                WHERE owner_email=? AND account_id=? AND session_id=?
            """, (owner_email.casefold(), account_id, session_id)).fetchone()
        if row is None:
            return None
        result = dict(row)
        try:
            result["picker_uri"] = self.cipher.decrypt(bytes(result.pop("picker_uri_ciphertext"))).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError("Google Photos Picker session failed integrity/decryption check") from exc
        return result

    def set_picker_session_status(self, owner_email: str, account_id: str,
                                  session_id: str, status: str) -> bool:
        if status not in {"created", "ready", "deleted", "expired"}:
            raise ValueError("invalid picker session status")
        with self._db() as db:
            changed = db.execute("""
                UPDATE google_photos_picker_sessions SET status=?
                WHERE owner_email=? AND account_id=? AND session_id=?
            """, (status, owner_email.casefold(), account_id, session_id)).rowcount
        return changed == 1

    def quarantine_media(
        self, *, owner_email: str, account_id: str, remote_media_id: str,
        file_name: str, mime_type: str, media_type: str, content: bytes,
        metadata: dict[str, Any] | None = None, provider: str = "google_photos",
    ) -> dict[str, Any]:
        if provider not in {"google_photos", "google_drive"}:
            raise ValueError("unsupported personal media provider")
        if media_type not in {"photo", "video", "audio", "image", "document"}:
            raise ValueError("unsupported media type")
        if not content or len(content) > 100 * 1024 * 1024:
            raise ValueError("media must be between 1 byte and 100 MB")
        digest = hashlib.sha256(content).hexdigest()
        encrypted = self.cipher.encrypt(content)
        media_id = hashlib.sha256(
            f"{owner_email.casefold()}|{provider}|{account_id}|{remote_media_id}".encode()
        ).hexdigest()
        safe_meta = {
            "provider": provider, "account_id": account_id,
            "remote_media_id": remote_media_id, **(metadata or {}),
        }
        with self._db() as db:
            db.execute("""
                INSERT INTO personal_memory_media
                    (media_id, owner_email, provider, account_id, remote_media_id,
                     file_name, mime_type, media_type, content_sha256,
                     media_ciphertext, metadata_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'quarantined')
                ON CONFLICT(owner_email, provider, account_id, remote_media_id)
                DO UPDATE SET file_name=excluded.file_name,
                    mime_type=excluded.mime_type, media_type=excluded.media_type,
                    content_sha256=excluded.content_sha256,
                    media_ciphertext=excluded.media_ciphertext,
                    metadata_json=excluded.metadata_json, status='quarantined',
                    imported_at=CURRENT_TIMESTAMP
            """, (
                media_id, owner_email.casefold(), provider, account_id, remote_media_id,
                file_name[:255], mime_type[:200], media_type, digest, encrypted,
                json.dumps(safe_meta, ensure_ascii=False, sort_keys=True),
            ))
            db.execute("""
                INSERT INTO personal_memory_audit
                    (owner_email, action, provider, account_id, remote_ref_hash,
                     content_sha256, detail_json)
                VALUES (?, 'media_quarantined', ?, ?, ?, ?, ?)
            """, (
                owner_email.casefold(), provider, account_id,
                hashlib.sha256(remote_media_id.encode()).hexdigest(),
                digest, json.dumps({"file_name": file_name[:255], "mime_type": mime_type[:200], "media_type": media_type}),
            ))
        return {"media_id": media_id, "content_sha256": digest,
                "status": "quarantined", "requires_owner_review": True}

    def list_media(self, owner_email: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        with self._db() as db:
            rows = db.execute("""
                SELECT media_id, provider, account_id, file_name, mime_type,
                       media_type, content_sha256, status, imported_at
                FROM personal_memory_media WHERE owner_email=?
                ORDER BY imported_at DESC LIMIT ?
            """, (owner_email.casefold(), limit)).fetchall()
        return [dict(row) for row in rows]

    def search_sources(self, owner_email: str, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        cleaned = query.strip()
        if not cleaned or len(cleaned) > 256:
            raise ValueError("query must contain 1 to 256 characters")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        terms = list(dict.fromkeys(re.findall(r"[\w-]{2,}", cleaned.casefold())))
        if not terms:
            return []
        with self._db() as db:
            rows = db.execute("""
                SELECT source_id, file_name, mime_type, content_sha256,
                       extracted_text_ciphertext, metadata_json, status
                FROM personal_memory_sources
                WHERE owner_email=? AND status='quarantined'
                ORDER BY imported_at DESC LIMIT 200
            """, (owner_email.casefold(),)).fetchall()
        matches = []
        for row in rows:
            try:
                text = self.cipher.decrypt(bytes(row["extracted_text_ciphertext"])).decode("utf-8")
            except (InvalidToken, UnicodeDecodeError, ValueError):
                continue
            folded = text.casefold()
            score = sum(folded.count(term) for term in terms)
            if score <= 0:
                continue
            first = min((folded.find(term) for term in terms if folded.find(term) >= 0), default=0)
            start = max(0, first - 180)
            snippet = text[start:start + 500].replace("\n", " ")
            matches.append({
                "source_id": row["source_id"], "file_name": row["file_name"],
                "mime_type": row["mime_type"], "content_sha256": row["content_sha256"],
                "score": score, "snippet": snippet,
                "metadata": json.loads(row["metadata_json"]),
            })
        matches.sort(key=lambda item: (-item["score"], item["file_name"].casefold()))
        return matches[:limit]

    def read_media(self, owner_email: str, media_id: str) -> dict[str, Any] | None:
        with self._db() as db:
            row = db.execute("""
                SELECT * FROM personal_memory_media
                WHERE owner_email=? AND media_id=?
            """, (owner_email.casefold(), media_id)).fetchone()
        if row is None:
            return None
        try:
            content = self.cipher.decrypt(bytes(row["media_ciphertext"]))
        except (InvalidToken, ValueError) as exc:
            raise RuntimeError("Personal media failed integrity/decryption check") from exc
        return {
            "media_id": row["media_id"], "file_name": row["file_name"],
            "mime_type": row["mime_type"], "media_type": row["media_type"],
            "content_sha256": row["content_sha256"], "status": row["status"],
            "metadata": json.loads(row["metadata_json"]), "content": content,
        }

    def audit_events(self, owner_email: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        with self._db() as db:
            rows = db.execute("""
                SELECT event_id, action, provider, account_id, remote_ref_hash,
                       content_sha256, occurred_at, detail_json
                FROM personal_memory_audit
                WHERE owner_email=? ORDER BY event_id DESC LIMIT ?
            """, (owner_email.casefold(), limit)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["detail"] = json.loads(item.pop("detail_json"))
            except (TypeError, ValueError):
                item["detail"] = {}
            result.append(item)
        return result

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
