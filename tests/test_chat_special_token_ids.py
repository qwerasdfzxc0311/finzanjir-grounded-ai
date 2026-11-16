import pytest

from finzanjir_ai.training.chat_format import ChatMessage, IM_END, IM_SEP, IM_START
from finzanjir_ai.training.tokenizer import ByteBPETokenizer, SPECIAL_TOKEN_TEXT


def test_byte_bpe_round_trips_multilingual_text():
    texts = [
        "Salom, FINZANJIR!",
        "Сәлем, әлем!",
        "Сәлеметсиз бе, дүнья!",
        "Hello world",
        "Salom, FINZANJIR!",
    ]
    tokenizer = ByteBPETokenizer.train(texts, vocab_size=320)
    for text in texts:
        assert tokenizer.decode(tokenizer.encode(text)) == text


def test_training_is_deterministic():
    corpus = ["abababab", "abab", "baba", "FINZANJIR"]
    first = ByteBPETokenizer.train(corpus, vocab_size=280)
    second = ByteBPETokenizer.train(corpus, vocab_size=280)
    assert first.merges == second.merges
    assert first.to_json() == second.to_json()


def test_json_round_trip_preserves_tokenizer():
    tokenizer = ByteBPETokenizer.train(["hello hello", "сәлем сәлем"], vocab_size=300)
    restored = ByteBPETokenizer.from_json(tokenizer.to_json())
    assert restored == tokenizer
    assert restored.encode("сәлем hello") == tokenizer.encode("сәлем hello")
    assert restored.special_token_ids == tokenizer.special_token_ids


def test_empty_corpus_and_small_vocab_are_rejected():
    with pytest.raises(ValueError, match="empty"):
        ByteBPETokenizer.train(["", ""])
    with pytest.raises(ValueError, match="at least 256"):
        ByteBPETokenizer.train(["abc"], vocab_size=255)


def test_decode_rejects_invalid_token_ids():
    tokenizer = ByteBPETokenizer.train(["abc"], vocab_size=260)
    with pytest.raises(ValueError, match="out of range"):
        tokenizer.decode([999])


def test_special_token_ids_are_reserved_after_base_vocabulary():
    tokenizer = ByteBPETokenizer.train(["FINZANJIR tokenizer"], vocab_size=280)
    ids = tokenizer.special_token_ids
    assert tuple(ids) == SPECIAL_TOKEN_TEXT
    assert tuple(ids.values()) == tuple(range(tokenizer.vocab_size, tokenizer.total_vocab_size))
    assert len(set(ids.values())) == 3


def test_chat_round_trip_uses_special_ids_and_preserves_multilingual_content():
    messages = (
        ChatMessage("system", "Use only approved evidence."),
        ChatMessage("user", "Сәлем! Qaraqalpaqsha: Сәлеметсиз бе?"),
        ChatMessage("assistant", "Salom! Javob manbaga asoslangan."),
    )
    tokenizer = ByteBPETokenizer.train(
        [message.content for message in messages], vocab_size=320
    )
    encoded = tokenizer.encode_chat(messages)
    assert encoded.count(tokenizer.special_token_ids[IM_START]) == len(messages)
    assert encoded.count(tokenizer.special_token_ids[IM_SEP]) == len(messages)
    assert encoded.count(tokenizer.special_token_ids[IM_END]) == len(messages)
    assert tokenizer.decode_chat(encoded) == messages


def test_literal_marker_text_in_message_body_is_not_a_special_token():
    content = f"These are literal strings: {IM_START} {IM_SEP} {IM_END}"
    messages = (ChatMessage("user", content),)
    tokenizer = ByteBPETokenizer.train([content], vocab_size=300)
    encoded = tokenizer.encode_chat(messages)
    ids = tokenizer.special_token_ids
    # Only the message framing is structural: one start, one separator, one end.
    assert encoded.count(ids[IM_START]) == 1
    assert encoded.count(ids[IM_SEP]) == 1
    assert encoded.count(ids[IM_END]) == 1
    assert tokenizer.decode_chat(encoded) == messages


def test_plain_text_encode_does_not_activate_chat_special_tokens():
    tokenizer = ByteBPETokenizer.train(["ordinary text"], vocab_size=280)
    literal = f"{IM_START}user{IM_SEP}hello{IM_END}"
    encoded = tokenizer.encode(literal)
    assert not set(encoded).intersection(tokenizer.special_token_ids.values())
    assert tokenizer.decode(encoded) == literal


def test_plain_decode_rejects_reserved_chat_token_ids():
    tokenizer = ByteBPETokenizer.train(["abc"], vocab_size=260)
    with pytest.raises(ValueError, match="out of range"):
        tokenizer.decode([tokenizer.special_token_ids[IM_START]])
