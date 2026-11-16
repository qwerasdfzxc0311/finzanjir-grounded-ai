from dataclasses import dataclass

from finzanjir_ai.answer.local_composer import compose_local_grounded_answer


@dataclass
class Evidence:
    record_id: str
    statement: str
    aliases: tuple[str, ...] = ()
    score: float = 0.5


def test_composer_selects_relevant_grounded_statements_and_citations():
    items = [
        Evidence(
            "risk-1",
            "FINZANJIR shubhali pul oqimlarini tahlil qilishga qaratilgan loyiha.",
            ("moliyaviy xavfsizlik",),
            0.9,
        ),
        Evidence(
            "risk-2",
            "Shubhali signal qo'shimcha tekshiruv talab qilishi mumkin.",
            ("signal", "tekshiruv"),
            0.7,
        ),
        Evidence(
            "unrelated",
            "Astronomiya sayyoralar va yulduzlarni o'rganadi.",
            ("kosmos",),
            1.0,
        ),
    ]

    result = compose_local_grounded_answer(
        "FINZANJIR shubhali pul oqimlarini qanday tahlil qiladi?",
        items,
        language="uz",
    )

    assert result.abstained is False
    assert result.generation_mode == "local_composed_grounded"
    assert "FINZANJIR shubhali pul oqimlarini tahlil qilishga qaratilgan loyiha." in result.answer
    assert "Astronomiya" not in result.answer
    assert "risk-1" in result.citations
    assert "risk-2" in result.citations
    assert "unrelated" not in result.citations


def test_composer_uses_aliases_but_preserves_original_source_text():
    item = Evidence(
        "protection-1",
        "Loyiha xavf belgilarini tekshirishga ko'maklashadi.",
        ("moliyaviy himoya", "fuqarolar xavfsizligi"),
    )
    result = compose_local_grounded_answer(
        "moliyaviy himoya",
        [item],
        language="kaa",
    )
    assert result.abstained is False
    assert result.answer.startswith("Sorawǵa tiyisli joybardıń tastıyıqlanǵan maǵlıwmatları:")
    assert item.statement in result.answer
    assert result.citations == ("protection-1",)


def test_composer_abstains_instead_of_inventing_when_no_evidence_matches():
    result = compose_local_grounded_answer(
        "Quyosh tizimidagi eng katta sayyora qaysi?",
        [Evidence("finance-1", "FINZANJIR moliyaviy xavflarni tahlil qiladi.")],
    )
    assert result.abstained is True
    assert result.answer == ""
    assert result.citations == ()


def test_composer_deduplicates_identical_source_statements():
    statement = "FINZANJIR moliyaviy firibgarlik xavfini tahlil qiladi."
    result = compose_local_grounded_answer(
        "FINZANJIR moliyaviy firibgarlik xavfini qanday tahlil qiladi?",
        [
            Evidence("a", statement, score=0.5),
            Evidence("b", statement, score=0.8),
        ],
    )
    assert result.answer.count(statement) == 1
    assert len(result.citations) == 1
