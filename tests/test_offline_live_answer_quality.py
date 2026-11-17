from functools import lru_cache

from finzanjir_api.app import knowledge_index
from finzanjir_ai.orchestration.engine import FINZANJIRAI


@lru_cache(maxsize=1)
def _offline_engine():
    engine = FINZANJIRAI(knowledge_index())
    # Keep this benchmark deterministic and strictly offline in CI.
    engine.language_model.environ = {}
    return engine


def _answer(question: str):
    return _offline_engine().answer(
        question,
        runtime_refs=(),
        working_memory_scope="offline-50q-benchmark",
    ).answer


def test_offline_benchmark_bank_neutrality_never_blames_banks():
    result = _answer("FINZANJIR banklarga qarshimi?")
    if result.abstained:
        assert any(
            phrase in result.answer.casefold()
            for phrase in ("yetarli tasdiqlangan dalil", "javobni chekladim", "dalil")
        )
    else:
        assert any(word in result.answer.casefold() for word in ("bank", "hamkor", "qarshi"))
    assert "banklarni aybl" not in result.answer.casefold()


def test_offline_benchmark_signal_is_not_presented_as_guilt():
    result = _answer("Signal fuqaroning aybdorligini isbotlaydimi?")
    assert result.abstained is False
    assert "aybdor" in result.answer.casefold()
    assert "isbot" in result.answer.casefold()


def test_offline_benchmark_case_answer_excludes_unrelated_security_attack_terms():
    result = _answer("Case nima uchun ochiladi?")
    assert result.abstained is False
    assert "case" in result.answer.casefold()
    assert "idor" not in result.answer.casefold()
    assert "bola" not in result.answer.casefold()


def test_offline_benchmark_fraud_graph_is_an_explanation_not_alias_list():
    result = _answer("Fraud Graph nima?")
    answer = result.answer.casefold()
    assert result.abstained is False
    assert "fraud graph: [" not in answer
    assert "fraud graph" in answer
    assert any(term in answer for term in ("karta", "tranzaksiya", "bog'lan", "aloqa"))


def test_offline_benchmark_fin_recovery_answer_excludes_biology_contamination():
    result = _answer("FIN-RECOVERY nima vazifani bajaradi?")
    answer = result.answer.casefold()
    assert "to'qima" not in answer
    assert "hujayra" not in answer
    assert "recovery" in answer or "tiklash" in answer or "hodisadan keyin" in answer


def test_offline_benchmark_c_model_answer_is_relevant_or_abstains():
    result = _answer("FINZANJIRning C modeli qanday ishlaydi?")
    answer = result.answer.casefold()
    assert result.abstained or (
        "atmos" not in answer
        and any(term in answer for term in ("banklararo", "banklar o'rtasida", "signallar", "ma'lumot almash"))
    )


def test_offline_benchmark_sixteen_layer_answer_is_relevant_or_abstains():
    result = _answer("FINZANJIRning 16 qatlamli arxitekturasi nimani anglatadi?")
    answer = result.answer.casefold()
    assert result.abstained or (
        ("qatlam" in answer or "layer" in answer)
        and ("16" in answer or "o'n olti" in answer)
    )


def test_offline_benchmark_general_knowledge_uses_source_backed_local_fact():
    result = _answer("toshvaqa qansha yil umir koradi")
    assert result.abstained is False
    assert result.generation_mode == "general_knowledge_local_facts"
    assert "150 yil" in result.answer
    assert "toshbaqaning turi" in result.answer.casefold()
    assert result.citations
    assert result.provenance


def test_offline_benchmark_author_motivation_uses_grounded_localized_answer():
    result = _answer("Почему автор создал FINZANJIR?")
    assert result.abstained is False
    assert "автор" in result.answer.casefold() or "муаллиф" in result.answer.casefold()
    assert "bank xatosi" not in result.answer.casefold()


def test_offline_benchmark_kazakh_comparison_is_localized_and_never_returns_cell_definition():
    from finzanjir_ai.orchestration.intent import detect_query_language

    question = "FINZANJIR басқа елдерден несімен ерекшеленеді?"
    result = _answer(question)
    answer = result.answer.casefold()
    assert detect_query_language(question) == "kk"
    assert "жасуша" not in answer
    assert "cell" not in answer
    assert any(term in answer for term in ("жоба", "салыстыру", "дерек", "расталған", "мәлімет"))


def test_fraud_graph_definition_intent_does_not_capture_other_fraud_graph_questions():
    from finzanjir_ai.orchestration.intent import is_fraud_graph_definition_query

    assert is_fraud_graph_definition_query("Fraud Graph nima?")
    assert is_fraud_graph_definition_query("What is Fraud Graph?")
    assert is_fraud_graph_definition_query("Fraud Graph qanday ishlaydi?")
    assert not is_fraud_graph_definition_query("Fraud Graph ma'lumotlari qayerda saqlanadi?")
    assert not is_fraud_graph_definition_query("Fraud Graph ma'lumotlarida nima xato?")
    assert not is_fraud_graph_definition_query("Fraud Graph bo'yicha kim qaror qabul qiladi?")


def test_offline_benchmark_detects_uzbek_signal_questions_as_uzbek():
    from finzanjir_ai.orchestration.intent import detect_query_language

    assert detect_query_language("Shubhali signal nimani anglatadi?") == "uz"
    assert detect_query_language("Signal fuqaroning aybdorligini isbotlaydimi?") == "uz"
