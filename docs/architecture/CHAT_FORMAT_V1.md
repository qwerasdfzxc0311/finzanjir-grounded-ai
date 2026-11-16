# FINZANJIR Chat Format v1

Status: deterministic text serializer/parser proposal. It is not yet wired into model training, tokenizer special-token IDs, inference, or any deployed service.

## Message structure

Each message is serialized as:

```text
<|im_start|>{role}<|im_sep|>
{escaped content}<|im_end|>
```

Supported roles are `system`, `user`, `assistant`, and `tool`. A conversation is an ordered sequence of messages. Structural markers appearing literally in message content are escaped and restored by the parser.

## Evidence and privacy boundary

Do not place retrieval source IDs, licensing records, review notes, personal data, or bank/customer data into user-visible message content unless the task specifically requires it and the data is authorized. Dataset provenance and review metadata must remain in the governed dataset record, separate from model prompt text. Tool messages must contain only approved, minimized tool output.

## Known limits

- Complete messages only; partial assistant prefixes and streaming are not supported.
- No tool-call JSON schema or multimodal payload format.
- This serializer does not create dedicated tokenizer IDs for markers.
- This is not a standard such as ChatML; it is a versioned internal proposal.
- No corpus has been imported and no training has started.

## Next review gates

1. Review role semantics and whether a separate `developer` role is necessary.
2. Decide whether tool results are model-visible and under which allowlist.
3. Define tokenizer special IDs and model stop-token behavior.
4. Add reviewed golden conversations in all supported languages before training use.
