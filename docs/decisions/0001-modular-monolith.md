# ADR 0001: Modular monolith, not microservices

**Status:** accepted · **Date:** 2026-07-06

## Context

The platform has several concerns (ingestion, API, RAG, LLM orchestration)
that could each be a service. One developer builds and operates it.

## Decision

One FastAPI application with strict internal module boundaries
(`api/`, `services/`, `ingestion/`, `rag/`, `llm/`), one Postgres, one
deployable unit.

## Consequences

- ✅ One deployment, one log stream, no inter-service auth/network failures.
- ✅ Refactoring across module boundaries is a code change, not an API change.
- ✅ Module boundaries keep a later extraction possible (ingestion is the
  natural first candidate — it's already decoupled via the database).
- ❌ Ingestion load and API load share one process; acceptable at 35 tickers,
  revisit if the universe grows 100x.
