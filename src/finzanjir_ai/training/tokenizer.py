from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from typing import Iterable, Sequence

from finzanjir_ai.training.chat_format import (
    ChatMessage,
    IM_END,
    IM_SEP,
    IM_START,
    IM_TURN_END,
    parse_chat,
    serialize_chat,
)


SPECIAL_TOKEN_TEXT = (IM_START, IM_SEP, IM_END, IM_TURN_END)


@dataclass(frozen=True)
class ByteBPETokenizer:
    """Small deterministic byte-level BPE tokenizer; not GPT-2 tokenizer compatible."""

    merges: tuple[tuple[int, int], ...]

    @property
    def vocab_size(self) -> int:
        """Base byte+BPE vocabulary size, excluding reserved chat tokens."""
        return 256 + len(self.merges)

    @property
    def special_token_ids(self) -> dict[str, int]:
        """Stable reserved IDs immediately after this tokenizer's BPE vocabulary."""
        return {
            token: self.vocab_size + index
            for index, token in enumerate(SPECIAL_TOKEN_TEXT)
        }

    @property
    def total_vocab_size(self) -> int:
        return self.vocab_size + len(SPECIAL_TOKEN_TEXT)

    @classmethod
    def train(cls, texts: Iterable[str], *, vocab_size: int = 16000) -> "ByteBPETokenizer":
        if vocab_size < 256:
            raise ValueError("vocab_size must be at least 256")
        sequences = [list(text.encode("utf-8")) for text in texts if text]
        if not sequences:
            raise ValueError("tokenizer training corpus is empty")

        merges: list[tuple[int, int]] = []
        next_id = 256
        while next_id < vocab_size:
            counts: Counter[tuple[int, int]] = Counter()
            for sequence in sequences:
                counts.update(zip(sequence, sequence[1:]))
            if not counts:
                break

            # Deterministic tie-breaking makes the same corpus produce the same model.
            pair, _ = min(counts.items(), key=lambda item: (-item[1], item[0]))
            merges.append(pair)
            replaced: list[list[int]] = []
            for sequence in sequences:
                output: list[int] = []
                index = 0
                while index < len(sequence):
                    if (
                        index + 1 < len(sequence)
                        and (sequence[index], sequence[index + 1]) == pair
                    ):
                        output.append(next_id)
                        index += 2
                    else:
                        output.append(sequence[index])
                        index += 1
                replaced.append(output)
            sequences = replaced
            next_id += 1

        return cls(merges=tuple(merges))

    def encode(self, text: str) -> list[int]:
        tokens = list(text.encode("utf-8"))
        for merge_index, pair in enumerate(self.merges):
            merged_id = 256 + merge_index
            output: list[int] = []
            index = 0
            while index < len(tokens):
                if (
                    index + 1 < len(tokens)
                    and (tokens[index], tokens[index + 1]) == pair
                ):
                    output.append(merged_id)
                    index += 2
                else:
                    output.append(tokens[index])
                    index += 1
            tokens = output
        return tokens

    def encode_chat(self, messages: Iterable[ChatMessage]) -> list[int]:
        """Encode v1 chat structure with dedicated IDs; body text stays ordinary BPE."""
        serialized = serialize_chat(messages)
        markers = self.special_token_ids
        token_ids: list[int] = []
        cursor = 0
        while cursor < len(serialized):
            matches = [
                (position, marker)
                for marker in SPECIAL_TOKEN_TEXT
                if (position := serialized.find(marker, cursor)) >= 0
            ]
            if not matches:
                token_ids.extend(self.encode(serialized[cursor:]))
                break
            position, marker = min(matches, key=lambda item: item[0])
            token_ids.extend(self.encode(serialized[cursor:position]))
            token_ids.append(markers[marker])
            cursor = position + len(marker)
        return token_ids

    def _byte_expansions(self) -> list[bytes]:
        expansions: list[bytes] = [bytes((value,)) for value in range(256)]
        for left, right in self.merges:
            if left >= len(expansions) or right >= len(expansions):
                raise ValueError("invalid merge table")
            expansions.append(expansions[left] + expansions[right])
        return expansions

    def decode(self, token_ids: Sequence[int], *, errors: str = "strict") -> str:
        expansions = self._byte_expansions()
        output = bytearray()
        for token_id in token_ids:
            if not isinstance(token_id, int) or isinstance(token_id, bool):
                raise ValueError("token IDs must be integers")
            if token_id < 0 or token_id >= len(expansions):
                raise ValueError(f"token ID out of range: {token_id}")
            output.extend(expansions[token_id])
        return bytes(output).decode("utf-8", errors=errors)

    def decode_chat(self, token_ids: Sequence[int]) -> tuple[ChatMessage, ...]:
        """Decode dedicated structural IDs and parse a complete v1 conversation."""
        expansions = self._byte_expansions()
        reverse_special = {value: key for key, value in self.special_token_ids.items()}
        output: list[str] = []
        byte_buffer = bytearray()

        def flush_bytes() -> None:
            if byte_buffer:
                output.append(bytes(byte_buffer).decode("utf-8"))
                byte_buffer.clear()

        for token_id in token_ids:
            if not isinstance(token_id, int) or isinstance(token_id, bool):
                raise ValueError("token IDs must be integers")
            if token_id in reverse_special:
                flush_bytes()
                output.append(reverse_special[token_id])
            elif 0 <= token_id < len(expansions):
                byte_buffer.extend(expansions[token_id])
            else:
                raise ValueError(f"token ID out of range: {token_id}")
        flush_bytes()
        return parse_chat("".join(output))

    def to_json(self) -> str:
        payload = {
            "format": "finzanjir-byte-bpe-v1",
            "base_vocab_size": 256,
            "vocab_size": self.vocab_size,
            "merges": [list(pair) for pair in self.merges],
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> "ByteBPETokenizer":
        payload = json.loads(value)
        if payload.get("format") != "finzanjir-byte-bpe-v1":
            raise ValueError("unsupported tokenizer format")
        if payload.get("base_vocab_size") != 256:
            raise ValueError("invalid base vocabulary size")
        raw_merges = payload.get("merges")
        if not isinstance(raw_merges, list):
            raise ValueError("merges must be a list")

        merges: list[tuple[int, int]] = []
        for expected_id, pair in enumerate(raw_merges, start=256):
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or any(not isinstance(item, int) or isinstance(item, bool) for item in pair)
                or any(item < 0 or item >= expected_id for item in pair)
            ):
                raise ValueError("invalid BPE merge entry")
            merges.append((pair[0], pair[1]))

        tokenizer = cls(merges=tuple(merges))
        if payload.get("vocab_size") != tokenizer.vocab_size:
            raise ValueError("vocabulary size does not match merge table")
        return tokenizer
