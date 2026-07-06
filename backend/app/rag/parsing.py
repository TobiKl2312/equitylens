"""Parse SEC filing HTML into section-labeled plain text.

10-K/10-Q filings follow a standard item structure ("Item 1A. Risk
Factors", "Item 7. Management's Discussion..."). We split along those
headings so chunks carry their section as metadata — retrieval can then
filter or boost by section, and citations can say *where* in the filing
a statement comes from.

Heading detection is heuristic: the table of contents repeats every
heading, so for each item number we keep the LAST occurrence, which is
the actual section start. Filings that defeat the heuristics degrade
gracefully to a single "Full document" section.
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

# Canonical 10-K item titles (subset we care most about, for nicer labels)
ITEM_TITLES_10K = {
    "1": "Business",
    "1A": "Risk Factors",
    "1B": "Unresolved Staff Comments",
    "2": "Properties",
    "3": "Legal Proceedings",
    "5": "Market for Registrant's Common Equity",
    "7": "Management's Discussion and Analysis",
    "7A": "Quantitative and Qualitative Disclosures About Market Risk",
    "8": "Financial Statements",
    "9A": "Controls and Procedures",
}

_ITEM_HEADING = re.compile(r"^\s*item\s+(\d{1,2}[a-c]?)\W", re.IGNORECASE)
_MAX_HEADING_LENGTH = 120


@dataclass
class Section:
    name: str  # e.g. "Item 1A. Risk Factors"
    text: str


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse whitespace but keep line structure for heading detection
    lines = [re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _find_headings(lines: list[str]) -> dict[str, int]:
    """Map item number -> line index of its LAST occurrence (skips the TOC)."""
    headings: dict[str, int] = {}
    for index, line in enumerate(lines):
        if len(line) > _MAX_HEADING_LENGTH:
            continue
        match = _ITEM_HEADING.match(line)
        if match:
            headings[match.group(1).upper()] = index
    return headings


def split_sections(text: str, form_type: str = "10-K") -> list[Section]:
    """Split filing text into item sections; fall back to one big section."""
    lines = text.splitlines()
    headings = _find_headings(lines)
    if len(headings) < 3:  # heuristics failed — don't pretend we have structure
        return [Section(name="Full document", text=text)]

    ordered = sorted(headings.items(), key=lambda kv: kv[1])
    sections = []
    for position, (item, start) in enumerate(ordered):
        end = ordered[position + 1][1] if position + 1 < len(ordered) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        if len(body) < 200:  # skip stub sections ("Item 6. [Reserved]")
            continue
        title = ITEM_TITLES_10K.get(item)
        name = f"Item {item}. {title}" if title and form_type == "10-K" else f"Item {item}"
        sections.append(Section(name=name, text=body))
    return sections or [Section(name="Full document", text=text)]
