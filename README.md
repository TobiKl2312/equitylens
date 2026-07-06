# EquityLens

**AI investment research platform** — aggregates SEC filings, XBRL fundamentals, and market data for ~35 US large caps, and (from week 2) answers questions about them with a citation-grounded RAG pipeline.

> ⚠️ Educational portfolio project. Nothing here is investment advice.

## Status

- ✅ **Week 1 — Foundation & data:** Postgres/pgvector schema, SEC EDGAR + XBRL + price ingestion, read API
- ⬜ Week 2 — RAG core: filing parsing, section-aware chunking, embeddings, cited chat
- ⬜ Week 3 — Frontend: Next.js screener, company dashboard, chat UI with citation panel
- ⬜ Week 4 — AI reports, deployment, polish

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────┐
│  Next.js UI │────▶│  FastAPI                          │
│  (week 3)   │     │  ├── api/        routes, DTOs     │
└─────────────┘     │  ├── services/   business logic   │
                    │  ├── ingestion/  EDGAR, XBRL,     │
                    │  │               prices           │
                    │  ├── rag/        (week 2)         │
                    │  └── llm/        (week 2)         │
                    └───────┬───────────────┬───────────┘
                            ▼               ▼
                      PostgreSQL      Claude API /
                      + pgvector      Voyage AI
```

A deliberate **modular monolith** — see [docs/decisions](docs/decisions) for why.

## Quickstart

Requires Docker.

```bash
cp .env.example .env          # set EDGAR_USER_AGENT to include your email
docker compose up --build     # db + migrations + API on :8000
```

Then load data (one-off, ~2 minutes):

```bash
docker compose exec api uv run python -m app.cli all
```

Explore the API at http://localhost:8000/docs — e.g.:

- `GET /companies` — the universe with metadata
- `GET /companies/AAPL/prices?start=2025-01-01`
- `GET /companies/AAPL/fundamentals?metric=revenue`
- `GET /companies/AAPL/filings`

## Local development (without Docker)

Requires [uv](https://docs.astral.sh/uv/) and a Postgres 16 with pgvector on `localhost:5432`.

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.cli all
uv run uvicorn app.main:app --reload
```

Lint and tests (no network or DB needed):

```bash
uv run ruff check .
uv run pytest
```

## Data sources

| Source | Data | Notes |
|---|---|---|
| SEC EDGAR | 10-K/10-Q metadata + full text, XBRL fundamentals | Free, no key; descriptive User-Agent required |
| yfinance | Daily EOD prices | Fine for a portfolio project, not production-grade |
| FRED (planned) | Macro context | |

How we deal with restatements, vendor quirks, and rate limits: [docs/data-quality.md](docs/data-quality.md).

## Docs

- [Architecture](docs/architecture.md)
- [Data quality](docs/data-quality.md)
- [Decision records](docs/decisions)
