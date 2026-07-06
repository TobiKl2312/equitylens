from app.rag.embeddings import BATCH_TOKEN_BUDGET, MAX_BATCH_ITEMS, VoyageClient


def _client() -> VoyageClient:
    return VoyageClient(api_key="test")


def test_batches_respect_token_budget():
    # ~1000 estimated tokens per text -> at most 8 per batch under an 8K budget
    texts = ["x" * 4000 for _ in range(20)]
    batches = _client()._batches(texts)
    assert all(len(batch) <= BATCH_TOKEN_BUDGET // 1000 for batch in batches)
    assert sum(len(batch) for batch in batches) == 20


def test_batches_respect_item_limit():
    texts = ["short" for _ in range(300)]
    batches = _client()._batches(texts)
    assert all(len(batch) <= MAX_BATCH_ITEMS for batch in batches)
    assert sum(len(batch) for batch in batches) == 300


def test_oversized_single_text_still_gets_a_batch():
    texts = ["y" * (BATCH_TOKEN_BUDGET * 8)]
    batches = _client()._batches(texts)
    assert len(batches) == 1
