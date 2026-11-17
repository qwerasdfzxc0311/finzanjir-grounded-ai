from finzanjir_ai.answer.providers import LLMGateway
from finzanjir_ai.knowledge.index import build_knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI
from finzanjir_ai.orchestration.intent import classify_query_intent


def _offline_engine(monkeypatch):
    gateway = LLMGateway(environ={
        "FINZANJIR_LLM_PROVIDER": "offline",
        "GEMINI_API_KEY": "must-not-be-used",
        "OPENROUTER_API_KEY": "must-not-be-used",
    })

    def forbidden_network_call(*_args, **_kwargs):
        raise AssertionError("offline path attempted a hosted model call")

    monkeypatch.setattr(gateway, "_generate_with", forbidden_network_call)
    engine = FINZANJIRAI(build_knowledge_index([]))
    engine.language_model = gateway
    engine.answer_generator.provider = gateway
    return engine, gateway


def test_offline_general_fact_answers_work_in_all_five_languages(monkeypatch):
    cases = (
        ("Nega osmon ko‘k?", "uz", "Rayleigh", "general_knowledge"),
        ("Aspannıń reńi ne ushın kók?", "kaa", "Rayleigh", "general_knowledge"),
        ("Неге аспан көк болып көрінеді?", "kk", "Рэлей", "general_knowledge"),
        ("Почему небо голубое?", "ru", "рассеяния", "general_knowledge"),
        ("Why is the sky blue?", "en", "Rayleigh", "general_knowledge"),
    )
    engine, gateway = _offline_engine(monkeypatch)
    for query, language, expected, intent in cases:
        assert classify_query_intent(query) == intent, query
        result = engine.answer(query, runtime_refs=(), working_memory_scope="offline-test")
        assert result.answer.abstained is False, query
        assert result.answer.generation_mode == "general_knowledge_local_facts", query
        assert result.answer.provider_status == "not_attempted", query
        assert expected.casefold() in result.answer.answer.casefold(), query
        assert result.answer.citations
        assert result.answer.provenance
    assert gateway.last_status == "not_attempted"


def test_offline_tortoise_lifespan_answers_misspelled_uzbek_without_provider(monkeypatch):
    engine, gateway = _offline_engine(monkeypatch)
    query = "toshvaqa qansha yil umir koradi"
    result = engine.answer(query, runtime_refs=(), working_memory_scope="offline-test")
    assert classify_query_intent(query) == "general_knowledge"
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "general_knowledge_local_facts"
    assert "150 yil" in result.answer.answer
    assert "toshbaqaning turi" in result.answer.answer.casefold()
    assert result.answer.provenance
    assert gateway.last_status == "not_attempted"


def test_offline_uzbekistan_geography_answers_without_current_population_claims(monkeypatch):
    cases = (
        ("O‘zbekiston haqida ma’lumot ber", "uz", "Markaziy Osiyo"),
        ("Ózbekstan haqqında maǵlıwmat ber", "kaa", "Oraylıq Aziyada"),
        ("Өзбекстан туралы мәлімет бер", "kk", "Орталық Азияда"),
        ("Расскажи об Узбекистане", "ru", "Центральной Азии"),
        ("Tell me about Uzbekistan", "en", "Central Asia"),
    )
    engine, gateway = _offline_engine(monkeypatch)
    for query, language, expected in cases:
        assert classify_query_intent(query) == "general_knowledge", query
        result = engine.answer(query, runtime_refs=(), working_memory_scope="offline-test")
        assert result.answer.abstained is False, query
        assert result.answer.generation_mode == "general_knowledge_local_facts", query
        assert expected.casefold() in result.answer.answer.casefold(), query
        assert result.answer.provenance
        assert "population" not in result.answer.answer.casefold()
    assert gateway.last_status == "not_attempted"


def test_project_question_remains_separate_and_works_without_hosted_model(monkeypatch):
    from finzanjir_ai.prototype.flow import build_system_flow

    engine, gateway = _offline_engine(monkeypatch)
    engine.index = build_system_flow().demo_knowledge_index()
    engine.retriever = __import__(
        "finzanjir_ai.retrieval.hybrid", fromlist=["HybridRetriever"]
    ).HybridRetriever(engine.index)
    engine.expander = __import__(
        "finzanjir_ai.retrieval.rerank", fromlist=["QueryExpander"]
    ).QueryExpander(engine.index)
    engine.reranker = __import__(
        "finzanjir_ai.retrieval.rerank", fromlist=["Reranker"]
    ).Reranker(engine.index)
    engine.grounder = __import__(
        "finzanjir_ai.retrieval.grounding", fromlist=["GroundedContextAssembler"]
    ).GroundedContextAssembler(engine.index)

    result = engine.answer(
        "FINZANJIR nima?",
        runtime_refs=(),
        working_memory_scope="offline-project-test",
    )
    assert result.answer.abstained is False
    assert result.answer.generation_mode == "project_overview_localized"
    assert result.answer.citations == ("project_0001",)
    assert gateway.last_status == "not_attempted"



def test_offline_unknown_general_topic_abstains_without_project_contamination(monkeypatch):
    engine, gateway = _offline_engine(monkeypatch)
    query = "What is photosynthesis?"
    assert classify_query_intent(query) == "general_knowledge"
    result = engine.answer(query, runtime_refs=(), working_memory_scope="offline-test")
    assert result.answer.abstained is True
    assert result.answer.generation_mode == "general_knowledge_provider_failed"
    assert "FINZANJIR" not in result.answer.answer
    assert gateway.last_status == "offline_mode"
