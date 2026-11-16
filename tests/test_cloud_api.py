from fastapi.testclient import TestClient

from finzanjir_api.app import app


client = TestClient(app)


def test_cloud_connector_status_is_publicly_safe_and_default_deny(monkeypatch):
    for name in (
        "FINZANJIR_DROPBOX_CLIENT_ID",
        "FINZANJIR_MICROSOFT_CLIENT_ID",
        "FINZANJIR_GOOGLE_CLIENT_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    response = client.get("/api/cloud/connectors")
    assert response.status_code == 200
    body = response.json()
    assert body["connect_enabled"] is False
    assert body["status"] == "setup_required"
    assert len(body["providers"]) == 3
    assert all(item["connect_enabled"] is False for item in body["providers"])
    assert body["policy"]["write_access_enabled"] is False
    assert body["policy"]["automatic_upload_enabled"] is False
