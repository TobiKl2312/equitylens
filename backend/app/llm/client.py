"""Claude API client wrapper with model tiering.

Sonnet for user-facing synthesis (chat, reports), Haiku for cheap
internal extraction/classification steps — the cost/quality split is
an explicit design decision, configurable via settings.
"""

from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from app.core.config import get_settings

CHAT_MODEL = "claude-sonnet-4-6"
FAST_MODEL = "claude-haiku-4-5"

# Grounded RAG answers are short; the cap is a cost guard for a
# credit-funded project, not a quality tradeoff.
CHAT_MAX_TOKENS = 4096

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=get_settings().anthropic_api_key)
    return _client


async def stream_chat(system: str, user_message: str) -> AsyncIterator[str]:
    """Yield text deltas from a streaming chat completion."""
    async with get_client().messages.stream(
        model=CHAT_MODEL,
        max_tokens=CHAT_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
