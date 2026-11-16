# Preliminary Provider Selection Review

Status: desk review of public vendor documentation, 16 November 2026. This is not a signed contract review, legal opinion, availability confirmation for Uzbekistan, or authorization to send real data.

## Candidate pool

| Candidate | Suitable optional role | Publicly documented data controls | Important limitation |
|---|---|---|---|
| OpenAI API | reasoning critic, response editor | API content is not used for model training by default; abuse-monitoring logs may retain content up to 30 days. Endpoint and feature state-retention differs; Responses API can retain application state for 30 days unless configured otherwise or ZDR applies. | Terms prohibit using outputs to develop competing models, including training material, labels, rankings and other training signals. Runtime use only for FINZANJIR's own general-purpose model roadmap unless written permission or a permitted exception clearly applies. |
| Anthropic Claude API | language specialist, reasoning critic | API feature retention varies; many stateless Messages API features are not retained by default. Zero Data Retention is an organization-level arrangement that must be requested and is feature-specific. | Commercial terms prohibit using the service to build competing products or train competing AI models without express approval. Runtime assistance only; do not use outputs as training targets. |
| Google Gemini API (paid service only) | multilingual language worker, multimodal specialist | Paid Services say prompts and responses are not used to improve Google products; abuse-monitoring logs still apply. ZDR requires specific approval/configuration. Interactions API stores state by default unless `store=false`; Search grounding has separate 30-day retention. | Unpaid Services may use submitted content to improve products and may involve human review. Terms prohibit developing competing models. Do not use free/unpaid quota for FINZANJIR content; runtime only, with stateful features disabled. |
| Mistral API (paid plan) | language, OCR, embeddings and specialist tasks | Mistral documents that API data is not used for model training; ZDR is available on request for supported stateless endpoints on paid plans. Stateful products and file/batch features are outside that ZDR scope. | ZDR is not automatic. Product-specific settings differ; verify that the exact API endpoint is covered before use. Runtime only unless written terms explicitly permit another use. |
| Cohere Model Vault | retrieval/reranking or a dedicated specialist model | Standard and Encrypted Model Vault document ZDR by default and dedicated inference. Standard Vault regions listed are US, EU and Canada; Encrypted Vault is currently US-only. | Dedicated GPU-hour pricing and regional constraints may make this costly or unavailable for the project's needs. Confirm region, model license, price and service contract first. |

## Official documentation reviewed

- OpenAI data controls: https://developers.openai.com/api/docs/guides/your-data
- OpenAI Services Agreement: https://openai.com/policies/services-agreement/
- OpenAI usage policies: https://openai.com/policies/usage-policies/
- Anthropic API data retention: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention
- Anthropic commercial terms: https://www.anthropic.com/legal/commercial-terms
- Google Gemini API terms: https://ai.google.dev/gemini-api/terms
- Google Gemini API ZDR: https://ai.google.dev/gemini-api/docs/zdr
- Google Interactions API storage: https://ai.google.dev/gemini-api/docs/interactions-overview
- Mistral ZDR: https://docs.mistral.ai/admin/monitor-comply/zero-data-retention
- Cohere Model Vault: https://docs.cohere.com/docs/model-vault
- Cohere Encrypted Vault FAQ: https://docs.cohere.com/docs/model-vault/encrypted/faq

## Important training restriction

The five vendors must not be treated as a source of training labels or targets for FINZANJIR's own general-purpose model. OpenAI and Anthropic explicitly restrict using their outputs to build competing models; Google's Gemini API terms also prohibit developing competing models. Do not use their outputs, ratings, rankings, corrections or synthetic examples to train FINZANJIR unless the relevant provider gives clear written permission or the use falls within a documented permitted exception. The training dataset should instead come from independently licensed, public-domain, or explicitly permissioned sources.

Mistral and Cohere must also be checked against the exact product, plan and contract before any output is considered for training. The safe default for every provider is runtime-only.

## Recommended rollout

1. Keep the local FINZANJIR core as the default.
2. Start with one optional paid API for low-risk public text only after the user's explicit approval and a reviewed data-processing agreement.
3. Benchmark the second provider against the first on the same public test set; add a third only if it adds measurable capability.
4. Keep research, language, critic and editor roles separate; call at most two per task.
5. Do not route bank/customer, card, account, identity or complaint data to any provider in this phase.
6. Confirm Uzbekistan availability, data location, DPA, retention, deletion, subprocessors, incident notice, price limits and payment method before enabling any provider.

No provider is selected as a production dependency by this review. The adapter framework remains disabled by default.
