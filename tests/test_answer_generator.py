from finzanjir_ai.answer.generator import GroundedAnswerGenerator
from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextItem


def test_grounded_answer_uses_context_and_emits_citations():
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-1", concept_id="c1",
        statement="Fraud signal requires supporting evidence.",
        score=0.9, provenance=({"source": "source-a"},),
        evidence={"status": "supported"},
    ),))
    result = GroundedAnswerGenerator().generate("Why is evidence required?", context)
    assert result.abstained is False
    assert result.confidence > 0
    assert "Fraud signal requires supporting evidence." in result.answer
    assert result.citations == ("ck-1",)


def test_grounded_answer_abstains_without_grounded_context():
    result = GroundedAnswerGenerator().generate(
        "What is the answer?", GroundedContext(items=())
    )
    assert result.abstained is True
    assert result.confidence == 0
    assert result.citations == ()
    assert "does not contain enough verified evidence" in result.answer.casefold()


def test_grounded_answer_abstains_when_context_has_no_supported_evidence():
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-observed", concept_id="c1",
        statement="Observed but not authoritative evidence.",
        score=0.95, provenance=({"source": "source-a"},),
        evidence={"status": "observed"},
    ),))
    result = GroundedAnswerGenerator().generate("Why is evidence required?", context)
    assert result.abstained is True
    assert result.confidence < GroundedAnswerGenerator.ABSTENTION_THRESHOLD


def _false_positive_negative_context():
    return GroundedContext(items=(
        GroundedContextItem(
            record_id="project_0003",
            concept_id="finzanjir_false_positive_negative",
            statement=(
                "False positive — qonuniy operatsiyani xato ravishda shubhali deb belgilash; "
                "false negative — haqiqiy xavfni aniqlamay o'tkazib yuborish. "
                "Ikkala xato ham birgalikda baholanishi kerak."
            ),
            score=0.9,
            provenance=({"source": "author-confirmed-project-principle"},),
            evidence={"status": "project_source", "verification": "author_confirmed"},
        ),
        GroundedContextItem(
            record_id="author_0004",
            concept_id="author_motivation_finzanjir",
            statement="Muallif motivatsiyasi haqida uzun matn. " * 100,
            score=0.8,
            provenance=({"source": "author-profile"},),
            evidence={"status": "project_source", "verification": "author_confirmed"},
        ),
    ))


def test_false_positive_negative_question_uses_concise_project_principle_fallback():
    result = GroundedAnswerGenerator().generate(
        "False positive va false negative nima uchun muhim?",
        _false_positive_negative_context(),
    )
    assert result.abstained is False
    assert result.generation_mode == "project_principle_deterministic_fallback"
    assert result.citations == ("project_0003",)
    assert "False positive" in result.answer
    assert "Muallif motivatsiyasi" not in result.answer


def test_colloquial_false_positive_negative_aliases_use_same_fallback():
    result = GroundedAnswerGenerator().generate(
        "Fals F va fals N nimani anglatadi?",
        _false_positive_negative_context(),
    )
    assert result.abstained is False
    assert result.citations == ("project_0003",)
    assert "false negative" in result.answer


def test_provider_failure_does_not_return_untranslated_project_statements():
    result = GroundedAnswerGenerator().generate(
        "Что означает false positive и false negative?",
        _false_positive_negative_context(),
    )
    assert result.abstained is True
    assert result.generation_mode == "language_safe_abstention"
    assert "Подходящий материал проекта найден" in result.answer
    assert "Loyiha bilimlar bazasi" not in result.answer


def _bank_authority_context():
    return GroundedContext(items=(
        GroundedContextItem(
            record_id="project_0004",
            concept_id="finzanjir_bank_authority_boundary",
            statement=(
                "FINZANJIR bank kartasini o'zi bloklamasligi, bank qarorini o'zgartirmasligi "
                "va bankning vakolatli jarayonlarini almashtirmasligi kerak."
            ),
            score=0.95,
            provenance=({"source": "author-confirmed-project-principle"},),
            evidence={"status": "project_source", "verification": "author_confirmed"},
        ),
        GroundedContextItem(
            record_id="project_0007",
            concept_id="finzanjir_data_minimization_security",
            statement="FINZANJIR minimal ma'lumot bilan ishlashi kerak.",
            score=0.92,
            provenance=({"source": "author-confirmed-project-principle"},),
            evidence={"status": "project_source", "verification": "author_confirmed"},
        ),
    ))


def test_bank_card_authority_question_uses_only_the_relevant_principle():
    result = GroundedAnswerGenerator().generate(
        "FINZANJIR bank kartasini o‘zi bloklay oladimi?",
        _bank_authority_context(),
    )
    assert result.abstained is False
    assert result.generation_mode == "bank_authority_localized"
    assert result.citations == ("project_0004",)
    assert "bank kartasini o'zi bloklamaydi" in result.answer
    assert "minimal ma'lumot" not in result.answer


def test_bank_card_authority_answer_is_localized():
    cases = (
        ("Can FINZANJIR block a bank card?", "No. FINZANJIR does not block"),
        ("Может ли FINZANJIR заблокировать карту?", "Нет. FINZANJIR не блокирует"),
        ("FINZANJIR деген не? FINZANJIR картаны бұғаттай ала ма?", "Жоқ. FINZANJIR"),
    )
    for query, expected in cases:
        result = GroundedAnswerGenerator().generate(query, _bank_authority_context())
        assert result.generation_mode == "bank_authority_localized"
        assert result.citations == ("project_0004",)
        assert expected.casefold() in result.answer.casefold()
