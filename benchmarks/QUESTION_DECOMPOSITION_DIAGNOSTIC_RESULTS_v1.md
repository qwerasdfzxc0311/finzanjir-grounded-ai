# FINZANJIR question decomposition diagnostic — results v1

Date: 2026-11-14
Corpus: canonical v0.6 (read-only)
PR: https://github.com/qwerasdfzxc0311/finzanjir-grounded-ai/pull/139

## Measurements

- 12 synthetic cases across Uzbek Latin/Cyrillic, Russian, English, Kazakh and Karakalpak.
- 29 subquestions.
- Domain routing: 12/12 correct (100%) for the expected project-domain route.
- Separate task-type baseline: 12/12 correct (100%) on the same synthetic fixture.
- Eligible grounded candidates for known/partial internal subquestions: 44.
- Manual-review candidates for evidence-review-only subquestions: 20.
- Internal corpus collision candidates for unknown external or production scope: 225. These are not answer evidence.

The task-type and cross-lingual recall scores are development-fixture results, not held-out generalization scores. The task classifier and cross-lingual bridge are not yet connected to the production answer path.

## Findings

1. Domain routing and task-type classification are different tasks. The previous diagnostic incorrectly compared the domain router output ("project") with task labels ("comparison", "architecture", etc.). That metric was removed.
2. The current task-type baseline separates comparison, architecture, process, status audit, reason, and definition patterns across the supported scripts/languages. The fixture and paraphrase tests pass, but the baseline still needs unseen, ambiguous and multi-intent tests.
3. Uzbek architecture queries can retrieve useful source records such as `ck_003257` (conceptual architecture and data flow), `ck_003252` (project purpose and case model), and `ck_003254` (platform functions and risk-score boundaries).
4. Cross-language retrieval remains weak. Russian, Kazakh and Karakalpak broad project questions can return author-profile records instead of project architecture. An English FINZANJIR capabilities question returned unrelated IBM material among its top candidates. This is a retrieval/language-bridge defect, not a task-classification success.
5. Several unknown-external and production-unconfirmed subquestions returned lexical collisions from the internal corpus. The revised runner now records these as collision candidates and explicitly excludes them from eligible answer evidence.
6. Some architecture records describe proposed/future bank integration, not current APK functionality. Answers must preserve this distinction.

## Next steps

1. Manually review the 44 eligible and 20 review-only candidate records; curate expected evidence IDs only where source relevance and status are confirmed.
2. Expand a held-out test set with paraphrases, colloquial Uzbek, spelling variants, mixed-language queries, multi-intent questions, and negative examples.
3. Improve multilingual retrieval further: the vocabulary bridge helps Russian/Karakalpak and partially Kazakh, but Uzbek retrieval and Kazakh grounding remain weak. Expand and validate the concept/alias bridge against unseen questions; do not introduce a large embedding model or mandatory API.
4. Add evidence coverage per subquestion and a grounded partial-answer contract.
5. Integrate the task classifier only after held-out tests pass; keep domain routing separate.
6. Browser/live answer testing comes after the retrieval and grounding changes are reviewed.

## Safety

- Canonical v0.6 was not modified.
- No bank/customer/card data was used.
- No external API, model provider, deployment secret, or bank integration was touched.
- PR remains draft/open and unmerged.


## Candidate provenance requiring manual review

The bridge surfaced additional potentially relevant records that are not yet in the curated expected-evidence set:

- `ck_000063` and `ck_000001`: source-derived from `16.10.12index.html`, with provenance pointing to `knowledge/source_knowledge.json` and `knowledge/knowledge_corpus.json`. Their statements cover conceptual architecture, project purpose, data flow, and the boundary that bank integration is future/proposed. Confirm the underlying source/version before adding them to the gold evidence set.
- `ck_000472`, `ck_000473`, `ck_000474`, `ck_000476`: source-derived records from `knowledge/deep_domain_ontology_candidate.json`, but their source_id/section fields are empty. They may help cross-language retrieval, but require provenance review before being treated as authoritative.
- `src3_000107` and `src3_000108`: V14 PDF records with status `proposal_or_future`. They explicitly describe bank/PSP integration as a future model, not current APK functionality.

The Kazakh query returned other grounded FINZANJIR records, but none of the currently curated expected IDs passed the grounding output. This is not proof that no useful evidence was found; it means the expected set and candidate provenance need review before drawing a final language-level quality conclusion.
