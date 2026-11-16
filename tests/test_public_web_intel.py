from finzanjir_ai.intel.public_web import (
    EvidenceRecord, OfflineEvidenceStore, PublicWebIntelClient, WebIntelError,
)


def test_offline_cache_round_trip(tmp_path):
    store = OfflineEvidenceStore(tmp_path / "evidence.sqlite")
    record = EvidenceRecord(
        url="https://example.org/report.txt", domain="example.org",
        retrieved_at="2026-11-16T00:00:00+00:00", content_type="text/plain",
        text="public report", sha256="abc123",
    )
    store.put(record)
    client = PublicWebIntelClient(["example.org"], cache=store)
    cached = client.fetch(record.url, offline=True)
    assert cached.text == "public report"
    assert cached.source_mode == "offline_cache"


def test_offline_cache_miss_fails_closed():
    client = PublicWebIntelClient(["example.org"])
    try:
        client.fetch("https://example.org/missing", offline=True)
    except WebIntelError as exc:
        assert "No cached evidence" in str(exc)
    else:
        raise AssertionError("offline cache miss must fail closed")


def test_non_https_rejected():
    client = PublicWebIntelClient(["example.org"])
    try:
        client.fetch("http://example.org/report")
    except WebIntelError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("plain HTTP must be rejected")


def test_domain_not_allowlisted():
    client = PublicWebIntelClient(["trusted.example"])
    try:
        client.fetch("https://example.org/report")
    except WebIntelError as exc:
        assert "allowlist" in str(exc)
    else:
        raise AssertionError("unapproved domain must be rejected")
