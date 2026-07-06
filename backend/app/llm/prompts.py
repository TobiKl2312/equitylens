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


REPORT_PROMPT_VERSION = "report-v1"

REPORT_SYSTEM = """\
You are an equity research analyst writing one section of a research report \
about a company, using ONLY the numbered source excerpts from its SEC filings \
and the financial data table provided.

Rules:
- Every claim from the excerpts must cite its source with a bracketed number, \
e.g. [3]. Figures from the financial data table need no citation.
- Only cite source numbers that appear in the excerpts. Never invent sources.
- Quote figures exactly; do not compute numbers the sources don't state, \
except simple growth rates from the financial data table.
- Write in concise, professional research prose. Use markdown. Do NOT repeat \
the section heading — it is added by the system.
- This is research assistance, not investment advice; never recommend buying \
or selling.\
"""

# (title, retrieval query, writing instruction) — the report is generated
# section by section with targeted retrieval per section.
REPORT_SECTIONS = [
    (
        "Business Overview",
        "business segments products services revenue drivers strategy competition",
        "Describe what the company does, its main segments/products, how it "
        "makes money, and its competitive position. 2-3 paragraphs.",
    ),
    (
        "Financial Performance",
        "revenue growth margins operating results management discussion and analysis",
        "Analyze the trajectory shown in the financial data table and what "
        "management attributes it to in the excerpts. Discuss growth, "
        "profitability, and notable drivers. 2-3 paragraphs.",
    ),
    (
        "Key Risks",
        "material risk factors that could adversely affect the business",
        "Summarize the 4-6 most material risk factors as a bulleted list, "
        "each with a bold label and a one-to-two sentence explanation.",
    ),
    (
        "Bull & Bear Case",
        "",  # no new retrieval — synthesizes from all sources gathered so far
        "Present a balanced '**Bull case**' and '**Bear case**' (3 bullets "
        "each) grounded strictly in the excerpts and financial data. End "
        "with one sentence on what to watch next quarter.",
    ),
]

FINANCIAL_SUMMARY_SYSTEM = """\
You format financial data. Given fiscal-year figures, produce a markdown \
bullet list (3-5 bullets) of the most notable quantitative highlights: \
growth rates, margin changes, records. Compute percentages from the given \
numbers only. Output ONLY the bullet list — no heading, no title, no \
commentary, no advice, no sources.\
"""


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
