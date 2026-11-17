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
        def search(self, query, *, max_results, search_depth="advanced", include_raw_content=False):
            assert "YouTube" in query
            assert max_results == 6
            assert search_depth == "advanced"
            assert include_raw_content is True
            return {
                "results": [{
                    "title": "FINZANJIR channel",
                    "url": "https://www.youtube.com/@finzanjir",
                    "content": "Public channel result",
                    "raw_content": "The FINZANJIR YouTube channel publishes public videos about the project.",
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
    assert body["composition_mode"] == "tavily_local_extractive"
    assert body["provider_status"] == "not_attempted"
    assert body["knowledge_refs"] == []
    assert body["external_sources"][0]["url"] == "https://www.youtube.com/@finzanjir"
    assert "Tavily" in body["answer"]


def test_web_search_does_not_fall_back_to_project_knowledge_when_unconfigured(monkeypatch):
    class MissingSearch:
        def search(self, query, *, max_results, search_depth="advanced", include_raw_content=False):
            raise RuntimeError("not configured")

    monkeypatch.setattr(api_module, "TavilySearchClient", MissingSearch)
    response = client.post(
        "/api/ai/answer",
        json={"question": "Finzanjir YouTube kanalini top"},
    )
    assert response.status_code == 503
    assert "Internet qidiruvi" in response.json()["detail"]


def test_auto_general_knowledge_uses_tavily_and_local_composer_without_llm(monkeypatch):
    from types import SimpleNamespace

    assert classify_query_intent("What is photosynthesis?") == "general_knowledge"
    calls = {"engines": [], "searches": 0}

    class OfflineEngine:
        def answer(self, *args, **kwargs):
            return SimpleNamespace(answer=SimpleNamespace(abstained=True))

    class FakeSearch:
        def search(self, query, *, max_results, search_depth="advanced", include_raw_content=False):
            calls["searches"] += 1
            assert query == "What is photosynthesis?"
            assert max_results == 6
            assert search_depth == "advanced"
            assert include_raw_content is True
            return {
                "results": [{
                    "title": "University biology guide",
                    "url": "https://biology.example.edu/photosynthesis",
                    "content": "Photosynthesis is the process by which green plants use sunlight to make food.",
                    "raw_content": (
                        "Photosynthesis is the process by which green plants use sunlight "
                        "to make food from carbon dioxide and water. Oxygen is released "
                        "as a byproduct of this process."
                    ),
                    "published_date": None,
                    "score": 0.94,
                }]
            }

    def fake_engine(policy="auto"):
        calls["engines"].append(policy)
        assert policy == "offline"
        return OfflineEngine()

    monkeypatch.setattr(api_module, "ai_engine", fake_engine)
    monkeypatch.setattr(api_module, "TavilySearchClient", FakeSearch)
    response = client.post(
        "/api/ai/answer",
        json={"question": "What is photosynthesis?", "model_policy": "auto"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is False
    assert body["generation_mode"] == "tavily_local_extractive"
    assert body["composition_mode"] == "tavily_local_extractive"
    assert body["provider_status"] == "not_attempted"
    assert body["external_sources"][0]["url"] == "https://biology.example.edu/photosynthesis"
    assert "Photosynthesis is the process" in body["answer"]
    assert calls == {"engines": ["offline"], "searches": 1}


def test_offline_explicit_web_search_never_calls_tavily(monkeypatch):
    class ForbiddenSearch:
        def search(self, *args, **kwargs):
            raise AssertionError("offline mode must not make a Tavily request")

    monkeypatch.setattr(api_module, "TavilySearchClient", ForbiddenSearch)
    response = client.post(
        "/api/ai/answer",
        json={
            "question": "Search the internet for official NASA astronomy resources",
            "model_policy": "offline",
        },
    )

    assert response.status_code == 503
    assert "Offline" in response.json()["detail"]


def test_project_question_does_not_fall_back_to_public_web_search(monkeypatch):
    from types import SimpleNamespace

    class ForbiddenSearch:
        def search(self, *args, **kwargs):
            raise AssertionError("project questions must stay inside project sources")

    class ProjectEngine:
        language_model = SimpleNamespace(last_provider_failures=())

        def answer(self, *args, **kwargs):
            return SimpleNamespace(
                answer=SimpleNamespace(
                    answer="Loyiha manbalarida yetarli dalil topilmadi.",
                    confidence=0.0,
                    abstained=True,
                    generation_mode="deterministic_fallback",
                    provider_status="not_attempted",
                    citations=(),
                    provenance=(),
                ),
                grounded_context=SimpleNamespace(items=()),
                runtime_context=SimpleNamespace(runtime_refs=()),
            )

    monkeypatch.setattr(api_module, "TavilySearchClient", ForbiddenSearch)
    monkeypatch.setattr(api_module, "ai_engine", lambda policy="auto": ProjectEngine())
    response = client.post(
        "/api/ai/answer",
        json={"question": "FINZANJIR bank kartasini bloklay oladimi?", "model_policy": "auto"},
    )

    assert response.status_code == 200
    assert response.json()["external_sources"] == []
    assert response.json()["abstained"] is True
