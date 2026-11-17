from __future__ import annotations

import httpx

from finzanjir_ai.research import service
from finzanjir_ai.research.local_answer import compose_tavily_local_answer


def _source(title="Biology guide", url="https://en.wikipedia.org/wiki/Photosynthesis"):
    return {
        "title": title,
        "url": url,
        "snippet": "Photosynthesis is the process by which plants use light energy.",
        "raw_content": (
            "Photosynthesis is the process by which green plants use sunlight "
            "to make food from carbon dioxide and water. Oxygen is released "
            "as a byproduct of this process."
        ),
        "score": 0.92,
    }


def test_wikimedia_composer_labels_backup_provider_and_keeps_source():
    result = compose_tavily_local_answer(
        "What is photosynthesis?",
        [_source()],
        provider_name="Wikimedia",
    )
    assert result.abstained is False
    assert result.generation_mode == "wikimedia_local_extractive"
    assert "Wikimedia" in result.answer
    assert result.provenance == ("https://en.wikipedia.org/wiki/Photosynthesis",)


def test_tavily_quota_failure_falls_back_to_wikimedia_without_llm(monkeypatch):
    service.clear_research_state_for_tests()
    calls = {"tavily": 0, "wikimedia": 0}

    class QuotaTavily:
        def search(self, *args, **kwargs):
            calls["tavily"] += 1
            request = httpx.Request("POST", "https://api.tavily.com/search")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    class BackupWiki:
        def search(self, query, *, max_results):
            calls["wikimedia"] += 1
            return {"results": [_source()]}

    monkeypatch.setattr(service, "TavilySearchClient", QuotaTavily)
    monkeypatch.setattr(service, "WikimediaSearchClient", BackupWiki)

    result = service.search_and_compose("What is the latest research on photosynthesis today?")
    assert result is not None
    assert result["abstained"] is False
    assert result["generation_mode"] == "wikimedia_local_extractive"
    assert result["research_provider"] == "wikimedia"
    assert result["provider_status"] == "not_attempted"
    assert result["research_diagnostics"][0]["status"] == "rate_limited"
    assert calls == {"tavily": 1, "wikimedia": 1}


def test_tavily_cooldown_skips_repeated_quota_requests(monkeypatch):
    service.clear_research_state_for_tests()
    calls = {"tavily": 0, "wikimedia": 0}

    class QuotaTavily:
        def search(self, *args, **kwargs):
            calls["tavily"] += 1
            request = httpx.Request("POST", "https://api.tavily.com/search")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    class BackupWiki:
        def search(self, query, *, max_results):
            calls["wikimedia"] += 1
            return {"results": [_source()]}

    monkeypatch.setattr(service, "TavilySearchClient", QuotaTavily)
    monkeypatch.setattr(service, "WikimediaSearchClient", BackupWiki)

    first = service.search_and_compose("What is the latest research on photosynthesis today?")
    second = service.search_and_compose("What are today's latest findings about photosynthesis?")
    assert first and second
    assert calls["tavily"] == 1
    assert calls["wikimedia"] == 2
    assert any(item["status"] == "rate_limited" for item in second["research_diagnostics"])


def test_successful_public_extract_is_cached_and_does_not_spend_tavily_again(monkeypatch):
    service.clear_research_state_for_tests()
    calls = {"tavily": 0, "wikimedia": 0}

    class GoodTavily:
        def search(self, *args, **kwargs):
            calls["tavily"] += 1
            return {"results": [_source(url="https://biology.example.edu/photosynthesis")]}

    class ForbiddenWiki:
        def search(self, *args, **kwargs):
            calls["wikimedia"] += 1
            raise AssertionError("Wikimedia should not be needed after a cache hit")

    monkeypatch.setattr(service, "TavilySearchClient", GoodTavily)
    monkeypatch.setattr(service, "WikimediaSearchClient", ForbiddenWiki)

    first = service.search_and_compose("What is the latest research on photosynthesis today?")
    second = service.search_and_compose("What is the latest research on photosynthesis today?")
    assert first and second
    assert first["generation_mode"] == "tavily_local_extractive"
    assert second["generation_mode"] == "cached_local_extractive"
    assert second["research_provider"] == "cache"
    assert calls == {"tavily": 1, "wikimedia": 0}


def test_cache_refuses_sensitive_identifiers():
    service.clear_research_state_for_tests()
    service._PUBLIC_RESEARCH_CACHE.put(
        "Call me at +998 90 123 45 67",
        "Tavily",
        [_source()],
    )
    assert service._PUBLIC_RESEARCH_CACHE.get("Call me at +998 90 123 45 67") is None


def test_stable_general_question_uses_wikimedia_before_tavily(monkeypatch):
    service.clear_research_state_for_tests()
    calls = {"tavily": 0, "wikimedia": 0}

    class ForbiddenTavily:
        def search(self, *args, **kwargs):
            calls["tavily"] += 1
            raise AssertionError("Stable encyclopedic questions should try Wikimedia first")

    class BackupWiki:
        def search(self, query, *, max_results):
            calls["wikimedia"] += 1
            return {"results": [_source()]}

    monkeypatch.setattr(service, "TavilySearchClient", ForbiddenTavily)
    monkeypatch.setattr(service, "WikimediaSearchClient", BackupWiki)

    result = service.search_and_compose("What is photosynthesis?")
    assert result is not None
    assert result["generation_mode"] == "wikimedia_local_extractive"
    assert result["research_provider"] == "wikimedia"
    assert calls == {"tavily": 0, "wikimedia": 1}


def test_wikimedia_client_fetches_search_results_and_extracts(monkeypatch):
    from finzanjir_ai.research.wikipedia import WikimediaSearchClient

    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def fake_get(url, *, params, headers, timeout, follow_redirects):
        calls.append((url, params))
        if params["list"] == "search":
            return FakeResponse({
                "query": {
                    "search": [{
                        "title": "Photosynthesis",
                        "snippet": "Photosynthesis is <b>the process</b> used by plants.",
                    }]
                }
            })
        return FakeResponse({
            "query": {
                "pages": [{
                    "title": "Photosynthesis",
                    "extract": (
                        "Photosynthesis is the process by which green plants use sunlight "
                        "to make food from carbon dioxide and water. Oxygen is released "
                        "as a byproduct of this process."
                    ),
                }]
            }
        })

    monkeypatch.setattr("finzanjir_ai.research.wikipedia.httpx.get", fake_get)
    result = WikimediaSearchClient().search("What is photosynthesis?")

    assert len(calls) == 2
    assert calls[0][1]["list"] == "search"
    assert calls[1][1]["prop"] == "extracts"
    assert result["language"] == "en"
    assert result["results"][0]["url"] == "https://en.wikipedia.org/wiki/Photosynthesis"
    assert "Photosynthesis is the process" in result["results"][0]["raw_content"]


def test_wikimedia_client_blocks_sensitive_queries_before_network(monkeypatch):
    from finzanjir_ai.research.wikipedia import WikimediaSearchClient

    def forbidden_get(*args, **kwargs):
        raise AssertionError("Sensitive search queries must not reach Wikimedia")

    monkeypatch.setattr("finzanjir_ai.research.wikipedia.httpx.get", forbidden_get)
    try:
        WikimediaSearchClient().search("Contact +998 90 123 45 67")
    except ValueError as exc:
        assert "personal or payment identifier" in str(exc)
    else:
        raise AssertionError("Expected sensitive query rejection")
