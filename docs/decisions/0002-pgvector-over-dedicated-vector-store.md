# ADR 0002: pgvector instead of a dedicated vector store

**Status:** accepted · **Date:** 2026-07-06

## Context

The RAG pipeline needs vector similarity search over filing chunks. Options:
a dedicated vector DB (Pinecone, Qdrant, Weaviate) or pgvector inside the
Postgres we already run.

## Decision

pgvector with an HNSW index, in the same database as the relational data.

## Consequences

- ✅ One less moving part: no extra service, no sync between relational rows
  and vectors, chunks and their metadata live in the same transaction.
- ✅ Hybrid retrieval (vector similarity + SQL metadata filters on ticker,
  form type, fiscal year) is a single query.
- ✅ Corpus size (~35 companies × a few filings × a few hundred chunks ≈ low
  tens of thousands of vectors) is far below where specialized stores pay off.
- ❌ At millions of vectors or high QPS, a dedicated store would win;
  the `rag/retrieval` module is the seam where it would be swapped in.
