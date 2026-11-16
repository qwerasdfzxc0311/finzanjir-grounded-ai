"""Small auditable local reasoning primitives.

These operators are deliberately narrow. They do not claim open-domain
understanding or causal discovery; callers must provide typed facts and rules.
"""
from __future__ import annotations

import ast
import operator
from dataclasses import dataclass
from typing import Iterable


class ReasoningInputError(ValueError):
    """Raised when an expression or inference rule is outside the safe subset."""


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_EXPRESSION_LENGTH = 160
_MAX_ABS_VALUE = 10**15


def safe_calculate(expression: str) -> int | float:
    """Evaluate a bounded arithmetic expression without eval(), names or calls."""
    source = str(expression).strip()
    if not source or len(source) > _MAX_EXPRESSION_LENGTH:
        raise ReasoningInputError("expression is empty or too long")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ReasoningInputError("invalid arithmetic expression") from exc

    def visit(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
            if abs(value) > _MAX_ABS_VALUE:
                raise ReasoningInputError("numeric value exceeds the safety bound")
            return value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            result = _UNARY_OPERATORS[type(node.op)](visit(node.operand))
        elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 8:
                raise ReasoningInputError("exponent exceeds the safety bound")
            result = _BINARY_OPERATORS[type(node.op)](left, right)
        else:
            raise ReasoningInputError("unsupported expression element")
        if not isinstance(result, (int, float)) or abs(result) > _MAX_ABS_VALUE:
            raise ReasoningInputError("calculation result exceeds the safety bound")
        return result

    try:
        result = visit(tree)
    except (ZeroDivisionError, OverflowError) as exc:
        raise ReasoningInputError("arithmetic operation is undefined or too large") from exc
    if isinstance(result, float) and not result.is_integer():
        return result
    return int(result)


@dataclass(frozen=True)
class Fact:
    """A typed, source-linked fact used as an inference premise."""

    subject: str
    relation: str
    object: str
    source_id: str

    def __post_init__(self) -> None:
        if not all(str(value).strip() for value in (self.subject, self.relation, self.object, self.source_id)):
            raise ReasoningInputError("facts require subject, relation, object and source_id")


@dataclass(frozen=True)
class Rule:
    """A simple one-premise implication with explicit provenance."""

    premise_relation: str
    premise_object: str
    conclusion_relation: str
    conclusion_object: str
    rule_id: str

    def __post_init__(self) -> None:
        if not all(str(value).strip() for value in (
            self.premise_relation, self.premise_object,
            self.conclusion_relation, self.conclusion_object, self.rule_id,
        )):
            raise ReasoningInputError("rules require complete fields")


@dataclass(frozen=True)
class Inference:
    fact: Fact
    premise_source_ids: tuple[str, ...]
    rule_id: str


def infer_facts(facts: Iterable[Fact], rules: Iterable[Rule]) -> tuple[Inference, ...]:
    """Apply explicit one-step rules; never invent premises or recurse silently."""
    known = tuple(facts)
    output: list[Inference] = []
    seen: set[tuple[str, str, str, str]] = set()
    for rule in rules:
        for premise in known:
            if premise.relation != rule.premise_relation or premise.object != rule.premise_object:
                continue
            key = (premise.subject, rule.conclusion_relation, rule.conclusion_object, rule.rule_id)
            if key in seen:
                continue
            seen.add(key)
            output.append(Inference(
                fact=Fact(
                    subject=premise.subject,
                    relation=rule.conclusion_relation,
                    object=rule.conclusion_object,
                    source_id=f"inference:{rule.rule_id}",
                ),
                premise_source_ids=(premise.source_id,),
                rule_id=rule.rule_id,
            ))
    return tuple(output)


def compare_numeric_values(left: float, right: float) -> str:
    """Compare two explicit numeric values without assigning unstated units."""
    if left < right:
        return "less"
    if left > right:
        return "greater"
    return "equal"
