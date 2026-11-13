from finzanjir_ai.orchestration.intent import classify_query_intent, normalize_query_for_intent


def test_misspelled_tortoise_lifespan_is_general_knowledge():
    assert normalize_query_for_intent("toshvaqa qansha yil umir koradi") == "toshbaqa qancha yil umr ko'radi"
    assert classify_query_intent("toshvaqa qansha yil umir koradi") == "general_knowledge"


def test_finzanjir_question_stays_in_project_knowledge():
    assert classify_query_intent("FINZANJIR nima va u nima uchun kerak?") == "project"


def test_assistant_purpose_question_uses_assistant_identity_intent():
    assert classify_query_intent("Sening maqsading nima?") == "assistant_identity"
    assert classify_query_intent("Sen kimsan?") == "assistant_identity"
    assert classify_query_intent("Sening vazifang nima?") == "assistant_identity"


def test_ambiguous_question_does_not_leave_project_rag():
    assert classify_query_intent("Maqsad nima?") == "project"


def test_author_questions_are_classified_separately():
    assert classify_query_intent("FINZANJIR muallifi kim?") == "author"
    assert classify_query_intent("Salamat Smaylov haqida aytib ber") == "author"
    assert classify_query_intent("Muallif nima uchun loyihani boshlagan?") == "author"


def test_author_question_expansion_adds_author_search_hints_only():
    from finzanjir_ai.knowledge.index import build_knowledge_index
    from finzanjir_ai.retrieval.rerank import QueryExpander

    expanded = QueryExpander(build_knowledge_index([])).expand("FINZANJIR muallifi kim?")
    assert any("Salamat Smaylov" in item for item in expanded)
    assert any("tarjimai holi" in item for item in expanded)

    name_expanded = QueryExpander(build_knowledge_index([])).expand(
        "Salamat Smaylov haqida aytib ber"
    )
    assert any("Salamat Smaylov" in item for item in name_expanded)
    assert any("qiziqishlari astronomiya kimyo" in item for item in name_expanded)


def test_finzanjir_overview_is_a_dedicated_intent_not_a_broad_retrieval():
    assert classify_query_intent("FINZANJIR nima?") == "project_overview"
    assert classify_query_intent("FINZANJIR haqida aytib ber") == "project_overview"
    assert classify_query_intent("What is FINZANJIR?") == "project_overview"
    assert classify_query_intent("Что такое FINZANJIR?") == "project_overview"
    assert classify_query_intent("ФИНЗАНЖИР нима?") == "project_overview"
    assert classify_query_intent("FINZANJIR nima uchun bank kartasini bloklaydi?") == "project"
    assert classify_query_intent("FINZANJIR картаны өзі блоктай ала ма?") == "project"


def test_query_language_detection_supports_project_languages_and_uzbek_scripts():
    from finzanjir_ai.orchestration.intent import detect_query_language

    assert detect_query_language("FINZANJIR nima?") == "uz"
    assert detect_query_language("FINZANJIR bank kartasini o‘zi bloklay oladimi?") == "uz"
    assert detect_query_language("ФИНЗАНЖИР нима?") == "uz"
    assert detect_query_language("Что такое FINZANJIR?") == "ru"
    assert detect_query_language("What is FINZANJIR?") == "en"
    assert detect_query_language("FINZANJIR деген не?") == "kk"
    assert detect_query_language("FINZANJIR joybar haqqında qáwip") == "kaa"

def test_uzbek_bank_card_questions_keep_uzbek_language_even_with_technical_terms():
    from finzanjir_ai.orchestration.intent import detect_query_language

    assert detect_query_language("FINZANJIR bank kartasini o'zi bloklay oladimi?") == "uz"
    assert detect_query_language("FINZANJIR bank kartasini o‘zi bloklay oladimi?") == "uz"
    assert detect_query_language("FINZANJIR kartani bloklay oladimi?") == "uz"
    assert classify_query_intent("FINZANJIR bank kartasini o‘zi bloklay oladimi?") == "project"


def test_bank_card_blocking_questions_are_detected_as_specific_authority_queries():
    from finzanjir_ai.orchestration.intent import is_bank_authority_query

    assert is_bank_authority_query("FINZANJIR bank kartasini o‘zi bloklay oladimi?")
    assert is_bank_authority_query("Can FINZANJIR block a bank card?")
    assert is_bank_authority_query("Может ли FINZANJIR заблокировать карту?")
    assert classify_query_intent("FINZANJIR nima?") == "project_overview"
    assert not is_bank_authority_query("FINZANJIR nima?")



def test_citizen_funds_protection_query_uses_specific_local_search_variants():
    from finzanjir_ai.knowledge.index import build_knowledge_index
    from finzanjir_ai.retrieval.rerank import QueryExpander

    expanded = QueryExpander(build_knowledge_index([])).expand(
        "FINZANJIR fuqarolar pulini qanday himoya qiladi?"
    )
    assert any("qonuniy mablag'lari" in value for value in expanded)
    assert any("shubhali pul oqimlarini" in value for value in expanded)
    assert "FINZANJIR moliyaviy xavfsizlik firibgarlik zanjiri" not in expanded
