# FINZANJIR byte-level BPE tokenizer

Status: first deterministic tokenizer implementation; no corpus has been imported and no model training has started.

## Scope

The pure-Python tokenizer starts with all 256 byte values and learns frequent adjacent-byte merges from approved UTF-8 text. It supports Uzbek Latin/Cyrillic, Karakalpak Latin/Cyrillic, Kazakh, Russian and English without a pretrained vocabulary. The merge process is deterministic, and the tokenizer can be exported/imported as JSON.

This is a small research implementation. It is deliberately **not** compatible with GPT-2, tiktoken or SentencePiece. It does not include normalization, language-specific pre-tokenization, special chat tokens, padding, truncation, batching or a model runtime. Those are separate design decisions and require evaluation on reviewed language samples.

## Safety and data boundary

Only text from the already-approved dataset intake should be passed to `ByteBPETokenizer.train`. Do not train from raw bank/customer records, personal data, secrets, hosted model outputs or unlicensed web dumps. The tokenizer class itself does not inspect licenses or detect personal information; callers must enforce the dataset governance gate before supplying text.

## Resource note

Tokenizer training is CPU-based and intended for small controlled corpora and reproducible tests. It is not the neural-model training process. Vocabulary size is a maximum; if the corpus has too few distinct byte pairs, the actual vocabulary can be smaller.

## Next gates

1. Review tokenizer behavior on human-checked examples for every supported language.
2. Add normalization and pre-tokenization only after comparing measurable language-specific results.
3. Define special tokens and the exact chat/instruction format.
4. Estimate model parameters, memory and compute before implementing transformer training.
