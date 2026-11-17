# FINZANJIR Training Data Governance

Status: dataset intake and readiness checks only. No neural model is trained by this module.

## Data that may enter the staging dataset

Every example must have:
- input and target text;
- one supported language tag (Uzbek Latin/Cyrillic, Karakalpak Latin/Cyrillic, Kazakh, Russian or English);
- task type;
- stable source ID and traceable HTTPS or local source URI;
- verified source status;
- an explicit training-compatible license;
- an explicit data class of `public` or `licensed_nonpersonal`;
- a source type of `public_domain`, `licensed_corpus` or `author_provided`.
Unknown source types and `hosted_model_output` are rejected.

The initial license allow-list is deliberately narrow: CC0-1.0, CC-BY-4.0, public domain, author-granted permission, and custom training grants. Author-granted and custom grants require a permission reference. Attribution and other license obligations must be preserved in the manifest and any downstream model card.

## Rejected data

The builder rejects:
- unknown, unapproved or unverifiable licenses;
- unknown or non-approved data classes;
- personal or financial data;
- unverified or untraceable sources;
- common sensitive identifiers detected by a conservative screening layer;
- duplicate input/target pairs.

The identifier scanner is not complete PII detection. A human data steward must inspect the source and the complete example. Real bank/customer records, card numbers, credentials, account data, private messages and confidential banking records must never be used for model training.

## Dataset readiness

The builder exports provenance-preserving JSONL for a staging process and a manifest with per-language counts and rejection reasons. It does not write to disk, start training, or enable a model.

Training readiness requires:
1. adequate examples for every required language;
2. zero unresolved rejected examples;
3. human reviewer approval;
4. documented rights and attribution for every source;
5. a separate privacy, safety and quality review.

The initial minimum-size threshold is supplied by the evaluator rather than hard-coded. Evaluation data must be held out from training and must include author-reviewed examples for spelling, dialect, multi-turn context, factuality, reasoning and uncertainty.

## Future model-training gate

Only after the dataset is approved should the project select a tokenizer, architecture, training framework, compute budget and evaluation plan. A small from-scratch model is a research milestone; it is not equivalent to a frontier assistant. The non-neural offline core must remain useful if the model is absent.


## Hosted-model output restriction

Do not treat outputs, labels, rankings, corrections, preferences or synthetic examples from hosted model APIs as training targets for FINZANJIR's general-purpose model by default. Some major providers explicitly prohibit using their outputs to develop competing models. The intake builder therefore rejects `hosted_model_output` and unknown source types. A provider-specific written permission or clearly documented contractual exception would need a separate legal review before changing this gate.


## Hosted-model output restriction

Do not treat outputs, labels, rankings, corrections, preferences or synthetic examples from hosted model APIs as training targets for FINZANJIR's general-purpose model by default. The intake builder rejects `hosted_model_output` and unknown source types. This is a conservative project-wide default; it does not claim that every provider has identical terms.

### Provider-specific basis checked on 2026-11-17

- **OpenAI API:** the OpenAI Services Agreement, effective 2026-01-01, section 3.3(e), prohibits using Output to develop AI models that compete with OpenAI, subject to its defined Permitted Exceptions. One exception is narrowly for models primarily intended to categorize, classify or organize data, provided they are not distributed or made commercially available to third parties. A general-purpose FINZANJIR assistant is not assumed to fit that exception.
- **Gemini API:** the Gemini API Additional Terms, effective 2026-03-23, prohibit using the service to develop models that compete with Gemini API or Google AI Studio, and prohibit reverse engineering or extracting model components such as parameter weights.

Official terms:
- OpenAI Services Agreement: https://openai.com/policies/services-agreement/
- Gemini API Additional Terms: https://ai.google.dev/gemini-api/terms

These terms are product- and account-specific and may change. Before any exception, confirm the exact service, account type, governing agreement, effective version, and written provider permission with legal review. A written exception must not be inferred from ownership of the generated text. Until that review is complete, keep hosted-model outputs out of FINZANJIR's general-model training corpus.
