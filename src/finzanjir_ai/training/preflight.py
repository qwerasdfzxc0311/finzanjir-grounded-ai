from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Sequence

from finzanjir_ai.training.data_governance import AcceptedExample, DatasetReadiness


@dataclass(frozen=True)
class ModelTrainingConfig:
    """Architecture proposal for a small model initialized from random weights."""

    model_id: str = "finzanjir-small-from-scratch"
    tokenizer: str = "byte_bpe"
    vocab_size: int = 16000
    context_length: int = 1024
    hidden_size: int = 512
    layer_count: int = 8
    attention_heads: int = 8
    seed: int = 20261116
    pretrained_weights: bool = False

    def validate(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id is required")
        if self.tokenizer != "byte_bpe":
            raise ValueError("only byte_bpe is currently planned")
        if self.vocab_size < 256:
            raise ValueError("vocab_size must be at least 256")
        if self.context_length < 128:
            raise ValueError("context_length must be at least 128")
        if self.hidden_size < 64 or self.hidden_size % self.attention_heads:
            raise ValueError("hidden_size must be >=64 and divisible by attention_heads")
        if self.layer_count < 1 or self.attention_heads < 1:
            raise ValueError("layer_count and attention_heads must be positive")
        if self.pretrained_weights:
            raise ValueError("FINZANJIR first model must start from random initialization")


@dataclass(frozen=True)
class DatasetSplit:
    name: str
    examples: tuple[AcceptedExample, ...]
    source_ids: tuple[str, ...]
    counts_by_language: dict[str, int]


@dataclass(frozen=True)
class SplitPlan:
    train: DatasetSplit
    validation: DatasetSplit
    test: DatasetSplit
    seed: int
    source_group_count: int


@dataclass(frozen=True)
class TrainingPreflight:
    ready: bool
    reasons: tuple[str, ...]
    total_examples: int
    train_examples: int
    validation_examples: int
    test_examples: int
    validation_missing_languages: tuple[str, ...]
    test_missing_languages: tuple[str, ...]


def _stable_key(seed: int, source_id: str) -> str:
    return sha256(f"{seed}:{source_id}".encode("utf-8")).hexdigest()


def _split_counts(examples: Sequence[AcceptedExample]) -> dict[str, int]:
    return dict(sorted(Counter(item.language for item in examples).items()))


def build_source_grouped_split(
    examples: Iterable[AcceptedExample],
    *,
    seed: int = 20261116,
    validation_fraction: float = 0.10,
    test_fraction: float = 0.10,
) -> SplitPlan:
    """Deterministic split that keeps all records from a source in one partition."""

    rows = tuple(examples)
    if not rows:
        raise ValueError("dataset is empty")
    if not 0 < validation_fraction < 1 or not 0 < test_fraction < 1:
        raise ValueError("validation and test fractions must be between 0 and 1")
    if validation_fraction + test_fraction >= 1:
        raise ValueError("validation and test fractions must sum to less than 1")

    grouped: dict[str, list[AcceptedExample]] = defaultdict(list)
    for item in rows:
        if not item.source_id.strip():
            raise ValueError("every example must have a source_id")
        grouped[item.source_id].append(item)
    if len(grouped) < 3:
        raise ValueError("at least three distinct source groups are required")

    groups = sorted(grouped.items(), key=lambda pair: _stable_key(seed, pair[0]))
    total = len(rows)
    targets = {
        "train": total * (1.0 - validation_fraction - test_fraction),
        "validation": total * validation_fraction,
        "test": total * test_fraction,
    }
    assigned: dict[str, list[AcceptedExample]] = {
        "train": [], "validation": [], "test": [],
    }
    assigned_sources: dict[str, list[str]] = {
        "train": [], "validation": [], "test": [],
    }

    # Seed one distinct source into each partition, then greedily minimize
    # absolute deviation from target example counts. Source groups never split.
    for split_name, (source_id, group_rows) in zip(
        ("train", "validation", "test"), groups[:3]
    ):
        assigned[split_name].extend(group_rows)
        assigned_sources[split_name].append(source_id)

    for source_id, group_rows in groups[3:]:
        candidates = []
        for split_name in ("train", "validation", "test"):
            current = len(assigned[split_name])
            projected = current + len(group_rows)
            deficit_before = targets[split_name] - current
            deficit_after = targets[split_name] - projected
            improvement = abs(deficit_before) - abs(deficit_after)
            candidates.append((improvement, -current, split_name))
        _, _, selected = max(candidates)
        assigned[selected].extend(group_rows)
        assigned_sources[selected].append(source_id)

    def make_split(name: str) -> DatasetSplit:
        selected = tuple(assigned[name])
        return DatasetSplit(
            name=name,
            examples=selected,
            source_ids=tuple(sorted(assigned_sources[name])),
            counts_by_language=_split_counts(selected),
        )

    plan = SplitPlan(
        train=make_split("train"),
        validation=make_split("validation"),
        test=make_split("test"),
        seed=seed,
        source_group_count=len(grouped),
    )
    validate_no_source_leakage(plan)
    if not plan.train.examples or not plan.validation.examples or not plan.test.examples:
        raise ValueError("all three partitions must contain examples")
    return plan


def validate_no_source_leakage(plan: SplitPlan) -> None:
    train = set(plan.train.source_ids)
    validation = set(plan.validation.source_ids)
    test = set(plan.test.source_ids)
    if train & validation or train & test or validation & test:
        raise ValueError("source leakage detected across dataset partitions")


def training_preflight(
    readiness: DatasetReadiness,
    plan: SplitPlan,
    *,
    required_languages: Iterable[str],
    human_split_review_approved: bool = False,
) -> TrainingPreflight:
    required = tuple(dict.fromkeys(required_languages))
    if not required:
        raise ValueError("required_languages must not be empty")

    validation_missing = tuple(
        lang for lang in required if plan.validation.counts_by_language.get(lang, 0) == 0
    )
    test_missing = tuple(
        lang for lang in required if plan.test.counts_by_language.get(lang, 0) == 0
    )
    reasons: list[str] = []
    if not readiness.ready:
        reasons.append("dataset_not_ready")
    if validation_missing:
        reasons.append("validation_language_coverage_incomplete")
    if test_missing:
        reasons.append("test_language_coverage_incomplete")
    if not human_split_review_approved:
        reasons.append("human_split_review_not_approved")

    return TrainingPreflight(
        ready=not reasons,
        reasons=tuple(reasons),
        total_examples=(
            len(plan.train.examples)
            + len(plan.validation.examples)
            + len(plan.test.examples)
        ),
        train_examples=len(plan.train.examples),
        validation_examples=len(plan.validation.examples),
        test_examples=len(plan.test.examples),
        validation_missing_languages=validation_missing,
        test_missing_languages=test_missing,
    )
