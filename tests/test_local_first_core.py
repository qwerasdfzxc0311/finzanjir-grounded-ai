import pytest

from finzanjir_ai.language.normalization import (
    character_ngrams,
    normalize_multilingual_text,
)
from finzanjir_ai.reasoning.core import (
    Fact,
    ReasoningInputError,
    Rule,
    compare_numeric_values,
    infer_facts,
    safe_calculate,
)


def test_normalizer_handles_common_typos_apostrophes_and_unicode():
    assert normalize_multilingual_text("Toshvaqa qansha yil umir ko‘radi?") == "toshbaqa qancha yil umr ko'radi"
    assert normalize_multilingual_text("  SALOM\u200b   DUNYO! ") == "salom dunyo"


def test_normalizer_accepts_reviewed_language_aliases_without_mutating_original():
    original = "Qaraqalpaqsha sóyle"
    normalized = normalize_multilingual_text(original, aliases={"sóyle": "soyle"})
    assert normalized == "qoraqalpoqcha soyle"
    assert original == "Qaraqalpaqsha sóyle"


def test_character_ngrams_are_deterministic_and_typo_tolerant():
    first = character_ngrams("firibgarlik")
    second = character_ngrams("firibgarlik")
    near = set(character_ngrams("firibgarlik"))
    typo = set(character_ngrams("firibgarlik"))
    assert first == second
    assert near & typo
    with pytest.raises(ValueError):
        character_ngrams("text", min_n=5, max_n=2)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 * 4", 14),
        ("(10 - 4) / 2", 3),
        ("2 ** 3", 8),
        ("-5 + 2", -3),
    ],
)
def test_safe_calculator_supports_bounded_arithmetic(expression, expected):
    assert safe_calculate(expression) == expected


@pytest.mark.parametrize("expression", ["__import__('os').system('id')", "x + 2", "1 / 0", "2 ** 99"])
def test_safe_calculator_rejects_calls_names_and_unsafe_operations(expression):
    with pytest.raises(ReasoningInputError):
        safe_calculate(expression)


def test_rule_inference_keeps_premise_and_rule_provenance():
    facts = [Fact("A", "has_property", "verified", "source-17")]
    rules = [Rule("has_property", "verified", "may_be_classified", "eligible", "rule-3")]
    results = infer_facts(facts, rules)
    assert len(results) == 1
    assert results[0].fact.subject == "A"
    assert results[0].fact.relation == "may_be_classified"
    assert results[0].premise_source_ids == ("source-17",)
    assert results[0].rule_id == "rule-3"


def test_rule_inference_does_not_infer_without_explicit_premise():
    assert infer_facts([], [Rule("is", "known", "implies", "answer", "rule-1")]) == ()


def test_numeric_comparison_does_not_assume_units():
    assert compare_numeric_values(3, 4) == "less"
    assert compare_numeric_values(4, 3) == "greater"
    assert compare_numeric_values(4, 4) == "equal"
