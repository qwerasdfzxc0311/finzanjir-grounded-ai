# FINZANJIR Multilingual Golden Conversations v1

Status: small regression fixture set for intent and policy expectations. These examples are not training data, do not establish answer quality, and are not a substitute for native-speaker review.

## Coverage

The initial fixture set covers Uzbek (uz), Karakalpak (kaa), Kazakh (kk), Russian (ru), and English (en). It includes:
- assistant identity and capability questions;
- general-knowledge questions with spelling variation;
- project-grounded FINZANJIR purpose questions;
- separation of author/source facts from opinion;
- plugin permission inspection and safe continuation.

Each case states the expected intent plus required and prohibited behaviors. Tests currently validate fixture structure and language coverage only; they do not yet run the live intent router or score generated answers.

## Evaluation gate before training

1. Have at least two fluent reviewers per language check wording, dialect fit, grammar, and expected behavior.
2. Add paraphrases, spelling errors, colloquial speech, code-switching, and multi-turn context.
3. Keep training, validation, and test examples separated by source and conversation family; do not duplicate paraphrases across splits.
4. Score intent accuracy, language match, grounded factuality, abstention when evidence is absent, prohibited-action rate, and user-correction recovery.
5. Track false positives and false refusals separately. A safe assistant must not confuse permission to read with permission to write or act externally.
6. Keep author opinions and project source facts in distinct evaluation labels.

No generated answer is approved merely because it matches a fixture string. Review semantic behavior, not exact wording. A failed critical safety expectation blocks release even if aggregate accuracy is high.

## Data governance

These examples contain synthetic, non-personal prompts. Future additions must record source, license/permission, language, reviewer, and split metadata in the governed dataset pipeline. Do not add bank/customer conversations, personal data, secrets, or unlicensed corpora.
