from fastapi.testclient import TestClient

from finzanjir_api import app as api_module
from finzanjir_api.app import app
from finzanjir_ai.orchestration.intent import classify_query_intent


client = TestClient(app)


def test_explicit_youtube_channel_discovery_routes_to_web_search():
    assert classify_query_intent("Finzanjir YouTube kanalini top") == "web_search"
    assert classify_query_intent("Finzanjir nima?") == "project_overview"


def test_ai_answer_uses_external_search_for_youtube_discovery(monkeypatch):
    class FakeSearch:
        def search(self, query, *, max_results):
            assert "YouTube" in query
            assert max_results == 5
            return {
                "results": [{
                    "title": "FINZANJIR channel",
                    "url": "https://www.youtube.com/@finzanjir",
                    "content": "Public channel result",
                    "published_date": None,
                    "score": 0.91,
                }]
            }

    monkeypatch.setattr(api_module, "TavilySearchClient", FakeSearch)
    response = client.post(
        "/api/ai/answer",
        json={"question": "Finzanjir YouTube kanalini top"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["generation_mode"] == "web_search"
    assert body["knowledge_refs"] == []
    assert body["external_sources"][0]["url"] == "https://www.youtube.com/@finzanjir"
    assert "tashqi manbalar" in body["answer"]


def test_web_search_does_not_fall_back_to_project_knowledge_when_unconfigured(monkeypatch):
    class MissingSearch:
        def search(self, query, *, max_results):
            raise RuntimeError("not configured")

    monkeypatch.setattr(api_module, "TavilySearchClient", MissingSearch)
    response = client.post(
        "/api/ai/answer",
        json={"question": "Finzanjir YouTube kanalini top"},
    )
    assert response.status_code == 503
    assert "Internet qidiruvi" in response.json()["detail"]
