# FINZANJIR byte-level BPE tokenizer

Status: deterministic byte-level BPE tokenizer with reserved chat-format v1 token IDs. No corpus has been imported and no model training has started.

## Scope

The pure-Python tokenizer starts with all 256 byte values and learns frequent adjacent-byte merges from approved UTF-8 text. It supports Uzbek Latin/Cyrillic, Karakalpak Latin/Cyrillic, Kazakh, Russian and English without a pretrained vocabulary. The merge process is deterministic, and the tokenizer can be exported/imported as JSON.

This is a small research implementation. It is deliberately **not** compatible with GPT-2, tiktoken or SentencePiece. It does not include normalization, language-specific pre-tokenization, padding, truncation, batching or a model runtime.

## Vocabulary and special chat IDs

The existing base byte+BPE vocabulary remains unchanged: byte IDs are 0–255 and learned merge IDs begin at 256. Three reserved chat-format v1 IDs are assigned immediately after the base vocabulary, in this fixed order:

1. `<|im_start|>`
2. `<|im_sep|>`
3. `<|im_end|>`

Use `encode_chat` and `decode_chat` for structured conversations. Plain `encode` treats marker-looking strings as ordinary UTF-8 text and never activates special IDs. Within chat bodies, literal marker strings are escaped by the chat serializer, so only framing markers become special IDs. `vocab_size` continues to mean the base byte+BPE vocabulary; `total_vocab_size` includes the three reserved IDs.

The special IDs are derived from the trained merge count and are not stored separately in the v1 tokenizer JSON. This keeps existing v1 tokenizer files readable and preserves their BPE IDs. A future model checkpoint must store the exact tokenizer JSON and special-token mapping together; changing the merge table changes the derived special IDs.

## Safety and data boundary

Only text from the already-approved dataset intake should be passed to `ByteBPETokenizer.train`. Do not train from raw bank/customer records, personal data, secrets, hosted model outputs or unlicensed web dumps. The tokenizer class itself does not inspect licenses or detect personal information; callers must enforce the dataset governance gate before supplying text.

## Resource note

Tokenizer training is CPU-based and intended for small controlled corpora and reproducible tests. It is not the neural-model training process. Vocabulary size is a maximum; if the corpus has too few distinct byte pairs, the actual vocabulary can be smaller.

## Next gates

1. Review tokenization and chat round-trips on human-checked examples for every supported language.
2. Decide whether the model needs additional control tokens (for example, an assistant-turn terminator) before freezing the vocabulary contract.
3. Add reviewed golden conversations and test malformed/partial sequence handling before training use.
4. Estimate model parameters, memory and compute before implementing transformer training.
