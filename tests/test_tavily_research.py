import pytest

from finzanjir_ai.research.tavily import TavilySearchClient


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "results": [
                {
                    "title": "Official source",
                    "url": "https://example.org/reference",
                    "content": "A short external reference excerpt.",
                    "published_date": "2026-11-01",
                    "score": 0.91,
                },
                {"title": "No URL result", "content": "This result should be skipped."},
            ]
        }


def test_tavily_requires_server_side_key():
    with pytest.raises(RuntimeError, match="not configured"):
        TavilySearchClient(api_key="").search("RAG retrieval")


def test_tavily_refuses_common_sensitive_identifiers():
    with pytest.raises(ValueError, match="identifier"):
        TavilySearchClient(api_key="test").search("Card 8600 1234 5678 9012")


def test_tavily_returns_external_sources_without_claiming_canonical_status(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("finzanjir_ai.research.tavily.httpx.post", fake_post)
    result = TavilySearchClient(api_key="test-only").search("multilingual RAG retrieval", max_results=99)

    assert result["source_type"] == "external_web_research"
    assert len(result["results"]) == 1
    assert result["results"][0]["url"] == "https://example.org/reference"
    assert "FINZANJIRning tasdiqlangan bilimlar bazasi emas" in result["warning"]
    assert calls[0][1]["json"]["max_results"] == 8
    assert calls[0][1]["json"]["include_answer"] is False
    assert calls[0][1]["headers"]["Authorization"] == "Bearer test-only"
