from finzanjir_ai.orchestration.intent import classify_query_intent, normalize_query_for_intent


def test_misspelled_tortoise_lifespan_is_general_knowledge():
    assert normalize_query_for_intent("toshvaqa qansha yil umir koradi") == "toshbaqa qancha yil umr ko'radi"
    assert classify_query_intent("toshvaqa qansha yil umir koradi") == "general_knowledge"


def test_finzanjir_question_stays_in_project_knowledge():
    assert classify_query_intent("FINZANJIR nima va u nima uchun kerak?") == "project"


def test_assistant_purpose_question_stays_in_project_context():
    assert classify_query_intent("Sening maqsading nima?") == "project"


def test_ambiguous_question_does_not_leave_project_rag():
    assert classify_query_intent("Maqsad nima?") == "project"


def test_author_questions_are_classified_separately():
    assert classify_query_intent("FINZANJIR muallifi kim?") == "author"
    assert classify_query_intent("Salamat Smaylov haqida aytib ber") == "author"
    assert classify_query_intent("Muallif nima uchun loyihani boshlagan?") == "author"
