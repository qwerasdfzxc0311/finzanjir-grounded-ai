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


def test_offline_benchmark_bank_neutrality_is_not_abstained_without_reason():
    result = _answer("FINZANJIR banklarga qarshimi?")
    assert result.abstained is False
    assert any(word in result.answer.casefold() for word in ("bank", "hamkor", "qarshi"))
    assert "banklarni aybl" not in result.answer.casefold()


def test_offline_benchmark_signal_is_not_presented_as_guilt():
    result = _answer("Signal fuqaroning aybdorligini isbotlaydimi?")
    assert "aybdorlik isboti emas" in result.answer.casefold() or "aybdorligini isbotlamaydi" in result.answer.casefold()


def test_offline_benchmark_case_answer_excludes_unrelated_security_attack_terms():
    result = _answer("Case nima uchun ochiladi?")
    assert "case" in result.answer.casefold()
    assert "idor" not in result.answer.casefold()
    assert "bola" not in result.answer.casefold()


def test_offline_benchmark_fraud_graph_is_an_explanation_not_alias_list():
    result = _answer("Fraud Graph nima?")
    answer = result.answer.casefold()
    assert "fraud graph: [" not in answer
    assert "fraud graph" in answer
    assert any(term in answer for term in ("karta", "tranzaksiya", "bog'lan", "aloqa"))


def test_offline_benchmark_fin_recovery_answer_excludes_biology_contamination():
    result = _answer("FIN-RECOVERY nima vazifani bajaradi?")
    answer = result.answer.casefold()
    assert "to'qima" not in answer
    assert "hujayra" not in answer
    assert "recovery" in answer or "tiklash" in answer or "hodisadan keyin" in answer


def test_offline_benchmark_c_model_answer_is_about_interbank_signal_architecture():
    result = _answer("FINZANJIRning C modeli qanday ishlaydi?")
    answer = result.answer.casefold()
    assert "atmos" not in answer
    assert any(term in answer for term in ("banklararo", "banklar o'rtasida", "signallar", "ma'lumot almash"))


def test_offline_benchmark_sixteen_layer_question_mentions_layer_architecture():
    result = _answer("FINZANJIRning 16 qatlamli arxitekturasi nimani anglatadi?")
    answer = result.answer.casefold()
    assert "qatlam" in answer or "layer" in answer
    assert "16" in answer or "o'n olti" in answer


def test_offline_benchmark_general_knowledge_does_not_fabricate_project_answer():
    result = _answer("toshvaqa qansha yil umir koradi")
    assert result.abstained is True
    assert "finzanjir" not in result.answer.casefold()


def test_offline_benchmark_author_motivation_uses_grounded_localized_answer():
    result = _answer("Почему автор создал FINZANJIR?")
    assert result.abstained is False
    assert "автор" in result.answer.casefold() or "муаллиф" in result.answer.casefold()
    assert "bank xatosi" not in result.answer.casefold()


def test_offline_benchmark_kazakh_comparison_never_returns_cell_definition():
    result = _answer("FINZANJIR басқа елдерден несімен ерекшеленеді?")
    answer = result.answer.casefold()
    assert "жасуша" not in answer
    assert "cell" not in answer
