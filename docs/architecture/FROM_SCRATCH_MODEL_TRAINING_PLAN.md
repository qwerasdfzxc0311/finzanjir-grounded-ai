# FINZANJIR From-Scratch Model: Training and Evaluation Plan

Status: preflight and split planning only. No model architecture has been trained and no training job is enabled.

## Design principle

The first FINZANJIR neural model is intended to be initialized from random weights, not downloaded pretrained weights. It is a small research model for language normalization, simple instruction following and grounded-answer assistance. It is not expected to match a frontier general assistant.

The non-neural local core remains available if the neural model is absent, too slow, inaccurate or disabled.

## Data preparation pipeline

1. Collect only public-domain, appropriately licensed or explicitly permissioned non-personal examples.
2. Preserve language, task type, source ID, source URI, license, permission reference and data class.
3. Reject bank/customer records, personal data, financial records, credentials and hosted-model outputs by default.
4. Deduplicate normalized input/target pairs.
5. Have a human reviewer inspect source rights, content quality, dialect, factual accuracy and privacy.
6. Create train/validation/test splits grouped by source ID. A source must never appear in more than one split.
7. Check that every required language appears in validation and test before any run can be approved.

The current intake and preflight modules implement steps 2–7 as a staging framework. The sensitive-identifier scanner is only a conservative additional filter; it is not a full privacy review.

## Initial language scope

- Uzbek Latin and Cyrillic
- Karakalpak Latin and Cyrillic
- Kazakh
- Russian
- English

Do not assume equal quality across languages merely because all language tags are accepted. Report per-language training, validation and test coverage and measure each language independently.

## Proposed first research configuration

| Parameter | Initial proposal |
|---|---:|
| Initialization | Random weights; no pretrained checkpoint |
| Tokenizer | Byte-level BPE |
| Vocabulary | 16,000 |
| Context length | 1,024 tokens |
| Hidden width | 512 |
| Transformer layers | 8 |
| Attention heads | 8 |
| Seed | 20261116 |

These are planning defaults, not a final model decision. Before implementation, estimate parameter count, memory use, training throughput, energy and checkpoint storage using a small pilot on actual hardware.

## Evaluation gates

A training run must not start until:
- dataset readiness passes with all rejected records resolved;
- the required minimum per language is met;
- the source-grouped split has no leakage;
- validation and test each cover all required languages;
- a human reviewer approves both dataset and split;
- evaluation examples are held out from training and reviewed independently.

Evaluate at minimum:
- spelling and dialect normalization;
- language identification and code-switching;
- multi-turn reference resolution;
- instruction following;
- grounded factual answers with source attribution;
- unsupported-claim rate and appropriate abstention;
- arithmetic and bounded reasoning;
- latency, memory and energy on target devices.

Do not select a checkpoint based on aggregate accuracy alone. Publish per-language metrics and known failure cases.

## Hardware and deployment

A Galaxy S22 Ultra is a useful target for inference experiments and quantized small-model trials, but it is not a practical environment for training a useful multilingual transformer from scratch at scale. Training may require rented GPU compute or a research partner. That does not mean the project must own a cloud: the data and training environment can remain separately controlled, and no customer/bank data should be sent to hosted model providers.

No cloud training service, GPU spend, model weights, external dataset or API key is configured by this plan. Compute procurement and any data transfer require separate approval.

## Current implementation boundary

- Dataset intake and provenance: implemented.
- License/privacy rejection and deduplication: implemented.
- Deterministic source-isolated split: implemented in preflight branch.
- Human approval and language coverage gate: implemented in preflight branch.
- Tokenizer training, transformer implementation, optimizer, checkpointing and training runner: not implemented.
- No training has started.
