"""Safe cloud-source capability registry.

This is intentionally a discovery/policy layer, not an OAuth implementation.
No provider credentials, access tokens, user files, or cloud contents are read here.
Connection remains disabled until FINZANJIR has a real authenticated identity layer,
OAuth 2.1/PKCE flow, encrypted token vault, and revocation/audit handling.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CloudProviderPolicy:
    provider_id: str
    display_name: str
    environment_client_id: str
    readonly_scopes: tuple[str, ...]
    write_scopes: tuple[str, ...] = ()
    supports_readonly: bool = True


PROVIDERS: tuple[CloudProviderPolicy, ...] = (
    CloudProviderPolicy(
        provider_id="dropbox",
        display_name="Dropbox",
        environment_client_id="FINZANJIR_DROPBOX_CLIENT_ID",
        readonly_scopes=("files.metadata.read", "files.content.read"),
    ),
    CloudProviderPolicy(
        provider_id="onedrive",
        display_name="Microsoft OneDrive",
        environment_client_id="FINZANJIR_MICROSOFT_CLIENT_ID",
        readonly_scopes=("Files.Read", "User.Read"),
    ),
    CloudProviderPolicy(
        provider_id="google_drive",
        display_name="Google Drive",
        environment_client_id="FINZANJIR_GOOGLE_CLIENT_ID",
        # drive.file is intentionally narrower than full-drive read access.
        readonly_scopes=("https://www.googleapis.com/auth/drive.file",),
    ),
)

_REQUIRED_SECURITY_CONTROLS = (
    "authenticated_user_identity",
    "oauth_state_and_pkce",
    "encrypted_server_side_token_vault",
    "token_refresh_and_revocation",
    "per_user_source_isolation",
    "audit_log_and_user_disconnect",
)


def cloud_connector_status(
    configured_environment: Iterable[str] = (),
) -> dict[str, object]:
    """Return safe, non-secret provider readiness; never return env values."""
    configured = set(configured_environment)
    providers = []
    for provider in PROVIDERS:
        client_configured = provider.environment_client_id in configured
        providers.append({
            "provider_id": provider.provider_id,
            "display_name": provider.display_name,
            "status": "not_connected",
            "client_application_configured": client_configured,
            "connect_enabled": False,
            "access_mode": "read_only",
            "approved_scopes": list(provider.readonly_scopes),
            "write_scopes": [],
            "reason": (
                "Xavfsiz OAuth ulanish mexanizmi va foydalanuvchi autentifikatsiyasi "
                "hali tayyor emas; ulanish hozircha ataylab o‘chirilgan."
            ),
        })
    return {
        "status": "setup_required",
        "connect_enabled": False,
        "providers": providers,
        "security_controls_required": list(_REQUIRED_SECURITY_CONTROLS),
        "policy": {
            "read_only_by_default": True,
            "write_access_enabled": False,
            "public_sharing_enabled": False,
            "automatic_upload_enabled": False,
            "automatic_knowledge_promotion": False,
            "training_from_cloud_files": False,
            "user_chat_upload": False,
        },
    }


def validate_requested_scopes(provider_id: str, requested_scopes: Iterable[str]) -> tuple[str, ...]:
    """Reject unknown providers and any scope beyond the approved read-only set."""
    provider = next((item for item in PROVIDERS if item.provider_id == provider_id), None)
    if provider is None:
        raise ValueError("Unknown cloud provider")
    requested = tuple(dict.fromkeys(scope.strip() for scope in requested_scopes if scope.strip()))
    allowed = set(provider.readonly_scopes)
    if not requested or any(scope not in allowed for scope in requested):
        raise ValueError("Requested cloud permissions exceed the approved read-only scope")
    return requested
