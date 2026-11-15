# FINZANJIR multilingual benchmark expansion — batch 1

## Scope

This batch adds 60 synthetic prompts: 10 each in Uzbek Latin, Uzbek Cyrillic, Russian, English, Kazakh, and Karakalpak. It is the first tranche toward the existing 250-prompt minimum plan; it is not the complete benchmark.

The prompts cover project identity, architecture, signals and Cases, privacy and interbank exchange, fairness, prototype/pilot status, AI evidence behavior, author-name criticism traps, and general-knowledge routing.

## Important boundaries

- The prompt corpus is an evaluation fixture, not a FAQ and not a bank of prewritten answers.
- No new canonical answer is introduced.
- The canonical knowledge corpus v0.6 remains unchanged and read-only.
- Evidence IDs are intentionally empty until each prompt is mapped to exact source records and those records are checked for provenance, status, and relevance.
- Kazakh and Karakalpak wording requires native-speaker review before language-quality claims are made.
- General-knowledge prompts must remain outside FINZANJIR project-document mode.
- Author-name criticism prompts must not trigger agreement or the canonical author-motivation answer.
- This batch does not change runtime routing, retrieval, the API, or deployment behavior.

## Next steps

1. Add the remaining prompt batches to reach at least 250 unique prompts with the planned language distribution.
2. Audit duplicates against the existing 50 live QA prompts, 8 complex-question cases, and 12 decomposition cases.
3. Review each subquestion's evidence mapping against canonical corpus v0.6; do not assign an ID merely because a record is lexically retrieved.
4. Expand adversarial near-miss and multi-part follow-up coverage.
5. Run retrieval diagnostics and report candidate recall separately from grounded evidence recall for every language and task family.
6. Only after evidence mapping and language review, use the benchmark to guide retrieval changes. No runtime behavior change is authorized by this fixture alone.
