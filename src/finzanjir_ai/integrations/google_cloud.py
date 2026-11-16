"""Single-owner, multi-account Google cloud gateway for FINZANJIR.

All provider tokens remain encrypted server-side. This module is inert unless the
owner identity, OAuth client, persistent state path, session secret and token key
are configured. It never exposes tokens to the browser.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/api/google", tags=["google-cloud"])
MAX_GOOGLE_ACCOUNTS = 100
SESSION_COOKIE = "finzanjir_owner_session"
IDENTITY_SCOPES = ("openid", "email", "profile")
SERVICE_SCOPES = {
    "drive": ("https://www.googleapis.com/auth/drive.readonly",),
    "gmail": ("https://www.googleapis.com/auth/gmail.readonly",),
}
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_TOKEN_INFO = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_REVOKE = "https://oauth2.googleapis.com/revoke"
GOOGLE_DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"


class GoogleConfigError(RuntimeError):
    pass


def _config() -> dict[str, str]:
    keys = (
        "FINZANJIR_GOOGLE_CLIENT_ID",
        "FINZANJIR_GOOGLE_CLIENT_SECRET",
        "FINZANJIR_GOOGLE_REDIRECT_URI",
        "FINZANJIR_OWNER_EMAIL",
        "FINZANJIR_SESSION_SECRET",
        "FINZANJIR_TOKEN_ENCRYPTION_KEY",
        "FINZANJIR_GOOGLE_STATE_DB_PATH",
    )
    values = {key: os.getenv(key, "").strip() for key in keys}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise GoogleConfigError("Google cloud gateway is not configured: " + ", ".join(missing))
    if len(values["FINZANJIR_SESSION_SECRET"].encode()) < 32:
        raise GoogleConfigError("Session secret must contain at least 32 bytes")
    try:
        Fernet(values["FINZANJIR_TOKEN_ENCRYPTION_KEY"].encode())
    except (ValueError, TypeError) as exc:
        raise GoogleConfigError("Token encryption key must be a valid Fernet key") from exc
    if not values["FINZANJIR_GOOGLE_REDIRECT_URI"].startswith("https://"):
        raise GoogleConfigError("Google OAuth redirect URI must use HTTPS")
    values["FINZANJIR_OWNER_EMAIL"] = values["FINZANJIR_OWNER_EMAIL"].casefold()
    return values


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class GoogleAccountStore:
    """Persistent owner-scoped registry and encrypted refresh-token vault."""

    def __init__(self, path: str, encryption_key: str):
        if not Path(path).is_absolute():
            raise ValueError("Google state database path must be absolute")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.cipher = Fernet(encryption_key.encode())
        with self._db() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS google_oauth_flows (
                    state_hash TEXT PRIMARY KEY, verifier TEXT NOT NULL,
                    purpose TEXT NOT NULL, owner_session_id TEXT,
                    created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS google_owner_sessions (
                    session_id TEXT PRIMARY KEY, owner_email TEXT NOT NULL,
                    created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS google_accounts (
                    account_id TEXT PRIMARY KEY, owner_email TEXT NOT NULL,
                    google_email TEXT NOT NULL, display_name TEXT NOT NULL,
                    refresh_token_ciphertext BLOB NOT NULL, scopes_json TEXT NOT NULL,
                    connected_at INTEGER NOT NULL, last_seen_at INTEGER,
                    status TEXT NOT NULL DEFAULT 'connected',
                    UNIQUE(owner_email, google_email)
                );
                CREATE TABLE IF NOT EXISTS google_cloud_audit (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_email TEXT NOT NULL, account_id TEXT,
                    action TEXT NOT NULL, occurred_at INTEGER NOT NULL,
                    detail_json TEXT NOT NULL
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

    def create_flow(self, state: str, verifier: str, purpose: str,
                    owner_session_id: str | None, now: int | None = None) -> None:
        stamp = int(time.time() if now is None else now)
        if purpose not in {"owner_login", "add_account"}:
            raise ValueError("unsupported OAuth flow purpose")
        with self._db() as db:
            db.execute("DELETE FROM google_oauth_flows WHERE expires_at < ?", (stamp,))
            db.execute(
                "INSERT INTO google_oauth_flows VALUES (?, ?, ?, ?, ?, ?)",
                (_digest(state), verifier, purpose, owner_session_id, stamp, stamp + 600),
            )

    def consume_flow(self, state: str, now: int | None = None) -> dict[str, Any] | None:
        stamp = int(time.time() if now is None else now)
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM google_oauth_flows WHERE state_hash=? AND expires_at>=?",
                (_digest(state), stamp),
            ).fetchone()
            db.execute("DELETE FROM google_oauth_flows WHERE state_hash=?", (_digest(state),))
        return dict(row) if row else None

    def create_session(self, owner_email: str, now: int | None = None) -> str:
        stamp = int(time.time() if now is None else now)
        session_id = secrets.token_urlsafe(32)
        with self._db() as db:
            db.execute(
                "INSERT INTO google_owner_sessions VALUES (?, ?, ?, ?, 0)",
                (session_id, owner_email.casefold(), stamp, stamp + 30 * 86400),
            )
        return session_id

    def valid_session(self, session_id: str, owner_email: str,
                      now: int | None = None) -> bool:
        stamp = int(time.time() if now is None else now)
        with self._db() as db:
            row = db.execute(
                """SELECT 1 FROM google_owner_sessions
                   WHERE session_id=? AND owner_email=? AND revoked=0 AND expires_at>=?""",
                (session_id, owner_email.casefold(), stamp),
            ).fetchone()
        return row is not None

    def revoke_session(self, session_id: str) -> None:
        with self._db() as db:
            db.execute("UPDATE google_owner_sessions SET revoked=1 WHERE session_id=?", (session_id,))

    def save_account(self, owner_email: str, google_email: str, display_name: str,
                     refresh_token: str, scopes: tuple[str, ...], now: int | None = None) -> dict[str, Any]:
        stamp = int(time.time() if now is None else now)
        owner_email, google_email = owner_email.casefold(), google_email.casefold()
        encrypted = self.cipher.encrypt(refresh_token.encode())
        account_id = hashlib.sha256((owner_email + ":" + google_email).encode()).hexdigest()[:32]
        with self._db() as db:
            existing = db.execute(
                "SELECT account_id FROM google_accounts WHERE owner_email=? AND google_email=?",
                (owner_email, google_email),
            ).fetchone()
            if not existing:
                count = db.execute(
                    "SELECT COUNT(*) FROM google_accounts WHERE owner_email=? AND status='connected'",
                    (owner_email,),
                ).fetchone()[0]
                if count >= MAX_GOOGLE_ACCOUNTS:
                    raise OverflowError("FINZANJIR supports at most 100 connected Google accounts")
            db.execute("""
                INSERT INTO google_accounts
                    (account_id, owner_email, google_email, display_name,
                     refresh_token_ciphertext, scopes_json, connected_at, last_seen_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'connected')
                ON CONFLICT(owner_email, google_email) DO UPDATE SET
                    display_name=excluded.display_name,
                    refresh_token_ciphertext=excluded.refresh_token_ciphertext,
                    scopes_json=excluded.scopes_json,
                    last_seen_at=excluded.last_seen_at,
                    status='connected'
            """, (account_id, owner_email, google_email, display_name[:200],
                  encrypted, json.dumps(sorted(set(scopes))), stamp, stamp))
            db.execute(
                "INSERT INTO google_cloud_audit(owner_email,account_id,action,occurred_at,detail_json) VALUES(?,?,?,?,?)",
                (owner_email, account_id, "account_connected", stamp,
                 json.dumps({"google_email": google_email, "scopes": sorted(set(scopes))})),
            )
        return {"account_id": account_id, "google_email": google_email,
                "display_name": display_name[:200], "scopes": sorted(set(scopes)),
                "status": "connected", "connected_at": stamp}

    def list_accounts(self, owner_email: str) -> list[dict[str, Any]]:
        with self._db() as db:
            rows = db.execute(
                """SELECT account_id, google_email, display_name, scopes_json,
                          connected_at, last_seen_at, status
                   FROM google_accounts WHERE owner_email=? ORDER BY connected_at, google_email""",
                (owner_email.casefold(),),
            ).fetchall()
        return [{
            "account_id": row["account_id"], "google_email": row["google_email"],
            "display_name": row["display_name"], "scopes": json.loads(row["scopes_json"]),
            "connected_at": row["connected_at"], "last_seen_at": row["last_seen_at"],
            "status": row["status"],
        } for row in rows]

    def account_secret(self, owner_email: str, account_id: str) -> tuple[str, tuple[str, ...]] | None:
        with self._db() as db:
            row = db.execute(
                """SELECT refresh_token_ciphertext, scopes_json FROM google_accounts
                   WHERE owner_email=? AND account_id=? AND status='connected'""",
                (owner_email.casefold(), account_id),
            ).fetchone()
        if not row:
            return None
        try:
            token = self.cipher.decrypt(bytes(row["refresh_token_ciphertext"])).decode()
        except (InvalidToken, ValueError):
            raise RuntimeError("Stored Google token could not be decrypted")
        return token, tuple(json.loads(row["scopes_json"]))

    def disconnect(self, owner_email: str, account_id: str) -> str | None:
        with self._db() as db:
            row = db.execute(
                """SELECT refresh_token_ciphertext FROM google_accounts
                   WHERE owner_email=? AND account_id=? AND status='connected'""",
                (owner_email.casefold(), account_id),
            ).fetchone()
            if not row:
                return None
            token = self.cipher.decrypt(bytes(row["refresh_token_ciphertext"])).decode()
            db.execute(
                """UPDATE google_accounts SET status='disconnected',
                   refresh_token_ciphertext=X'', last_seen_at=? WHERE owner_email=? AND account_id=?""",
                (int(time.time()), owner_email.casefold(), account_id),
            )
            db.execute(
                "INSERT INTO google_cloud_audit(owner_email,account_id,action,occurred_at,detail_json) VALUES(?,?,?,?,?)",
                (owner_email.casefold(), account_id, "account_disconnected",
                 int(time.time()), "{}"),
            )
        return token


def _store(config: dict[str, str] | None = None) -> GoogleAccountStore:
    cfg = config or _config()
    return GoogleAccountStore(
        cfg["FINZANJIR_GOOGLE_STATE_DB_PATH"],
        cfg["FINZANJIR_TOKEN_ENCRYPTION_KEY"],
    )


def _session_cookie(session_id: str, secret: str) -> str:
    signature = hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).hexdigest()
    return session_id + "." + signature


def _read_session(request: Request, cfg: dict[str, str], store: GoogleAccountStore) -> str:
    raw = request.cookies.get(SESSION_COOKIE, "")
    if "." not in raw:
        raise HTTPException(status_code=401, detail="FINZANJIR egasi Google orqali tizimga kirishi kerak.")
    session_id, signature = raw.rsplit(".", 1)
    expected = hmac.new(cfg["FINZANJIR_SESSION_SECRET"].encode(), session_id.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected) or not store.valid_session(
        session_id, cfg["FINZANJIR_OWNER_EMAIL"]
    ):
        raise HTTPException(status_code=401, detail="Sessiya yaroqsiz yoki muddati tugagan.")
    return session_id


def _authorization_url(cfg: dict[str, str], state: str, verifier: str,
                       scopes: tuple[str, ...]) -> str:
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    params = {
        "client_id": cfg["FINZANJIR_GOOGLE_CLIENT_ID"],
        "redirect_uri": cfg["FINZANJIR_GOOGLE_REDIRECT_URI"],
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "include_granted_scopes": "true",
    }
    if "drive.readonly" in scopes or "gmail.readonly" in scopes:
        params["prompt"] = "consent"
    return GOOGLE_AUTH + "?" + urlencode(params)


def _exchange_and_verify(code: str, verifier: str, cfg: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    with httpx.Client(timeout=httpx.Timeout(15, connect=5), follow_redirects=False) as client:
        token_response = client.post(GOOGLE_TOKEN, data={
            "code": code,
            "client_id": cfg["FINZANJIR_GOOGLE_CLIENT_ID"],
            "client_secret": cfg["FINZANJIR_GOOGLE_CLIENT_SECRET"],
            "redirect_uri": cfg["FINZANJIR_GOOGLE_REDIRECT_URI"],
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        })
        token_response.raise_for_status()
        tokens = token_response.json()
        id_token = tokens.get("id_token")
        if not id_token or not tokens.get("refresh_token"):
            raise ValueError("Google did not return required ID and refresh tokens")
        info_response = client.get(GOOGLE_TOKEN_INFO, params={"id_token": id_token})
        info_response.raise_for_status()
        identity = info_response.json()
    if identity.get("aud") != cfg["FINZANJIR_GOOGLE_CLIENT_ID"]:
        raise ValueError("Google ID token audience mismatch")
    if identity.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise ValueError("Google ID token issuer mismatch")
    if int(identity.get("exp", 0)) <= int(time.time()):
        raise ValueError("Google ID token expired")
    if identity.get("email_verified") not in {True, "true"}:
        raise ValueError("Google account email is not verified")
    return tokens, identity


@router.get("/oauth/start")
def google_oauth_start(
    request: Request,
    purpose: str = Query(default="owner_login", pattern="^(owner_login|add_account)$"),
    services: str = Query(default="drive", max_length=32),
):
    try:
        cfg = _config()
        store = _store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google ulanishi uchun xavfsiz server sozlamalari hali to‘liq emas.") from exc
    owner_session_id = None
    scopes = list(IDENTITY_SCOPES)
    if purpose == "add_account":
        owner_session_id = _read_session(request, cfg, store)
        selected = tuple(dict.fromkeys(item.strip().lower() for item in services.split(",") if item.strip()))
        if not selected or any(item not in SERVICE_SCOPES for item in selected):
            raise HTTPException(status_code=422, detail="Faqat drive va gmail xizmatlari tanlanishi mumkin.")
        for service in selected:
            scopes.extend(SERVICE_SCOPES[service])
    elif services != "drive":
        raise HTTPException(status_code=422, detail="Avval egasining Google akkaunti tasdiqlanishi kerak.")
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    store.create_flow(state, verifier, purpose, owner_session_id)
    return RedirectResponse(
        _authorization_url(cfg, state, verifier, tuple(scopes)),
        status_code=302,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/oauth/callback")
def google_oauth_callback(
    request: Request,
    response: Response,
    code: str = Query(min_length=1, max_length=4096),
    state: str = Query(min_length=20, max_length=256),
    error: str | None = Query(default=None, max_length=128),
):
    if error:
        raise HTTPException(status_code=400, detail="Google ruxsat berilmadi yoki bekor qilindi.")
    try:
        cfg = _config()
        store = _store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google ulanishi uchun xavfsiz server sozlamalari hali to‘liq emas.") from exc
    flow = store.consume_flow(state)
    if not flow:
        raise HTTPException(status_code=400, detail="OAuth holati topilmadi yoki muddati tugagan.")
    if flow["purpose"] == "add_account":
        if not flow["owner_session_id"] or not store.valid_session(
            flow["owner_session_id"], cfg["FINZANJIR_OWNER_EMAIL"]
        ):
            raise HTTPException(status_code=401, detail="Google akkaunt qo‘shish sessiyasi yaroqsiz.")
    try:
        tokens, identity = _exchange_and_verify(code, flow["verifier"], cfg)
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Google OAuth javobini xavfsiz tekshirish muvaffaqiyatsiz bo‘ldi.") from exc
    email = str(identity.get("email", "")).casefold()
    if email != cfg["FINZANJIR_OWNER_EMAIL"] and flow["purpose"] == "owner_login":
        raise HTTPException(status_code=403, detail="Bu Google akkaunt FINZANJIR egasi sifatida ruxsat etilmagan.")
    if flow["purpose"] == "owner_login":
        session_id = store.create_session(cfg["FINZANJIR_OWNER_EMAIL"])
        redirect = RedirectResponse("/?google=connected", status_code=303)
        redirect.set_cookie(
            SESSION_COOKIE, _session_cookie(session_id, cfg["FINZANJIR_SESSION_SECRET"]),
            max_age=30 * 86400, httponly=True, secure=True, samesite="lax", path="/",
        )
        return redirect
    scopes = tuple(str(tokens.get("scope", "")).split())
    if not scopes:
        raise HTTPException(status_code=502, detail="Google ruxsat bergan scope ro‘yxati bo‘sh.")
    try:
        account = store.save_account(
            cfg["FINZANJIR_OWNER_EMAIL"], email,
            str(identity.get("name") or email),
            str(tokens["refresh_token"]), scopes,
        )
    except OverflowError as exc:
        raise HTTPException(status_code=409, detail="100 ta Google akkaunt limiti to‘ldi.") from exc
    redirect = RedirectResponse("/?google_account=added", status_code=303)
    redirect.headers["Cache-Control"] = "no-store"
    return redirect


@router.get("/accounts")
def google_accounts(request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google xotira ombori sozlanmagan.") from exc
    _read_session(request, cfg, store)
    accounts = store.list_accounts(cfg["FINZANJIR_OWNER_EMAIL"])
    return {"count": len(accounts), "limit": MAX_GOOGLE_ACCOUNTS, "accounts": accounts}


@router.post("/accounts/{account_id}/disconnect")
def google_account_disconnect(account_id: str, request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google xotira ombori sozlanmagan.") from exc
    _read_session(request, cfg, store)
    token = store.disconnect(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Ulangan Google akkaunt topilmadi.")
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            client.post(GOOGLE_REVOKE, data={"token": token})
    except httpx.HTTPError:
        # Local token is already erased and the account is disconnected. The
        # user can also revoke access in their Google Account security page.
        pass
    return {"status": "disconnected", "account_id": account_id}


@router.get("/accounts/{account_id}/drive/files")
def google_drive_files(
    account_id: str,
    request: Request,
    page_token: str | None = Query(default=None, max_length=2048),
):
    try:
        cfg = _config()
        store = _store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google xotira ombori sozlanmagan.") from exc
    _read_session(request, cfg, store)
    secret = store.account_secret(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Google akkaunt ulanmagan.")
    refresh_token, scopes = secret
    if SERVICE_SCOPES["drive"][0] not in scopes:
        raise HTTPException(status_code=403, detail="Bu akkaunt uchun Google Drive ruxsati berilmagan.")
    try:
        with httpx.Client(timeout=httpx.Timeout(20, connect=5), follow_redirects=False) as client:
            token_response = client.post(GOOGLE_TOKEN, data={
                "client_id": cfg["FINZANJIR_GOOGLE_CLIENT_ID"],
                "client_secret": cfg["FINZANJIR_GOOGLE_CLIENT_SECRET"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            params = {
                "pageSize": 100,
                "orderBy": "modifiedTime desc",
                "q": "trashed = false",
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size,webViewLink,thumbnailLink)",
            }
            if page_token:
                params["pageToken"] = page_token
            files_response = client.get(
                GOOGLE_DRIVE_FILES, params=params,
                headers={"Authorization": "Bearer " + access_token},
            )
            files_response.raise_for_status()
            body = files_response.json()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Google Drive ma’lumotlarini olish muvaffaqiyatsiz bo‘ldi.") from exc
    return {
        "account_id": account_id,
        "files": body.get("files", []),
        "next_page_token": body.get("nextPageToken"),
        "read_only": True,
    }
