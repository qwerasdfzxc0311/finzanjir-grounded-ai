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


def test_multi_card_fallback_excludes_unrelated_card_app_and_credential_sentences():
    source = (
        "Fraud Graph karta, hisob, telefon, qurilma va qabul qiluvchi o'rtasidagi bog'lanishlarni ko'rsatadi. "
        "Bog'langan tranzaksiyalar Cross-Match orqali aniqlanib, umumiy pul oqimi tahlil qilinadi. "
        "Mening kartalarim fuqaroga qonuniy integratsiya orqali taqdim etilgan kartalarni ko'rsatadi. "
        "Tizim real bank API, CVV, OTP, parol yoki real pul bilan ishlamaydi. "
    ) * 20
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-multi-card",
        concept_id="multi-card-fraud-graph",
        statement=source,
        score=0.95,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
    ),))

    result = GroundedAnswerGenerator(FailedProvider()).generate(
        "Agar firibgar pulni bir nechta karta orqali o'tkazsa, FINZANJIR buni qanday tushunadi?",
        context,
    )

    assert result.abstained is False
    assert "Fraud Graph" in result.answer
    assert "Cross-Match" in result.answer
    assert "Mening kartalarim" not in result.answer
    assert "CVV, OTP" not in result.answer


def test_funds_protection_fallback_combines_primary_and_supporting_evidence():
    source = (
        "FINZANJIR fuqarolarning qonuniy mablag'lari va tranzaksiyalariga asossiz zarar yetmasligiga yordam beradi. "
        "Shubhali pul oqimlarini aniqlash va tahlil qilish fuqarolar mablag'ini himoya qilish mexanizmlaridan biridir. "
        "Daromad modelining huquqiy va etik cheklovlari fuqarolar manfaatlarini himoya qilish tamoyillaridan ustun qo'yilmasligi kerak. "
    ) * 20
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-funds-protection",
        concept_id="citizen-funds-protection",
        statement=source,
        score=0.96,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
    ),))

    result = GroundedAnswerGenerator(FailedProvider()).generate(
        "FINZANJIR fuqarolar pulini qanday himoya qiladi?",
        context,
    )

    assert result.abstained is False
    assert "qonuniy mablag'lari" in result.answer
    assert "Shubhali pul oqimlarini aniqlash" in result.answer
    assert "Daromad modelining" not in result.answer


def test_signal_process_fallback_orders_only_source_supported_process_stages():
    source = (
        "Bank o'z vakolatidagi qarorni qonuniy asos va vakolatli tartib bo'yicha qabul qiladi. "
        "AuditEvent va feedback natijalari audit izida qayd etiladi. "
        "Case threshold bajarilganda ochiladi. "
        "Risk Score va Threshold qiymati dalillar asosida baholanadi. "
        "Vakolatli mutaxassis Human Review jarayonida dalillarni ko'rib chiqadi. "
        "Dalillar tekshiriladi va tranzaksiya konteksti bilan solishtiriladi. "
        "Shubhali signal aniqlanadi va keyingi tahlil uchun qayd etiladi. "
        "Shubhali signal avtomatik ravishda aybdorlik isboti hisoblanmaydi. "
    ) * 20
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-process-stages",
        concept_id="signal-followup-process",
        statement=source,
        score=0.95,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
    ),))

    result = GroundedAnswerGenerator(FailedProvider()).generate(
        "Shubhali signal topilgandan keyin qanday jarayon bo'ladi va bank nima qiladi?",
        context,
    )

    assert result.abstained is False
    assert result.generation_mode == "extractive_grounded_fallback"
    expected = [
        "Shubhali signal aniqlanadi",
        "Dalillar tekshiriladi",
        "Risk Score va Threshold",
        "Case threshold",
        "Human Review",
        "Bank o'z vakolatidagi qarorni",
        "AuditEvent va feedback",
    ]
    assert all(value in result.answer for value in expected), result.answer
    positions = [result.answer.index(value) for value in expected]
    assert positions == sorted(positions)
    assert "avtomatik aybdorlik isboti" not in result.answer


def test_comparison_question_answers_supported_finzanjir_part_and_withholds_unknown_external_part():
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-finzanjir-purpose",
        concept_id="finzanjir-purpose",
        statement=(
            "FINZANJIR moliyaviy firibgarlik xavflari va shubhali pul oqimlarini "
            "aniqlash hamda tahlil qilishga yo'naltirilgan loyiha."
        ),
        score=0.92,
        provenance=({"source": "synthetic-project-evidence"},),
        evidence={"status": "supported", "verification": "verified"},
    ),))
    result = GroundedAnswerGenerator().generate(
        "FINZANJIRning boshqa davlatlardagi o'xshash tizimlardan farqi nimada?",
        context,
    )
    assert result.abstained is False
    assert result.generation_mode == "comparison_partial_grounded_fallback"
    assert "moliyaviy firibgarlik" in result.answer
    assert "yetarli, tekshirilgan qiyosiy ma'lumot yo'q" in result.answer
    assert "ustun-kamligini taxmin qilib aytmayman" in result.answer
    assert result.citations == ("ck-finzanjir-purpose",)


def test_task_specific_guidance_sets_separate_evidence_boundaries():
    from finzanjir_ai.answer.generator import _task_specific_guidance

    comparison = _task_specific_guidance("comparison")
    assert "boshqa davlatlar" in comparison
    assert "ustunligini" in comparison
    assert "tasdiqlangan qismni javobsiz qoldirishga sabab bo'lmasin" in comparison

    status = _task_specific_guidance("status_audit")
    assert "amaldagi prototip" in status
    assert "reja" in status
    assert "ishlayotganini isbotlamaydi" in status

    architecture = _task_specific_guidance("architecture")
    assert "konseptual arxitekturani" in architecture.casefold()
    assert "production tizimi" in architecture.casefold()


def test_uzbek_cyrillic_comparison_uses_the_same_safe_partial_answer_policy():
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck-finzanjir-purpose-cyrl",
        concept_id="finzanjir-purpose",
        statement=(
            "FINZANJIR молиявий фирибгарлик хавфлари ва шубҳали пул оқимларини "
            "аниқлаш ҳамда таҳлил қилишга йўналтирилган лойиҳа."
        ),
        score=0.92,
        provenance=({"source": "synthetic-project-evidence"},),
        evidence={"status": "supported", "verification": "verified"},
    ),))
    result = GroundedAnswerGenerator().generate(
        "FINZANJIR бошқа давлатлардаги ўхшаш тизимлардан нимаси билан фарқ қилади?",
        context,
    )
    assert result.abstained is False
    assert result.generation_mode == "comparison_partial_grounded_fallback"
    assert "FINZANJIR" in result.answer
    assert "Taqqoslash chegarasi" in result.answer
    assert result.citations == ("ck-finzanjir-purpose-cyrl",)


def test_comparison_fallback_skips_unrelated_grounded_records_and_keeps_project_definition():
    unrelated = GroundedContextItem(
        record_id="ck-unrelated-weather",
        concept_id="weather",
        statement="Ob-havo ma'lumotlari har kuni yangilanadi va harorat o'zgaradi.",
        score=0.99,
        provenance=({"source": "synthetic-unrelated"},),
        evidence={"status": "supported", "verification": "verified"},
    )
    relevant = GroundedContextItem(
        record_id="ck-project-definition",
        concept_id="project-purpose",
        statement=(
            "FINZANJIR moliyaviy firibgarlik xavflarini aniqlash va tahlil qilishga "
            "yo'naltirilgan loyiha."
        ),
        score=0.91,
        provenance=({"source": "synthetic-project-evidence"},),
        evidence={"status": "supported", "verification": "verified"},
    )
    result = GroundedAnswerGenerator().generate(
        "FINZANJIRning boshqa davlatlardagi o'xshash tizimlardan farqi nimada?",
        GroundedContext(items=(unrelated, relevant)),
    )
    assert result.generation_mode == "comparison_partial_grounded_fallback"
    assert "moliyaviy firibgarlik" in result.answer
    assert "Ob-havo" not in result.answer
    assert result.citations == ("ck-project-definition",)


def test_comparison_fallback_does_not_turn_irrelevant_context_into_an_answer():
    unrelated = GroundedContextItem(
        record_id="ck-unrelated-weather-only",
        concept_id="weather",
        statement="Ob-havo ma'lumotlari har kuni yangilanadi va harorat o'zgaradi.",
        score=0.99,
        provenance=({"source": "synthetic-unrelated"},),
        evidence={"status": "supported", "verification": "verified"},
    )
    result = GroundedAnswerGenerator().generate(
        "FINZANJIRning boshqa davlatlardagi o'xshash tizimlardan farqi nimada?",
        GroundedContext(items=(unrelated,)),
    )
    assert result.abstained is True
    assert result.generation_mode == "comparison_no_relevant_evidence"
    assert result.citations == ()
    assert "Ob-havo" not in result.answer


def test_provider_failure_rejects_unrelated_short_kazakh_record_for_comparison():
    unrelated = (
        "Жасуша — тірі ағзалардың негізгі құрылымдық және функционалдық бірлігі. "
        "Әртүрлі ағзаларда жасушалар құрылысы мен қызметі бойынша ерекшеленеді."
    )
    context = GroundedContext(items=(GroundedContextItem(
        record_id="ck_001693",
        concept_id="cell_biology",
        statement=unrelated,
        score=0.94,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
    ),))

    result = GroundedAnswerGenerator(FailedProvider()).generate(
        "FINZANJIR басқа елдерден несімен ерекшеленеді?", context
    )

    assert result.abstained is True
    assert result.generation_mode == "comparison_no_relevant_evidence"
    assert result.citations == ()
    assert "Жасуша" not in result.answer
    assert "тікелей қатысты расталған дерек" in result.answer


def test_provider_failure_comparison_uses_project_definition_and_localizes_kazakh():
    unrelated = GroundedContextItem(
        record_id="ck_001693",
        concept_id="cell_biology",
        statement="Жасуша — тірі ағзалардың негізгі құрылымдық және функционалдық бірлігі.",
        score=0.99,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
    )
    relevant = GroundedContextItem(
        record_id="project-purpose",
        concept_id="finzanjir-purpose",
        statement="FINZANJIR қаржылық алаяқтық тәуекелдерін анықтау мен талдауға бағытталған жоба.",
        score=0.91,
        provenance=({"source": "canonical-v0.6"},),
        evidence={"status": "supported"},
    )
    result = GroundedAnswerGenerator(FailedProvider()).generate(
        "FINZANJIR басқа елдерден несімен ерекшеленеді?",
        GroundedContext(items=(unrelated, relevant)),
    )
    assert result.abstained is False
    assert result.generation_mode == "comparison_partial_grounded_fallback"
    assert result.citations == ("project-purpose",)
    assert "Жасуша" not in result.answer
    assert "Салыстыру шегі" in result.answer
    assert result.answer.startswith("Жоба дереккөздерінде FINZANJIR туралы расталған мәліметтер:")
