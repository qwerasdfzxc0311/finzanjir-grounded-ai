from finzanjir_ai.answer.generator import GroundedAnswerGenerator
from finzanjir_ai.retrieval.grounding import GroundedContext, GroundedContextItem


class FakeProvider:
    def __init__(self, response):
        self.response = response
        self.last_prompt = None

    def generate_json(self, **kwargs):
        self.last_prompt = kwargs
        return self.response


def _context():
    return GroundedContext(items=(
        GroundedContextItem(
            record_id="ck-protect",
            concept_id="concept-protect",
            statement="FINZANJIR moliyaviy xavflarni aniqlash va fuqarolar mablag'ini himoya qilishga yordam beradi.",
            score=0.92,
            provenance=({"source": "canonical-v0.6"},),
            evidence={"status": "supported"},
            aliases=("moliyaviy xavfsizlik", "firibgarlikdan himoya"),
        ),
        GroundedContextItem(
            record_id="ck-human",
            concept_id="concept-human",
            statement="Muhim holatlar vakolatli mutaxassis tomonidan ko'rib chiqiladi.",
            score=0.84,
            provenance=({"source": "canonical-v0.6"},),
            evidence={"status": "supported"},
        ),
    ))


def test_answer_generator_uses_model_for_natural_long_form_grounded_answer():
    provider = FakeProvider({
        "answer": "FINZANJIR moliyaviy xavf belgilarini aniqlashga yordam beradi. "
                  "Shubhali holatlar dalillar bilan tekshiriladi va zarur bo'lsa mutaxassisga yuboriladi.",
        "used_record_ids": ["ck-protect", "not-in-context"],
        "evidence_gaps": [],
    })
    result = GroundedAnswerGenerator(provider).generate("Bu tizim pulimni qanday himoya qiladi?", _context())
    assert result.abstained is False
    assert "moliyaviy xavf belgilarini" in result.answer
    assert result.citations == ("ck-protect",)
    assert "faqat berilgan tasdiqlangan loyiha dalillari" in provider.last_prompt["system"].casefold()


def test_answer_generator_fallback_keeps_source_statements_readable():
    result = GroundedAnswerGenerator().generate("FINZANJIR nima qiladi?", _context())
    assert result.abstained is False
    assert "1. FINZANJIR" in result.answer
    assert "\n\n2. Muhim holatlar" in result.answer
