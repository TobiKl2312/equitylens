"""Voyage AI embeddings client (voyage-finance-2, 1024 dimensions).

Voyage distinguishes document vs query embeddings via input_type —
using the right one measurably improves retrieval.

Rate limits vary hugely by account tier (accounts without a payment
method get ~10K tokens/minute), so batches are sized by a token budget
and 429s are handled by honoring the Retry-After header — the client
degrades to the account's actual throughput instead of failing.
"""

import logging
import time

import httpx

from app.rag.chunking import estimate_tokens

logger = logging.getLogger(__name__)

VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"
MODEL = "voyage-finance-2"
MAX_BATCH_ITEMS = 128  # Voyage hard limit
BATCH_TOKEN_BUDGET = 8000  # keeps single batches under low-tier TPM limits
MAX_ATTEMPTS = 10


class VoyageClient:
    def __init__(self, api_key: str):
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    def close(self) -> None:
        self._client.close()

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self._client.post(
                    VOYAGE_URL,
                    json={"input": texts, "model": MODEL, "input_type": input_type},
                )
            except httpx.TransportError as exc:  # timeouts, resets, DNS blips
                wait = min(2**attempt, 60)
                logger.info("Voyage transport error (%s); retrying in %ds", exc, wait)
                time.sleep(wait)
                continue
            if response.status_code == 429:
                wait = float(response.headers.get("retry-after", 2**attempt))
                wait = min(max(wait, 1.0), 120.0)
                logger.info("Voyage rate limited; waiting %.0fs", wait)
                time.sleep(wait)
                continue
            if response.status_code >= 500:
                time.sleep(min(2**attempt, 60))
                continue
            response.raise_for_status()
            data = response.json()["data"]
            return [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]
        raise RuntimeError(f"Voyage still rate limited after {MAX_ATTEMPTS} attempts")

    def _batches(self, texts: list[str]) -> list[list[str]]:
        batches: list[list[str]] = []
        current: list[str] = []
        current_tokens = 0
        for text in texts:
            tokens = estimate_tokens(text)
            if current and (
                current_tokens + tokens > BATCH_TOKEN_BUDGET or len(current) >= MAX_BATCH_ITEMS
            ):
                batches.append(current)
                current, current_tokens = [], 0
            current.append(text)
            current_tokens += tokens
        if current:
            batches.append(current)
        return batches

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in self._batches(texts):
            vectors.extend(self._embed(batch, "document"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "query")[0]
