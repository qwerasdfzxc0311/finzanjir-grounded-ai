# FINZANJIR From-Scratch Model: Compute and Memory Estimate

Status: planning estimate only. No training code is being launched and no hardware or cloud resources are being rented.

## Baseline configuration

The current preflight proposal is:
- decoder-only transformer;
- 8 layers;
- hidden width 512;
- 8 attention heads;
- context length 1,024;
- byte-level BPE vocabulary 16,000;
- no pretrained weights.

For a conventional 4x-width feed-forward block, approximate parameter count is:

- Transformer blocks: about 25.2 million parameters.
- Token embedding (16,000 × 512): about 8.2 million.
- Total with tied input/output embeddings: about 33.4 million.
- Total with untied output head: about 41.6 million.

This is an estimate, not an implemented model. Exact count depends on normalization, biases, positional encoding, output-head tying, and architecture choices.

## Memory estimate

For the 33.4M tied-embedding configuration:
- FP32 weights alone: about 127 MiB.
- FP32 gradients: another 127 MiB.
- Adam first/second moments: about 254 MiB combined.
- Training framework, temporary tensors, dataloader, activations, and checkpoints add substantially more.

Mixed precision does not simply halve total memory because optimizer states and/or master weights may remain FP32. Attention implementation and batch size can dominate activation memory. Standard attention may materialize large sequence-by-sequence attention tensors; memory-efficient attention reduces this overhead.

Planning guidance, not a guarantee:
- 8 GB GPU VRAM: possible for a carefully constrained small-model experiment with small micro-batches and memory-efficient attention; tight.
- 12–16 GB GPU VRAM: more practical for iteration and larger micro-batches.
- 24 GB or more: more headroom for longer context, larger batches, and experiments.
- CPU-only or a phone: suitable for tokenizer/data validation and tiny smoke tests, not recommended for serious multi-language transformer training from scratch.

A phone's advertised system RAM is not equivalent to available GPU VRAM. The Samsung S22 Ultra can help validate preprocessing and small inference experiments, but should not be treated as the training machine for this model.

## Token and compute scenarios

A common dense-transformer training approximation is 6 × parameter_count × training_tokens. Using 33.4M parameters:

| Training tokens | Approximate training compute |
|---:|---:|
| 10M | 2.0 PFLOP |
| 30M | 6.0 PFLOP |
| 100M | 20.0 PFLOP |
| 300M | 60.1 PFLOP |
| 1B | 200.2 PFLOP |

These are theoretical operation counts, not wall-clock promises. Actual duration depends on GPU type, sustained throughput, sequence packing, data loading, precision, kernel efficiency, evaluation, checkpointing, and failed runs. Benchmark a short representative run before estimating cost or committing resources.

## Recommended staged plan

1. **Pipeline smoke test:** 10M–30M approved tokens, tiny run, prove tokenizer/model/loss/checkpoint/resume/evaluation work. This is engineering validation, not evidence of useful assistant quality.
2. **Research pilot:** only after reviewed data is available, consider 100M tokens and evaluate per language, not only aggregate loss.
3. **Scale decision:** consider 300M+ tokens only if the pilot shows learning, acceptable language balance, and no data leakage. Obtain a real GPU benchmark and cost quote first.
4. **Release gate:** require held-out native-speaker tests, factuality/grounding tests, safety tests, memorization/privacy checks, and comparison against the existing retrieval-first system.

## Data constraints

The five-language target is Uzbek, Karakalpak, Kazakh, Russian, and English. A token total alone does not establish coverage: measure token and document counts per language, source diversity, domain balance, quality, and license/permission. Do not fill low-resource language gaps with unlicensed or synthetic-only material and then claim native fluency.

Never use bank/customer records, personal data, secrets, or data without documented training permission. Dataset provenance and review metadata remain outside prompt text.

## Decision

Do not start full training yet. The current repository has a tokenizer and preflight planning, but no completed transformer, optimizer, training runner, approved corpus, or measured GPU throughput. The next justified step is to complete a minimal model implementation and run a small, non-sensitive benchmark only after a compute budget and reviewed corpus are approved.
