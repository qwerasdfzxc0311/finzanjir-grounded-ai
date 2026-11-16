# FINZANJIR Chat Format v1

Status: deterministic text serializer/parser with tokenizer IDs for structural markers and an explicit assistant-turn terminator. It is not yet connected to model training, inference, or a deployed service.

## Message structure

Each message is serialized as:

```text
<|im_start|>{role}<|im_sep|>
{escaped content}{ending}
```

Supported roles are `system`, `user`, `assistant`, and `tool`.

- `<|im_end|>` closes one message. It does not by itself mean the assistant's response is complete.
- `<|assistant_end|>` closes an assistant turn. It is valid only on an `assistant` message.
- An assistant message that continues reasoning or hands control to a tool ends with `<|im_end|>`; a final assistant response ends with `<|assistant_end|>`.
- User, system, and tool messages end with `<|im_end|>`.

The `ChatMessage.end_of_turn` flag represents the distinction. It defaults to false for backward compatibility. The parser rejects assistant-turn endings on non-assistant roles. Structural markers appearing literally in message content are escaped and restored.

## Tool interaction boundary

This version can represent a tool result as a `tool` message, but it does not yet define a tool-call payload schema, tool allowlist, or automatic execution. A tool result is untrusted input: it must be minimized, validated, and explicitly approved before it is made available to a model. Tool output must never silently become authoritative project evidence.

## Evidence and privacy boundary

Do not place retrieval source IDs, licensing records, review notes, personal data, or bank/customer data into user-visible message content unless the task specifically requires it and the data is authorized. Dataset provenance and review metadata must remain in the governed dataset record, separate from model prompt text. Tool messages must contain only approved, minimized tool output.

## Known limits

- Complete messages only; partial assistant prefixes and streaming are not supported.
- No tool-call JSON schema or multimodal payload format.
- This is not a standard such as ChatML; it is a versioned internal proposal.
- No corpus has been imported and no training has started.

## Next review gates

1. Review whether a separate `developer` role is necessary and define precedence.
2. Define tool-call envelope and strict allowlist before any tool execution integration.
3. Add reviewed golden conversations in all supported languages before training use.
4. Estimate model parameters, memory and compute before implementing transformer training.
