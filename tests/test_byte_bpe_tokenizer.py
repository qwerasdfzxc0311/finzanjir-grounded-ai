from finzanjir_ai.training.tokenizer import ByteBPETokenizer


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


def test_empty_corpus_and_small_vocab_are_rejected():
    import pytest

    with pytest.raises(ValueError, match="empty"):
        ByteBPETokenizer.train(["", ""])
    with pytest.raises(ValueError, match="at least 256"):
        ByteBPETokenizer.train(["abc"], vocab_size=255)


def test_decode_rejects_invalid_token_ids():
    import pytest

    tokenizer = ByteBPETokenizer.train(["abc"], vocab_size=260)
    with pytest.raises(ValueError, match="out of range"):
        tokenizer.decode([999])
