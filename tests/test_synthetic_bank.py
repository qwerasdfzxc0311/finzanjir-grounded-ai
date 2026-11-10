from synthetic_data.generator import SyntheticBank, generate_synthetic_batch


def test_synthetic_bank_generates_traceable_synthetic_transactions():
    bank = SyntheticBank(seed=7, bank_id="bank-demo")
    batch = bank.generate_transactions(3)

    assert len(batch) == 3
    assert all(item["synthetic"] is True for item in batch)
    assert all(item["bank_id"] == "bank-demo" for item in batch)
    assert len({item["transaction_id"] for item in batch}) == 3


def test_synthetic_batch_is_deterministic_for_same_seed():
    first = generate_synthetic_batch(seed=11, count=2)
    second = generate_synthetic_batch(seed=11, count=2)
    assert first == second
