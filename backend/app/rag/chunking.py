"""Split section text into overlapping chunks sized for embedding.

Token counts are estimated at ~4 characters per token — exact enough
for sizing chunks, and it avoids pulling in a tokenizer dependency for
a heuristic decision (documented in docs/rag-design.md). Chunks break
on paragraph boundaries where possible so sentences aren't cut mid-way.
"""

from dataclasses import dataclass

CHARS_PER_TOKEN = 4
TARGET_TOKENS = 900
OVERLAP_TOKENS = 120

_TARGET_CHARS = TARGET_TOKENS * CHARS_PER_TOKEN
_OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN


@dataclass
class Chunk:
    content: str
    token_count: int  # estimated


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _break_point(text: str, limit: int) -> int:
    """Best split position <= limit: paragraph > sentence > hard cut."""
    window = text[:limit]
    for separator in ("\n\n", "\n", ". "):
        position = window.rfind(separator)
        if position > limit // 2:
            return position + len(separator)
    return limit


def chunk_text(text: str) -> list[Chunk]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        remaining = text[start:]
        if len(remaining) <= _TARGET_CHARS:
            chunks.append(Chunk(content=remaining, token_count=estimate_tokens(remaining)))
            break
        split = _break_point(remaining, _TARGET_CHARS)
        piece = remaining[:split].strip()
        if piece:
            chunks.append(Chunk(content=piece, token_count=estimate_tokens(piece)))
        # Step forward with overlap so context spans chunk boundaries
        start += max(split - _OVERLAP_CHARS, 1)
    return chunks
