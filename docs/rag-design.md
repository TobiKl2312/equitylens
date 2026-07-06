# RAG design

How EquityLens turns SEC filings into citable answers.

## Corpus

Latest 10-K plus the two most recent 10-Qs per company (~105 filings across
the 35-ticker universe). Bounded deliberately: current enough for research
questions, small enough that a full re-embed costs minutes, not hours.

## Ingestion pipeline

```
EDGAR HTML ─▶ html_to_text ─▶ split_sections ─▶ chunk_text ─▶ Voyage embed ─▶ pgvector
              (bs4/lxml)      (Item headings)   (~900 tok,     (voyage-        (HNSW,
                                                 120 overlap)   finance-2)      cosine)
```

Each filing walks a state machine (`pending → parsed → chunked → embedded`,
or `failed`), so partial progress is visible in the DB and re-runs are
idempotent — chunks from a previous attempt are replaced, never duplicated.

### Section-aware chunking

10-K/10-Qs have a standard item structure ("Item 1A. Risk Factors"). We split
on those headings **before** chunking so every chunk carries its section as
metadata. That buys two things: citations can say *where* in the filing a
statement lives, and retrieval quality is measurable against expected
sections (see Eval below).

Heading detection is heuristic. The table of contents repeats every heading,
so we keep the **last** occurrence of each item number — the real section
start. Filings that defeat the heuristic degrade to a single "Full document"
section rather than mislabeled chunks.

### Chunk sizing

~900 tokens per chunk with ~120 tokens overlap, breaking on paragraph
boundaries where possible. Token counts are estimated at 4 chars/token —
chunk sizing is a heuristic decision, so a tokenizer dependency isn't
warranted; the estimate is within ~10% on filing prose.

### Embeddings

`voyage-finance-2` (1024 dims) — finance-domain embeddings measurably beat
general-purpose models on filing text. Voyage distinguishes `document` vs
`query` input types; we use both correctly. Batched 64 chunks/request with
exponential backoff on 429s.

## Query pipeline

1. Embed the question (`input_type=query`).
2. **Hybrid retrieval**: pgvector cosine similarity + SQL filters (company,
   optionally form type) in a single query — the payoff of keeping vectors
   and metadata in one Postgres (ADR 0002). Top k=8.
3. Claude (`claude-sonnet-4-6`) answers under a strict system prompt: only
   from the numbered excerpts, every claim cited as `[n]`, explicit "not in
   the excerpts" when the context lacks the answer.
4. The answer streams to the client as SSE (`sources` → `delta`* → `done`).

### Citation validation

Bracketed citations in the answer are validated server-side against the
source count actually provided. Out-of-range citations — hallucinated
sources — are surfaced separately in the `done` event (`invalid_citations`)
instead of being silently trusted. The assistant message also stores
`retrieved_chunk_ids`, so every answer is auditable: which chunks did the
model see when it said this?

### Model tiering

Sonnet 4.6 for user-facing synthesis, Haiku 4.5 reserved for cheap internal
extraction steps (report pipeline, week 4). Configured in `app/llm/client.py`.

## Eval

`tests/eval/golden_questions.json` holds hand-written questions with expected
source sections. `uv run python -m app.cli eval` embeds each question,
retrieves top-8, and scores a hit when any retrieved chunk comes from an
expected section. This measures **retrieval**, not generation — it needs no
LLM call, runs in seconds, and catches regressions from chunking or
embedding changes.

Current result: **11/12 (92%)** on the corpus of 105 filings / ~6,700
chunks. The one miss (Pfizer patent expirations) retrieves relevant chunks
from sections the heading heuristic left unlabeled — a parsing-coverage
issue, not a retrieval failure.

## Known limitations

- Heading detection misses filings with exotic formatting (falls back to
  unlabeled chunks — retrieval still works, section filters don't).
- 10-Q item numbers collide across Part I/II; labels are kept generic.
- No reranker; k=8 cosine-only. A cross-encoder rerank stage is the natural
  next quality lever.
