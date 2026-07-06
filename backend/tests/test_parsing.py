from app.rag.parsing import html_to_text, split_sections

FILING_HTML = """
<html><body>
<script>var tracking = true;</script>
<div>
  <p>TABLE OF CONTENTS</p>
  <p>Item 1. Business ..... 3</p>
  <p>Item 1A. Risk Factors ..... 20</p>
  <p>Item 7. Management's Discussion ..... 45</p>
</div>
<div>
  <h2>Item 1. Business</h2>
  <p>{business}</p>
  <h2>Item 1A. Risk Factors</h2>
  <p>{risks}</p>
  <h2>Item 7. Management's Discussion and Analysis</h2>
  <p>{mdna}</p>
</div>
</body></html>
""".format(
    business="The Company designs and sells consumer electronics. " * 20,
    risks="Supply chain concentration creates material risks. " * 20,
    mdna="Revenue increased driven by Services growth. " * 20,
)


def test_html_to_text_strips_scripts():
    text = html_to_text(FILING_HTML)
    assert "tracking" not in text
    assert "consumer electronics" in text


def test_split_sections_finds_items():
    text = html_to_text(FILING_HTML)
    sections = split_sections(text, form_type="10-K")
    names = [section.name for section in sections]
    assert "Item 1. Business" in names
    assert "Item 1A. Risk Factors" in names
    assert "Item 7. Management's Discussion and Analysis" in names


def test_toc_entries_are_skipped():
    """The last occurrence of each heading wins, so section bodies must
    contain the real content, not the table-of-contents stubs."""
    text = html_to_text(FILING_HTML)
    sections = {section.name: section.text for section in split_sections(text)}
    assert "Supply chain concentration" in sections["Item 1A. Risk Factors"]


def test_unstructured_text_falls_back_to_single_section():
    sections = split_sections("Just a plain announcement with no items. " * 50)
    assert len(sections) == 1
    assert sections[0].name == "Full document"
