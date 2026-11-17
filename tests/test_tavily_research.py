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


def test_tavily_raw_content_is_opt_in_and_bounded(monkeypatch):
    calls = []

    class RawResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{
                "title": "Public advisory",
                "url": "https://cisa.gov/advisories/one",
                "content": "Short snippet",
                "raw_content": "Full public extract " + "x" * 600000,
            }]}

    def fake_post(url, **kwargs):
        calls.append(kwargs["json"])
        return RawResponse()

    monkeypatch.setattr("finzanjir_ai.research.tavily.httpx.post", fake_post)
    client = TavilySearchClient(api_key="test-only")
    default = client.search("public advisory")
    assert default["results"][0]["raw_content"] == ""
    full = client.search("public advisory", include_raw_content=True)
    assert calls[-1]["include_raw_content"] is True
    assert len(full["results"][0]["raw_content"]) == 500000


def test_advanced_search_sends_depth_topic_and_time_filter(monkeypatch):
    import httpx

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(200, json={"results": [
            {"title": "Second", "url": "https://example.com/b", "content": "B", "score": 0.4},
            {"title": "First", "url": "https://example.com/a", "content": "A", "score": 0.9},
            {"title": "Duplicate", "url": "https://example.com/a", "content": "dup", "score": 0.8},
        ]})

    monkeypatch.setattr("finzanjir_ai.research.tavily.httpx.post", fake_post)
    monkeypatch.setattr(
        "finzanjir_ai.research.tavily.LLMGateway.can_send_text",
        lambda value: True,
    )
    result = TavilySearchClient(api_key="test-key").search(
        "Uzbekistan cybersecurity news",
        max_results=8,
        search_depth="advanced",
        topic="news",
        time_range="week",
    )

    assert captured["url"] == TavilySearchClient.ENDPOINT
    assert captured["json"]["search_depth"] == "advanced"
    assert captured["json"]["topic"] == "news"
    assert captured["json"]["time_range"] == "week"
    assert [item["title"] for item in result["results"]] == ["First", "Second"]
    assert result["search_depth"] == "advanced"


def test_search_rejects_unsupported_filters(monkeypatch):
    monkeypatch.setattr(
        "finzanjir_ai.research.tavily.LLMGateway.can_send_text",
        lambda value: True,
    )
    client = TavilySearchClient(api_key="test-key")
    with pytest.raises(ValueError, match="topic"):
        client.search("public information", topic="invalid")
    with pytest.raises(ValueError, match="time range"):
        client.search("public information", time_range="decade")
