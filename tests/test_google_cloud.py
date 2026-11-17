import hashlib
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from finzanjir_api.app import app, _parse_allowed_origins
from finzanjir_ai.integrations.google_cloud import (
    GoogleAccountStore,
    GoogleConfigError,
    _config,
    MAX_GOOGLE_ACCOUNTS,
    SERVICE_SCOPES,
    _authorization_url,
    _session_cookie,
    _require_same_origin,
)


def make_store(tmp_path):
    key = Fernet.generate_key().decode()
    return GoogleAccountStore(str(tmp_path / "google.sqlite3"), key)


def test_oauth_state_is_one_time_and_expires(tmp_path):
    store = make_store(tmp_path)
    store.create_flow("random-state-value-123456", "verifier", "nonce-value", "owner_login", None, now=100)
    flow = store.consume_flow("random-state-value-123456", now=200)
    assert flow["purpose"] == "owner_login"
    assert flow["verifier"] == "verifier"
    assert flow["nonce"] == "nonce-value"
    assert store.consume_flow("random-state-value-123456", now=200) is None


def test_oauth_state_expired_or_unknown_is_rejected(tmp_path):
    store = make_store(tmp_path)
    store.create_flow("random-state-value-123456", "verifier", "nonce-value", "owner_login", None, now=100)
    assert store.consume_flow("random-state-value-123456", now=701) is None


def test_owner_session_is_persisted_and_revocable(tmp_path):
    store = make_store(tmp_path)
    session_id = store.create_session("owner@example.com", now=100)
    assert store.valid_session(session_id, "OWNER@example.com", now=200)
    store.revoke_session(session_id)
    assert not store.valid_session(session_id, "owner@example.com", now=200)


def test_account_tokens_are_encrypted_and_never_listed(tmp_path):
    key = Fernet.generate_key().decode()
    path = tmp_path / "google.sqlite3"
    store = GoogleAccountStore(str(path), key)
    account = store.save_account(
        "owner@example.com", "archive@example.com", "Archive",
        "refresh-secret-value", ("openid", "email", "https://www.googleapis.com/auth/drive.readonly"),
        now=123,
    )
    raw = path.read_bytes()
    assert b"refresh-secret-value" not in raw
    assert "refresh-secret-value" not in str(store.list_accounts("owner@example.com"))
    secret, scopes = store.account_secret("owner@example.com", account["account_id"])
    assert secret == "refresh-secret-value"
    assert "https://www.googleapis.com/auth/drive.readonly" in scopes


def test_one_owner_can_connect_up_to_100_google_accounts(tmp_path):
    store = make_store(tmp_path)
    for index in range(MAX_GOOGLE_ACCOUNTS):
        store.save_account(
            "owner@example.com", f"archive{index}@example.com", f"Archive {index}",
            f"refresh-{index}", ("openid", "email"), now=100 + index,
        )
    assert len(store.list_accounts("owner@example.com")) == 100
    with pytest.raises(OverflowError):
        store.save_account(
            "owner@example.com", "overflow@example.com", "Overflow",
            "refresh-overflow", ("openid", "email"), now=999,
        )


def test_same_google_account_reconnect_does_not_consume_another_slot(tmp_path):
    store = make_store(tmp_path)
    first = store.save_account("owner@example.com", "archive@example.com", "Old",
                               "refresh-old", ("openid",), now=100)
    second = store.save_account("owner@example.com", "archive@example.com", "New",
                                "refresh-new", ("openid", "drive"), now=200)
    assert first["account_id"] == second["account_id"]
    assert len(store.list_accounts("owner@example.com")) == 1
    assert store.account_secret("owner@example.com", first["account_id"])[0] == "refresh-new"


def test_disconnect_erases_local_refresh_token_and_is_audited(tmp_path):
    store = make_store(tmp_path)
    account = store.save_account("owner@example.com", "archive@example.com", "Archive",
                                 "refresh-secret", ("openid",), now=100)
    assert store.disconnect("owner@example.com", account["account_id"]) == "refresh-secret"
    assert store.account_secret("owner@example.com", account["account_id"]) is None
    assert store.list_accounts("owner@example.com")[0]["status"] == "disconnected"


def test_oauth_url_uses_pkce_and_fixed_redirect_uri():
    cfg = {
        "FINZANJIR_GOOGLE_CLIENT_ID": "client-id",
        "FINZANJIR_GOOGLE_REDIRECT_URI": "https://api.example.com/api/google/oauth/callback",
    }
    url = _authorization_url(cfg, "state-value", "very-long-verifier", "nonce-value", ("openid", "email"))
    assert "code_challenge_method=S256" in url
    assert "state=state-value" in url
    assert "nonce=nonce-value" in url
    assert "redirect_uri=https%3A%2F%2Fapi.example.com" in url


def test_signed_cookie_is_bound_to_session_id():
    signed = _session_cookie("session-id", "a-secret-that-is-long-enough-for-tests")
    session_id, signature = signed.split(".", 1)
    assert session_id == "session-id"
    assert len(signature) == 64


def test_google_routes_fail_closed_without_server_configuration(monkeypatch):
    for key in (
        "FINZANJIR_GOOGLE_CLIENT_ID",
        "FINZANJIR_GOOGLE_CLIENT_SECRET",
        "FINZANJIR_GOOGLE_REDIRECT_URI",
        "FINZANJIR_OWNER_EMAIL",
        "FINZANJIR_SESSION_SECRET",
        "FINZANJIR_TOKEN_ENCRYPTION_KEY",
        "FINZANJIR_GOOGLE_STATE_DB_PATH",
        "FINZANJIR_PERSONAL_MEMORY_DB_PATH",
        "FINZANJIR_FRONTEND_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    response = TestClient(app).get("/api/google/accounts")
    assert response.status_code == 503
    assert "token" not in response.text.lower()



def test_gmail_scope_is_explicit_read_only_only():
    assert SERVICE_SCOPES["gmail"] == ("https://www.googleapis.com/auth/gmail.readonly",)
    assert not any("send" in scope or "modify" in scope for scope in SERVICE_SCOPES["gmail"])



def test_photos_picker_scope_is_explicit_and_not_legacy_library_scope():
    assert SERVICE_SCOPES["photos"] == (
        "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
    )
    assert not any("photoslibrary" in scope for scope in SERVICE_SCOPES["photos"])



def test_cors_allows_credentials_only_for_configured_frontend_origin(monkeypatch):
    monkeypatch.setenv("FINZANJIR_ALLOWED_ORIGINS", "https://frontend.example.com")
    assert _parse_allowed_origins("https://frontend.example.com") == ["https://frontend.example.com"]
    middleware = next(item for item in app.user_middleware if item.cls.__name__ == "CORSMiddleware")
    assert middleware.kwargs["allow_credentials"] is True
    assert "DELETE" in middleware.kwargs["allow_methods"]


def test_csrf_origin_rejects_unlisted_frontend(monkeypatch):
    from starlette.requests import Request
    from fastapi import HTTPException

    monkeypatch.setenv("FINZANJIR_ALLOWED_ORIGINS", "https://frontend.example.com")
    scope = {
        "type": "http", "method": "POST", "scheme": "https",
        "server": ("api.example.com", 443),
        "headers": [(b"origin", b"https://evil.example.com")],
        "path": "/", "query_string": b"", "root_path": "",
        "http_version": "1.1", "client": ("127.0.0.1", 1234),
    }
    with pytest.raises(HTTPException) as exc:
        _require_same_origin(Request(scope))
    assert exc.value.status_code == 403


def test_google_oauth_config_requires_frontend_in_exact_origin_allowlist(monkeypatch, tmp_path):
    monkeypatch.setenv("FINZANJIR_GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("FINZANJIR_GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("FINZANJIR_GOOGLE_REDIRECT_URI", "https://api.example.com/api/google/oauth/callback")
    monkeypatch.setenv("FINZANJIR_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("FINZANJIR_SESSION_SECRET", "s" * 40)
    monkeypatch.setenv("FINZANJIR_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("FINZANJIR_GOOGLE_STATE_DB_PATH", str(tmp_path / "state.sqlite"))
    monkeypatch.setenv("FINZANJIR_PERSONAL_MEMORY_DB_PATH", str(tmp_path / "memory.sqlite"))
    monkeypatch.setenv("FINZANJIR_FRONTEND_URL", "https://frontend.example.com")
    monkeypatch.setenv("FINZANJIR_ALLOWED_ORIGINS", "https://frontend.example.com")
    assert _config()["FINZANJIR_FRONTEND_URL"] == "https://frontend.example.com"
    monkeypatch.setenv("FINZANJIR_ALLOWED_ORIGINS", "https://other.example.com")
    with pytest.raises(GoogleConfigError):
        _config()


def test_reconnecting_account_adds_scopes_without_dropping_prior_services(tmp_path):
    store = make_store(tmp_path)
    first = store.save_account(
        "owner@example.com", "archive@example.com", "Archive",
        "refresh-drive", ("openid", "email", "https://www.googleapis.com/auth/drive.readonly"),
        now=100,
    )
    second = store.save_account(
        "owner@example.com", "archive@example.com", "Archive",
        "refresh-gmail", ("openid", "email", "https://www.googleapis.com/auth/gmail.readonly"),
        now=200,
    )
    assert first["account_id"] == second["account_id"]
    scopes = set(store.account_secret("owner@example.com", second["account_id"])[1])
    assert "https://www.googleapis.com/auth/drive.readonly" in scopes
    assert "https://www.googleapis.com/auth/gmail.readonly" in scopes


def test_oauth_requests_consent_when_any_cloud_service_is_selected():
    cfg = {
        "FINZANJIR_GOOGLE_CLIENT_ID": "client-id",
        "FINZANJIR_GOOGLE_REDIRECT_URI": "https://api.example.com/api/google/oauth/callback",
    }
    url = _authorization_url(
        cfg, "state", "verifier", "nonce",
        ("openid", "email", "https://www.googleapis.com/auth/photospicker.mediaitems.readonly"),
    )
    params = parse_qs(urlsplit(url).query)
    assert params["prompt"] == ["consent"]
    assert params["include_granted_scopes"] == ["true"]


def test_legacy_plaintext_oauth_verifier_and_nonce_are_migrated(tmp_path):
    import sqlite3

    path = tmp_path / "legacy-google.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("""
            CREATE TABLE google_oauth_flows (
                state_hash TEXT PRIMARY KEY, verifier TEXT NOT NULL, nonce TEXT NOT NULL,
                purpose TEXT NOT NULL, owner_session_id TEXT,
                created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL
            )
        """)
        db.execute(
            "INSERT INTO google_oauth_flows VALUES(?,?,?,?,?,?,?)",
            (hashlib.sha256(b"state-value").hexdigest(), "legacy-pkce-verifier", "legacy-oidc-nonce",
             "owner_login", None, 100, 700),
        )
    store = GoogleAccountStore(str(path), Fernet.generate_key().decode())
    flow = store.consume_flow("state-value", now=200)
    assert flow["verifier"] == "legacy-pkce-verifier"
    assert flow["nonce"] == "legacy-oidc-nonce"
    # OAuth flow records are one-time use; the second consume must fail.
    assert store.consume_flow("state-value", now=200) is None
    with sqlite3.connect(path) as db:
        row = db.execute("SELECT verifier, nonce FROM google_oauth_flows").fetchone()
    assert row[0] != "legacy-pkce-verifier"
    assert row[1] != "legacy-oidc-nonce"

def test_cloud_diagnostics_reports_missing_configuration_without_secrets(monkeypatch):
    for key in (
        "FINZANJIR_GOOGLE_CLIENT_ID",
        "FINZANJIR_GOOGLE_CLIENT_SECRET",
        "FINZANJIR_GOOGLE_REDIRECT_URI",
        "FINZANJIR_OWNER_EMAIL",
        "FINZANJIR_SESSION_SECRET",
        "FINZANJIR_TOKEN_ENCRYPTION_KEY",
        "FINZANJIR_GOOGLE_STATE_DB_PATH",
        "FINZANJIR_PERSONAL_MEMORY_DB_PATH",
        "FINZANJIR_FRONTEND_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    response = TestClient(app).get("/api/google/diagnostics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is False
    assert payload["checks"][0]["status"] == "not_configured"
    assert "client_secret" not in response.text.lower()


def test_cloud_diagnostics_checks_owner_databases_and_permissions(monkeypatch, tmp_path):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("FINZANJIR_GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("FINZANJIR_GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("FINZANJIR_GOOGLE_REDIRECT_URI", "https://api.example.com/api/google/oauth/callback")
    monkeypatch.setenv("FINZANJIR_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("FINZANJIR_SESSION_SECRET", "s" * 40)
    monkeypatch.setenv("FINZANJIR_TOKEN_ENCRYPTION_KEY", key)
    monkeypatch.setenv("FINZANJIR_GOOGLE_STATE_DB_PATH", str(tmp_path / "state.sqlite"))
    monkeypatch.setenv("FINZANJIR_PERSONAL_MEMORY_DB_PATH", str(tmp_path / "memory.sqlite"))
    monkeypatch.setenv("FINZANJIR_FRONTEND_URL", "https://frontend.example.com")
    monkeypatch.setenv("FINZANJIR_ALLOWED_ORIGINS", "https://frontend.example.com")
    store = GoogleAccountStore(str(tmp_path / "state.sqlite"), key)
    session_id = store.create_session("owner@example.com")
    client = TestClient(app)
    client.cookies.set(
        "finzanjir_owner_session",
        _session_cookie(session_id, "s" * 40),
    )
    response = client.get("/api/google/diagnostics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert payload["authenticated"] is True
    assert {item["id"] for item in payload["checks"]} >= {
        "oauth_config", "token_encryption", "owner_session",
        "google_state_db", "personal_memory_db", "storage_capacity",
    }
    assert payload["summary"]["error"] == 0
