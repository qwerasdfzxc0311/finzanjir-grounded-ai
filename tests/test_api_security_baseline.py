import pytest
from fastapi.testclient import TestClient

from finzanjir_api.app import _parse_allowed_origins, app


client = TestClient(app)


def test_api_responses_include_security_and_no_store_headers():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_cors_is_same_origin_only_when_no_allowlist_is_configured():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_origin_parser_accepts_only_explicit_unique_http_origins():
    assert _parse_allowed_origins(None) == []
    assert _parse_allowed_origins("") == []
    assert _parse_allowed_origins("https://app.example, http://localhost:5173/") == [
        "https://app.example",
        "http://localhost:5173",
    ]


@pytest.mark.parametrize(
    "raw",
    [
        "*",
        "https://app.example,*",
        "ftp://app.example",
        "app.example",
        "https://app.example,https://app.example",
    ],
)
def test_origin_parser_rejects_wildcards_invalid_schemes_and_duplicates(raw):
    with pytest.raises(RuntimeError):
        _parse_allowed_origins(raw)
