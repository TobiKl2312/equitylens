"""Versioned prompts. Bump the version whenever wording changes so
stored chat messages and reports stay traceable to the prompt that
produced them (reports table has a prompt_version column).
"""

import re

CHAT_PROMPT_VERSION = "chat-v1"

CHAT_SYSTEM = """\
You are an equity research assistant. You answer questions about a company \
using ONLY the numbered source excerpts from its SEC filings provided below.

Rules:
- Every factual claim must cite its source with a bracketed number, e.g. [1] \
or [2][3]. Place citations directly after the claim they support.
- Only cite source numbers that appear in the excerpts. Never invent sources.
- If the excerpts do not contain the answer, say so explicitly — do not fall \
back on general knowledge, and do not guess numbers.
- Quote figures exactly as they appear in the excerpts.
- Be concise and factual. This is research assistance, not investment advice; \
do not recommend buying or selling.\
"""


def build_context(sources: list[dict]) -> str:
    """Render retrieved chunks as numbered source excerpts."""
    blocks = []
    for number, source in enumerate(sources, start=1):
        header = (
            f"[{number}] {source['form_type']} filed {source['filing_date']}"
            f" — {source['section'] or 'unlabeled section'}"
        )
        blocks.append(f"{header}\n{source['content']}")
    return "\n\n---\n\n".join(blocks)


_CITATION = re.compile(r"\[(\d{1,2})\]")


def extract_citations(text: str, source_count: int) -> tuple[list[int], list[int]]:
    """Return (valid, invalid) source numbers cited in the answer.

    Invalid citations (numbers outside the provided range) indicate
    hallucinated sources and are surfaced to the client.
    """
    cited = {int(match) for match in _CITATION.findall(text)}
    valid = sorted(number for number in cited if 1 <= number <= source_count)
    invalid = sorted(number for number in cited if not 1 <= number <= source_count)
    return valid, invalid
