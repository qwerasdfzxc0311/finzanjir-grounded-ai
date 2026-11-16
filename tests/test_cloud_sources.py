import pytest

from finzanjir_ai.integrations.cloud_sources import (
    cloud_connector_status,
    validate_requested_scopes,
)


def test_cloud_connections_are_disabled_until_security_gateway_exists():
    status = cloud_connector_status()
    assert status["connect_enabled"] is False
    assert status["status"] == "setup_required"
    assert all(provider["connect_enabled"] is False for provider in status["providers"])


def test_registry_only_exposes_read_only_scopes():
    status = cloud_connector_status()
    for provider in status["providers"]:
        assert provider["access_mode"] == "read_only"
        assert provider["write_scopes"] == []
    assert status["policy"]["write_access_enabled"] is False
    assert status["policy"]["public_sharing_enabled"] is False
    assert status["policy"]["automatic_knowledge_promotion"] is False


def test_provider_client_configuration_is_reported_without_secret_values():
    status = cloud_connector_status({"FINZANJIR_DROPBOX_CLIENT_ID"})
    dropbox = next(item for item in status["providers"] if item["provider_id"] == "dropbox")
    assert dropbox["client_application_configured"] is True
    assert "FINZANJIR_DROPBOX_CLIENT_ID" not in str(status)


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError):
        validate_requested_scopes("unknown", ["files.content.read"])


def test_write_or_unapproved_scopes_are_rejected():
    with pytest.raises(ValueError):
        validate_requested_scopes("dropbox", ["files.content.write"])
    with pytest.raises(ValueError):
        validate_requested_scopes("onedrive", ["Files.ReadWrite"])


def test_read_only_scopes_are_deduplicated_and_preserved():
    assert validate_requested_scopes(
        "dropbox", ["files.metadata.read", "files.metadata.read"]
    ) == ("files.metadata.read",)
