import hashlib
import time

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from finzanjir_api.app import app
from finzanjir_ai.integrations.google_cloud import (
    GoogleAccountStore,
    MAX_GOOGLE_ACCOUNTS,
    SERVICE_SCOPES,
    _authorization_url,
    _session_cookie,
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
    ):
        monkeypatch.delenv(key, raising=False)
    response = TestClient(app).get("/api/google/accounts")
    assert response.status_code == 503
    assert "token" not in response.text.lower()



def test_gmail_scope_is_explicit_read_only_only():
    assert SERVICE_SCOPES["gmail"] == ("https://www.googleapis.com/auth/gmail.readonly",)
    assert not any("send" in scope or "modify" in scope for scope in SERVICE_SCOPES["gmail"])
