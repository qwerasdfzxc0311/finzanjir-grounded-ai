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
from urllib.parse import urlencode, quote, urlsplit

from .drive_extract import MAX_DOWNLOAD_BYTES, UnsupportedDriveFormat, extract_drive_text
from .personal_memory import PersonalMemoryStore
from .gmail_extract import extract_gmail_message
from .media_validation import UnsupportedMedia, validate_media_content

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter(prefix="/api/google", tags=["google-cloud"])
MAX_GOOGLE_ACCOUNTS = 100
SESSION_COOKIE = "finzanjir_owner_session"
IDENTITY_SCOPES = ("openid", "email", "profile")
SERVICE_SCOPES = {
    "drive": ("https://www.googleapis.com/auth/drive.readonly",),
    "gmail": ("https://www.googleapis.com/auth/gmail.readonly",),
    "photos": ("https://www.googleapis.com/auth/photospicker.mediaitems.readonly",),
}
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_TOKEN_INFO = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_REVOKE = "https://oauth2.googleapis.com/revoke"
GOOGLE_DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
GOOGLE_GMAIL_MESSAGES = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GOOGLE_PHOTOS_SESSIONS = "https://photospicker.googleapis.com/v1/sessions"
GOOGLE_PHOTOS_MEDIA = "https://photospicker.googleapis.com/v1/mediaItems"
GOOGLE_DOC_MIMES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.presentation": "text/plain",
}


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
        "FINZANJIR_PERSONAL_MEMORY_DB_PATH",
        "FINZANJIR_FRONTEND_URL",
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
    frontend = urlsplit(values["FINZANJIR_FRONTEND_URL"])
    if (frontend.scheme != "https" or not frontend.netloc or frontend.path not in {"", "/"}
            or frontend.query or frontend.fragment or frontend.username or frontend.password):
        raise GoogleConfigError("Frontend URL must be an HTTPS origin without path or query")
    allowed_origins = {
        item.strip().rstrip("/")
        for item in os.getenv("FINZANJIR_ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    }
    if values["FINZANJIR_FRONTEND_URL"].rstrip("/") not in allowed_origins:
        raise GoogleConfigError("Frontend URL must be included in FINZANJIR_ALLOWED_ORIGINS")
    values["FINZANJIR_FRONTEND_URL"] = values["FINZANJIR_FRONTEND_URL"].rstrip("/")
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
                    state_hash TEXT PRIMARY KEY, verifier TEXT NOT NULL, nonce TEXT NOT NULL,
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

    def create_flow(self, state: str, verifier: str, nonce: str, purpose: str,
                    owner_session_id: str | None, now: int | None = None) -> None:
        stamp = int(time.time() if now is None else now)
        if purpose not in {"owner_login", "add_account"}:
            raise ValueError("unsupported OAuth flow purpose")
        with self._db() as db:
            db.execute("DELETE FROM google_oauth_flows WHERE expires_at < ?", (stamp,))
            db.execute(
                "INSERT INTO google_oauth_flows VALUES (?, ?, ?, ?, ?, ?, ?)",
                (_digest(state), verifier, nonce, purpose, owner_session_id, stamp, stamp + 600),
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
                "SELECT account_id, scopes_json FROM google_accounts WHERE owner_email=? AND google_email=?",
                (owner_email, google_email),
            ).fetchone()
            combined_scopes = set(scopes)
            if existing:
                account_id = existing["account_id"]
                combined_scopes.update(json.loads(existing["scopes_json"]))
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
                  encrypted, json.dumps(sorted(combined_scopes)), stamp, stamp))
            db.execute(
                "INSERT INTO google_cloud_audit(owner_email,account_id,action,occurred_at,detail_json) VALUES(?,?,?,?,?)",
                (owner_email, account_id, "account_connected", stamp,
                 json.dumps({"google_email": google_email, "scopes": sorted(combined_scopes)})),
            )
        return {"account_id": account_id, "google_email": google_email,
                "display_name": display_name[:200], "scopes": sorted(combined_scopes),
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
                       nonce: str, scopes: tuple[str, ...]) -> str:
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    params = {
        "client_id": cfg["FINZANJIR_GOOGLE_CLIENT_ID"],
        "redirect_uri": cfg["FINZANJIR_GOOGLE_REDIRECT_URI"],
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "include_granted_scopes": "true",
    }
    if len(scopes) > len(IDENTITY_SCOPES):
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
        if not id_token:
            raise ValueError("Google did not return a required ID token")
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
            raise HTTPException(status_code=422, detail="Hozircha Google Drive, Gmail va Google Photos xizmatlari tanlanishi mumkin.")
        for service in selected:
            scopes.extend(SERVICE_SCOPES[service])
    elif services != "drive":
        raise HTTPException(status_code=422, detail="Avval egasining Google akkaunti tasdiqlanishi kerak.")
    state, verifier, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    store.create_flow(state, verifier, nonce, purpose, owner_session_id)
    return RedirectResponse(
        _authorization_url(cfg, state, verifier, nonce, tuple(scopes)),
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
    if identity.get("nonce") != flow["nonce"]:
        raise HTTPException(status_code=401, detail="Google ID token nonce mos kelmadi.")
    if email != cfg["FINZANJIR_OWNER_EMAIL"] and flow["purpose"] == "owner_login":
        raise HTTPException(status_code=403, detail="Bu Google akkaunt FINZANJIR egasi sifatida ruxsat etilmagan.")
    if flow["purpose"] == "owner_login":
        session_id = store.create_session(cfg["FINZANJIR_OWNER_EMAIL"])
        redirect = RedirectResponse(cfg["FINZANJIR_FRONTEND_URL"] + "/?google=connected", status_code=303)
        redirect.set_cookie(
            SESSION_COOKIE, _session_cookie(session_id, cfg["FINZANJIR_SESSION_SECRET"]),
            max_age=30 * 86400, httponly=True, secure=True, samesite="lax", path="/",
        )
        return redirect
    if not tokens.get("refresh_token"):
        raise HTTPException(status_code=502, detail="Google uzoq muddatli ruxsat tokenini bermadi; qayta rozilik berish kerak.")
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
    redirect = RedirectResponse(cfg["FINZANJIR_FRONTEND_URL"] + "/?google_account=added", status_code=303)
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
    connected_count = sum(1 for account in accounts if account["status"] == "connected")
    return {"count": connected_count, "limit": MAX_GOOGLE_ACCOUNTS, "accounts": accounts}



def _require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin", "").rstrip("/")
    allowed = {f"{request.url.scheme}://{request.url.netloc}".rstrip("/")}
    configured = os.getenv("FINZANJIR_ALLOWED_ORIGINS", "")
    allowed.update(item.strip().rstrip("/") for item in configured.split(",") if item.strip())
    if not origin or origin not in allowed:
        raise HTTPException(status_code=403, detail="So‘rov manbasi tasdiqlanmadi.")


@router.post("/logout")
def google_owner_logout(request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google xotira ombori sozlanmagan.") from exc
    _require_same_origin(request)
    session_id = _read_session(request, cfg, store)
    store.revoke_session(session_id)
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


@router.post("/accounts/{account_id}/disconnect")
def google_account_disconnect(account_id: str, request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google xotira ombori sozlanmagan.") from exc
    _require_same_origin(request)
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
                "q": "trashed = false and mimeType != 'application/vnd.google-apps.folder'",
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

def _personal_memory_store(cfg: dict[str, str]) -> PersonalMemoryStore:
    return PersonalMemoryStore(
        cfg["FINZANJIR_PERSONAL_MEMORY_DB_PATH"],
        cfg["FINZANJIR_TOKEN_ENCRYPTION_KEY"],
    )


def _google_access_token(cfg: dict[str, str], refresh_token: str) -> str:
    with httpx.Client(timeout=httpx.Timeout(20, connect=5), follow_redirects=False) as client:
        response = client.post(GOOGLE_TOKEN, data={
            "client_id": cfg["FINZANJIR_GOOGLE_CLIENT_ID"],
            "client_secret": cfg["FINZANJIR_GOOGLE_CLIENT_SECRET"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        response.raise_for_status()
        token = response.json().get("access_token")
    if not token:
        raise ValueError("Google did not return an access token")
    return token


def _download_drive_file(access_token: str, file_id: str, mime_type: str, *, max_bytes: int = MAX_DOWNLOAD_BYTES) -> bytes:
    encoded_id = quote(file_id, safe="")
    headers = {"Authorization": "Bearer " + access_token}
    if mime_type in GOOGLE_DOC_MIMES:
        url = "https://www.googleapis.com/drive/v3/files/" + encoded_id + "/export"
        params = {"mimeType": GOOGLE_DOC_MIMES[mime_type]}
    else:
        url = "https://www.googleapis.com/drive/v3/files/" + encoded_id
        params = {"alt": "media"}
    chunks: list[bytes] = []
    total = 0
    with httpx.Client(timeout=httpx.Timeout(30, connect=5), follow_redirects=False) as client:
        with client.stream("GET", url, params=params, headers=headers) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > max_bytes:
                raise ValueError("Google Drive file exceeds the configured import size limit")
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("Google Drive file exceeds the 10 MB import limit")
                chunks.append(chunk)
    return b"".join(chunks)


@router.post("/accounts/{account_id}/drive/files/{file_id}/import")
def google_drive_import_file(account_id: str, file_id: str, request: Request):
    """Import one owner-selected Drive file into encrypted quarantine, never auto-KB."""
    try:
        cfg = _config()
        store = _store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google xotira ombori sozlanmagan.") from exc
    _require_same_origin(request)
    _read_session(request, cfg, store)
    secret = store.account_secret(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Google akkaunt ulanmagan.")
    refresh_token, scopes = secret
    if SERVICE_SCOPES["drive"][0] not in scopes:
        raise HTTPException(status_code=403, detail="Bu akkauntda Google Drive o‘qish ruxsati yo‘q.")
    try:
        access_token = _google_access_token(cfg, refresh_token)
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            metadata_response = client.get(
                GOOGLE_DRIVE_FILES + "/" + quote(file_id, safe=""),
                params={"fields": "id,name,mimeType,modifiedTime,size,trashed"},
                headers={"Authorization": "Bearer " + access_token},
            )
            metadata_response.raise_for_status()
            metadata = metadata_response.json()
        if metadata.get("trashed") or metadata.get("id") != file_id:
            raise HTTPException(status_code=404, detail="Drive fayli mavjud emas yoki savatda.")
        if int(metadata.get("size") or 0) > MAX_DOWNLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Fayl 10 MB import limitidan katta.")
        mime_type = str(metadata.get("mimeType") or "")
        supported = set(GOOGLE_DOC_MIMES) | {
            "text/plain", "text/markdown", "text/csv", "application/json",
            "application/xml", "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        if mime_type not in supported:
            raise HTTPException(status_code=415, detail="Bu fayl turi hozircha matnga aylantirish uchun qo‘llanmaydi.")
        content = _download_drive_file(access_token, file_id, mime_type)
        extraction_mime = GOOGLE_DOC_MIMES.get(mime_type, mime_type)
        extracted = extract_drive_text(str(metadata.get("name") or file_id), extraction_mime, content)
        memory = _personal_memory_store(cfg)
        result = memory.quarantine(
            owner_email=cfg["FINZANJIR_OWNER_EMAIL"],
            account_id=account_id,
            remote_file_id=file_id,
            file_name=str(metadata.get("name") or file_id),
            mime_type=mime_type,
            modified_time=metadata.get("modifiedTime"),
            extracted_text=extracted["text"],
            metadata={
                "extractor": extracted["extractor"],
                "source_link": "https://drive.google.com/open?id=" + quote(file_id, safe=""),
            },
        )
    except HTTPException:
        raise
    except UnsupportedDriveFormat as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except (httpx.HTTPError, KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail="Drive faylini xavfsiz import qilish bajarilmadi: " + type(exc).__name__) from exc
    return {
        **result, "file_name": str(metadata.get("name") or file_id),
        "mime_type": mime_type, "extracted_characters": len(extracted["text"]),
        "message": "Fayl shifrlangan shaxsiy xotira karantiniga saqlandi; asosiy bilim bazasiga avtomatik qo‘shilmadi.",
    }



@router.post("/accounts/{account_id}/drive/files/{file_id}/import-media")
def google_drive_import_media(account_id: str, file_id: str, request: Request):
    """Import a selected image/audio/video file into encrypted private media storage."""
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google media xotira ombori sozlanmagan.") from exc
    _require_same_origin(request)
    _read_session(request, cfg, store)
    secret = store.account_secret(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Google akkaunt ulanmagan.")
    if SERVICE_SCOPES["drive"][0] not in secret[1]:
        raise HTTPException(status_code=403, detail="Bu akkauntda Google Drive o‘qish ruxsati yo‘q.")
    try:
        access_token = _google_access_token(cfg, secret[0])
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get(
                GOOGLE_DRIVE_FILES + "/" + quote(file_id, safe=""),
                params={"fields": "id,name,mimeType,modifiedTime,size,trashed"},
                headers={"Authorization": "Bearer " + access_token},
            )
            response.raise_for_status()
            metadata = response.json()
        if metadata.get("trashed") or metadata.get("id") != file_id:
            raise HTTPException(status_code=404, detail="Drive media fayli topilmadi yoki savatda.")
        mime_type = str(metadata.get("mimeType") or "")
        if not (mime_type.startswith("image/") or mime_type.startswith("audio/") or mime_type.startswith("video/")):
            raise HTTPException(status_code=415, detail="Faqat rasm, audio va video fayllar qabul qilinadi.")
        max_bytes = 100 * 1024 * 1024
        if int(metadata.get("size") or 0) > max_bytes:
            raise HTTPException(status_code=413, detail="Media fayl 100 MB import limitidan katta.")
        content = _download_drive_file(access_token, file_id, mime_type, max_bytes=max_bytes)
        validation = validate_media_content(mime_type, content)
        result = memory.quarantine_media(
            owner_email=cfg["FINZANJIR_OWNER_EMAIL"],
            account_id=account_id, remote_media_id=file_id,
            file_name=str(metadata.get("name") or file_id),
            mime_type=mime_type, media_type=validation["media_type"],
            content=content, provider="google_drive",
            metadata={
                "modified_time": metadata.get("modifiedTime"),
                "source_link": "https://drive.google.com/open?id=" + quote(file_id, safe=""),
                "validation": validation,
            },
        )
    except HTTPException:
        raise
    except UnsupportedMedia as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except (httpx.HTTPError, KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail="Drive media faylini xavfsiz import qilish bajarilmadi: " + type(exc).__name__) from exc
    return {
        **result, "file_name": str(metadata.get("name") or file_id),
        "mime_type": mime_type, "bytes_stored": len(content),
        "message": "Media shifrlangan shaxsiy xotira karantiniga saqlandi; hali AI tomonidan tahlil qilinmadi.",
    }


@router.get("/memory/sources")
def google_personal_memory_sources(request: Request, limit: int = Query(default=100, ge=1, le=200)):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Shaxsiy xotira ombori sozlanmagan.") from exc
    _read_session(request, cfg, store)
    return {"sources": memory.list_sources(cfg["FINZANJIR_OWNER_EMAIL"], limit=limit)}


@router.get("/memory/sources/{source_id}")
def google_personal_memory_read(source_id: str, request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Shaxsiy xotira ombori sozlanmagan.") from exc
    _read_session(request, cfg, store)
    source = memory.read_source(cfg["FINZANJIR_OWNER_EMAIL"], source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Shaxsiy xotira manbasi topilmadi.")
    return source


@router.get("/accounts/{account_id}/gmail/messages")
def google_gmail_messages(
    account_id: str,
    request: Request,
    q: str = Query(default="in:anywhere", max_length=256),
    page_token: str | None = Query(default=None, max_length=2048),
    max_results: int = Query(default=25, ge=1, le=50),
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
    if SERVICE_SCOPES["gmail"][0] not in scopes:
        raise HTTPException(status_code=403, detail="Bu akkaunt uchun Gmail o‘qish ruxsati berilmagan.")
    try:
        access_token = _google_access_token(cfg, refresh_token)
        params = {"q": q, "maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get(
                GOOGLE_GMAIL_MESSAGES, params=params,
                headers={"Authorization": "Bearer " + access_token},
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Gmail xabarlar ro‘yxatini olish muvaffaqiyatsiz bo‘ldi.") from exc
    return {
        "account_id": account_id,
        "messages": body.get("messages", []),
        "next_page_token": body.get("nextPageToken"),
        "result_size_estimate": body.get("resultSizeEstimate"),
        "read_only": True,
    }


@router.post("/accounts/{account_id}/gmail/messages/{message_id}/import")
def google_gmail_import_message(account_id: str, message_id: str, request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google xotira ombori sozlanmagan.") from exc
    _require_same_origin(request)
    _read_session(request, cfg, store)
    secret = store.account_secret(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Google akkaunt ulanmagan.")
    refresh_token, scopes = secret
    if SERVICE_SCOPES["gmail"][0] not in scopes:
        raise HTTPException(status_code=403, detail="Bu akkaunt uchun Gmail o‘qish ruxsati berilmagan.")
    try:
        access_token = _google_access_token(cfg, refresh_token)
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            response = client.get(
                GOOGLE_GMAIL_MESSAGES + "/" + quote(message_id, safe=""),
                params={"format": "full"},
                headers={"Authorization": "Bearer " + access_token},
            )
            response.raise_for_status()
            message = response.json()
        extracted = extract_gmail_message(message)
        headers = extracted["headers"]
        memory = _personal_memory_store(cfg)
        result = memory.quarantine(
            owner_email=cfg["FINZANJIR_OWNER_EMAIL"],
            account_id=account_id,
            remote_file_id=message_id,
            file_name=(headers.get("subject") or message_id)[:255],
            mime_type="message/rfc822",
            modified_time=str(message.get("internalDate") or ""),
            extracted_text=extracted["text"],
            provider="google_gmail",
            metadata={
                "extractor": extracted["extractor"],
                "message_id": message_id,
                "thread_id": message.get("threadId"),
                "headers": headers,
                "source_link": "https://mail.google.com/mail/u/0/#all/" + quote(message_id, safe=""),
            },
        )
    except HTTPException:
        raise
    except (httpx.HTTPError, KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail="Gmail xabarini xavfsiz import qilish bajarilmadi: " + type(exc).__name__) from exc
    return {
        **result, "subject": headers.get("subject", ""),
        "extractor": extracted["extractor"],
        "message": "Xat shifrlangan shaxsiy xotira karantiniga saqlandi; avtomatik ravishda bilim bazasiga yoki treningga qo‘shilmadi.",
    }



def _picker_session_for_owner(
    memory: PersonalMemoryStore, owner_email: str, account_id: str, session_id: str
) -> dict[str, Any]:
    session = memory.get_picker_session(owner_email, account_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Google Photos tanlash sessiyasi topilmadi.")
    return session


@router.post("/accounts/{account_id}/photos/sessions")
def google_photos_create_session(account_id: str, request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google Photos xotira ombori sozlanmagan.") from exc
    _require_same_origin(request)
    _read_session(request, cfg, store)
    secret = store.account_secret(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Google akkaunt ulanmagan.")
    refresh_token, scopes = secret
    if SERVICE_SCOPES["photos"][0] not in scopes:
        raise HTTPException(status_code=403, detail="Bu akkauntga Google Photos ruxsati berilmagan.")
    try:
        access_token = _google_access_token(cfg, refresh_token)
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.post(
                GOOGLE_PHOTOS_SESSIONS,
                headers={"Authorization": "Bearer " + access_token},
                json={},
            )
            response.raise_for_status()
            body = response.json()
        session_id = str(body.get("id") or "").split("/")[-1]
        picker_uri = str(body.get("pickerUri") or "")
        if not session_id or not picker_uri.startswith("https://"):
            raise ValueError("Google Photos Picker returned an invalid session")
        memory.save_picker_session(
            cfg["FINZANJIR_OWNER_EMAIL"], account_id, session_id, picker_uri
        )
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Google Photos tanlash sessiyasini yaratib bo‘lmadi.") from exc
    return {
        "session_id": session_id,
        "picker_uri": picker_uri,
        "status": "created",
        "instruction": "Google Photos rasm yoki videolarini o‘zingiz tanlang. Tanlov tugagach, FINZANJIR sessiya holatini tekshiradi.",
    }


@router.get("/accounts/{account_id}/photos/sessions/{session_id}")
def google_photos_get_session(account_id: str, session_id: str, request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google Photos xotira ombori sozlanmagan.") from exc
    _read_session(request, cfg, store)
    _picker_session_for_owner(memory, cfg["FINZANJIR_OWNER_EMAIL"], account_id, session_id)
    secret = store.account_secret(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Google akkaunt ulanmagan.")
    if SERVICE_SCOPES["photos"][0] not in secret[1]:
        raise HTTPException(status_code=403, detail="Google Photos ruxsati yo‘q.")
    try:
        access_token = _google_access_token(cfg, secret[0])
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get(
                GOOGLE_PHOTOS_SESSIONS + "/" + quote(session_id, safe=""),
                headers={"Authorization": "Bearer " + access_token},
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Google Photos sessiyasini tekshirish muvaffaqiyatsiz.") from exc
    ready = bool(body.get("mediaItemsSet"))
    memory.set_picker_session_status(
        cfg["FINZANJIR_OWNER_EMAIL"], account_id, session_id,
        "ready" if ready else "created",
    )
    return {
        "session_id": session_id, "media_items_set": ready,
        "polling_config": body.get("pollingConfig", {}),
        "status": "ready" if ready else "waiting_for_user_selection",
    }


@router.get("/accounts/{account_id}/photos/sessions/{session_id}/media-items")
def google_photos_list_selected(account_id: str, session_id: str, request: Request,
                                page_token: str | None = Query(default=None, max_length=2048),
                                page_size: int = Query(default=50, ge=1, le=100)):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google Photos xotira ombori sozlanmagan.") from exc
    _read_session(request, cfg, store)
    local_session = _picker_session_for_owner(memory, cfg["FINZANJIR_OWNER_EMAIL"], account_id, session_id)
    if local_session["status"] != "ready":
        raise HTTPException(status_code=409, detail="Avval Google Photos tanlovi tugaganini tekshiring.")
    secret = store.account_secret(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if not secret or SERVICE_SCOPES["photos"][0] not in secret[1]:
        raise HTTPException(status_code=403, detail="Google Photos ruxsati yo‘q.")
    try:
        access_token = _google_access_token(cfg, secret[0])
        params = {"sessionId": session_id, "pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get(
                GOOGLE_PHOTOS_MEDIA, params=params,
                headers={"Authorization": "Bearer " + access_token},
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Tanlangan Google Photos media ro‘yxatini olish muvaffaqiyatsiz.") from exc
    items = []
    for item in body.get("mediaItems", []):
        media_file = item.get("mediaFile") or {}
        metadata = media_file.get("mediaFileMetadata") or {}
        items.append({
            "id": item.get("id"),
            "type": item.get("type"),
            "create_time": item.get("createTime"),
            "filename": media_file.get("filename"),
            "mime_type": media_file.get("mimeType"),
            "metadata": metadata,
        })
    return {"session_id": session_id, "media_items": items,
            "next_page_token": body.get("nextPageToken")}


@router.post("/accounts/{account_id}/photos/sessions/{session_id}/media-items/{media_id}/import")
def google_photos_import_selected_media(account_id: str, session_id: str,
                                        media_id: str, request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google Photos xotira ombori sozlanmagan.") from exc
    _require_same_origin(request)
    _read_session(request, cfg, store)
    local_session = _picker_session_for_owner(memory, cfg["FINZANJIR_OWNER_EMAIL"], account_id, session_id)
    if local_session["status"] != "ready":
        raise HTTPException(status_code=409, detail="Google Photos tanlovi hali tugamagan.")
    secret = store.account_secret(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if not secret or SERVICE_SCOPES["photos"][0] not in secret[1]:
        raise HTTPException(status_code=403, detail="Google Photos ruxsati yo‘q.")
    try:
        access_token = _google_access_token(cfg, secret[0])
        page_token = None
        selected = None
        for _ in range(10):
            params = {"sessionId": session_id, "pageSize": 100}
            if page_token:
                params["pageToken"] = page_token
            with httpx.Client(timeout=20, follow_redirects=False) as client:
                response = client.get(
                    GOOGLE_PHOTOS_MEDIA, params=params,
                    headers={"Authorization": "Bearer " + access_token},
                )
                response.raise_for_status()
                body = response.json()
            selected = next((item for item in body.get("mediaItems", [])
                             if item.get("id") == media_id), None)
            if selected:
                break
            page_token = body.get("nextPageToken")
            if not page_token:
                break
        if not selected:
            raise HTTPException(status_code=404, detail="Bu media aynan shu Google Photos sessiyasida tanlanmagan.")
        if selected.get("type") not in {"PHOTO", "VIDEO"}:
            raise HTTPException(status_code=415, detail="Google Photos media turi qo‘llab-quvvatlanmaydi.")
        media_file = selected.get("mediaFile") or {}
        base_url = str(media_file.get("baseUrl") or "")
        parsed = urlsplit(base_url)
        if (parsed.scheme != "https" or not parsed.hostname
                or not parsed.hostname.endswith(".googleusercontent.com")
                or parsed.username or parsed.password or parsed.port not in (None, 443)):
            raise HTTPException(status_code=502, detail="Google Photos media manzili xavfsiz emas.")
        mime_type = str(media_file.get("mimeType") or "")
        media_kind = "photo" if selected.get("type") == "PHOTO" else "video"
        suffix = "=d" if media_kind == "photo" else "=dv"
        chunks = []
        total = 0
        with httpx.Client(timeout=httpx.Timeout(90, connect=10), follow_redirects=False) as client:
            with client.stream("GET", base_url + suffix,
                               headers={"Authorization": "Bearer " + access_token}) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > 100 * 1024 * 1024:
                        raise ValueError("Google Photos media exceeds 100 MB")
                    chunks.append(chunk)
        content = b"".join(chunks)
        validation = validate_media_content(mime_type, content)
        result = memory.quarantine_media(
            owner_email=cfg["FINZANJIR_OWNER_EMAIL"], account_id=account_id,
            remote_media_id=media_id,
            file_name=str(media_file.get("filename") or media_id),
            mime_type=mime_type, media_type=media_kind, content=content,
            metadata={
                "validation": validation,
                "picker_session_id": session_id,
                "create_time": selected.get("createTime"),
                "media_file_metadata": media_file.get("mediaFileMetadata", {}),
                "google_photos_type": selected.get("type"),
            },
        )
    except HTTPException:
        raise
    except UnsupportedMedia as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except (httpx.HTTPError, KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail="Tanlangan media faylni shifrlab saqlash muvaffaqiyatsiz: " + type(exc).__name__) from exc
    return {
        **result, "file_name": str(media_file.get("filename") or media_id),
        "mime_type": mime_type, "bytes_stored": len(content),
        "message": "Media shifrlangan shaxsiy xotira karantiniga saqlandi; hali AI tomonidan tahlil qilinmadi.",
    }


@router.delete("/accounts/{account_id}/photos/sessions/{session_id}")
def google_photos_delete_session(account_id: str, session_id: str, request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Google Photos xotira ombori sozlanmagan.") from exc
    _require_same_origin(request)
    _read_session(request, cfg, store)
    _picker_session_for_owner(memory, cfg["FINZANJIR_OWNER_EMAIL"], account_id, session_id)
    secret = store.account_secret(cfg["FINZANJIR_OWNER_EMAIL"], account_id)
    if not secret or SERVICE_SCOPES["photos"][0] not in secret[1]:
        raise HTTPException(status_code=403, detail="Google Photos ruxsati yo‘q.")
    try:
        access_token = _google_access_token(cfg, secret[0])
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.delete(
                GOOGLE_PHOTOS_SESSIONS + "/" + quote(session_id, safe=""),
                headers={"Authorization": "Bearer " + access_token},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Google Photos sessiyasini yopish muvaffaqiyatsiz.") from exc
    memory.set_picker_session_status(
        cfg["FINZANJIR_OWNER_EMAIL"], account_id, session_id, "deleted"
    )
    return {"status": "deleted", "session_id": session_id}


@router.get("/memory/search")
def google_personal_memory_search(
    request: Request,
    q: str = Query(min_length=1, max_length=256),
    limit: int = Query(default=10, ge=1, le=20),
):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Shaxsiy xotira ombori sozlanmagan.") from exc
    _read_session(request, cfg, store)
    try:
        results = memory.search_sources(cfg["FINZANJIR_OWNER_EMAIL"], q, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "query": q,
        "results": results,
        "search_mode": "local_decrypt_and_match",
        "external_search": False,
        "knowledge_status": "quarantined_sources_only",
    }


@router.get("/memory/media")
def google_personal_memory_media_list(
    request: Request, limit: int = Query(default=100, ge=1, le=200)
):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Shaxsiy xotira ombori sozlanmagan.") from exc
    _read_session(request, cfg, store)
    return {"media": memory.list_media(cfg["FINZANJIR_OWNER_EMAIL"], limit=limit)}


@router.get("/status")
def google_gateway_status(request: Request):
    try:
        cfg = _config()
        store = _store(cfg)
        memory = _personal_memory_store(cfg)
    except (GoogleConfigError, OSError, ValueError):
        return {"configured": False, "authenticated": False, "message": "Google ulanishi serverda hali sozlanmagan."}
    try:
        _read_session(request, cfg, store)
    except HTTPException:
        return {"configured": True, "authenticated": False, "account_limit": MAX_GOOGLE_ACCOUNTS}
    accounts = store.list_accounts(cfg["FINZANJIR_OWNER_EMAIL"])
    return {
        "configured": True,
        "authenticated": True,
        "owner_email": cfg["FINZANJIR_OWNER_EMAIL"],
        "account_count": sum(1 for item in accounts if item["status"] == "connected"),
        "account_limit": MAX_GOOGLE_ACCOUNTS,
        "accounts": accounts,
        "memory_source_count": len(memory.list_sources(cfg["FINZANJIR_OWNER_EMAIL"], limit=200)),
        "memory_media_count": len(memory.list_media(cfg["FINZANJIR_OWNER_EMAIL"], limit=200)),
    }
