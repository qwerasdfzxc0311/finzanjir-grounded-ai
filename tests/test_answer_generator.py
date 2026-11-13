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



class FailedProvider:
    last_status = "provider_failed"

    @staticmethod
    def can_send_text(_text):
        return True

    def generate_json(self, **_kwargs):
        return None


def test_long_grounded_sources_are_explained_with_relevant_extractive_fallback():
    source = (
        "Shubhali signal aniqlanganda, bu holat avtomatik ravishda aybdorlik isboti hisoblanmaydi. "
        "Signal tegishli dalillar va tranzaksiya konteksti bilan tekshiriladi. "
        "Shubhali signal zarur bo'lsa, vakolatli mutaxassis tomonidan ko'rib chiqiladi. "
        "Har qanday bank cheklovi faqat qonuniy asos va bankning vakolatli tartibida qabul qilinadi. "
    ) * 30
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-signal-process",
        concept_id="signal-review-process",
        statement=source,
        score=0.94,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
    ),))

    result = GroundedAnswerGenerator(FailedProvider()).generate(
        "Shubhali signal topilgach nima bo'ladi?", context
    )

    assert result.abstained is False
    assert result.generation_mode == "extractive_grounded_fallback"
    assert result.citations == ("ck-signal-process",)
    assert "dalillar va tranzaksiya konteksti bilan tekshiriladi" in result.answer
    assert "vakolatli mutaxassis tomonidan ko'rib chiqiladi" in result.answer
    assert len(result.answer) < 1600


def test_long_unmatched_source_still_abstains_instead_of_guessing():
    source = ("Astronomiya va sayyoralar haqidagi tasdiqlangan ma'lumot. " * 40)
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-unrelated-long",
        concept_id="unrelated-astronomy",
        statement=source,
        score=0.94,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
    ),))

    result = GroundedAnswerGenerator(FailedProvider()).generate(
        "FINZANJIR bank kartasini qanday himoya qiladi?", context
    )

    assert result.abstained is True
    assert result.generation_mode == "fallback_refused_unmatched_long_source"
    assert "Astronomiya" not in result.answer



def test_extractive_fallback_rejects_citizen_protection_sentences_without_funds():
    irrelevant = (
        "Daromad modelining huquqiy va etik cheklovlari fuqarolar manfaatlarini "
        "himoya qilish tamoyillaridan ustun qo'yilmasligi kerak. "
    )
    relevant = (
        "FINZANJIR fuqarolarning qonuniy mablag'lari va tranzaksiyalariga "
        "asossiz zarar yetmasligini ta'minlashga intiladi. "
    )
    source = (irrelevant * 20) + (relevant * 20)
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-citizen-funds",
        concept_id="citizen-funds-protection",
        statement=source,
        score=0.96,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
        aliases=("fuqarolar mablag'ini himoya qilish",),
    ),))

    result = GroundedAnswerGenerator(FailedProvider()).generate(
        "FINZANJIR fuqarolar pulini qanday himoya qiladi?", context
    )

    assert result.abstained is False
    assert result.generation_mode == "extractive_grounded_fallback"
    assert "qonuniy mablag'lari va tranzaksiyalariga" in result.answer
    assert "Daromad modelining huquqiy" not in result.answer



def test_signal_followup_fallback_prefers_review_process_not_only_general_warning():
    source = (
        "Shubhali signal aniqlanganda, bu holat avtomatik ravishda aybdorlik isboti hisoblanmaydi. "
        "Shubhali signal tegishli dalillar bilan tekshiriladi va Risk natijasi izohlanadi. "
        "Case ochilgach, vakolatli mutaxassis dalillarni ko'rib chiqadi. "
        "Bank o'z vakolatidagi qarorni qonuniy asos va ichki tartib bo'yicha qabul qiladi. "
    ) * 25
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-signal-followup",
        concept_id="signal-followup-process",
        statement=source,
        score=0.95,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
    ),))

    result = GroundedAnswerGenerator(FailedProvider()).generate(
        "Shubhali signal paydo bo'lsa, keyin qaysi bosqichlar bo'ladi va bank nima qiladi?",
        context,
    )

    assert result.abstained is False
    assert result.generation_mode == "extractive_grounded_fallback"
    assert "dalillar bilan tekshiriladi" in result.answer
    assert "vakolatli mutaxassis dalillarni ko'rib chiqadi" in result.answer
    assert "Bank o'z vakolatidagi qarorni" in result.answer
    assert "avtomatik ravishda aybdorlik isboti" not in result.answer
