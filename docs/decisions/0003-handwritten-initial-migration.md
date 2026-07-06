# ADR 0003: Handwritten initial migration, autogenerate later

**Status:** accepted · **Date:** 2026-07-06

## Context

Alembic can autogenerate migrations by diffing models against a live
database, but that requires a running Postgres at development time, and
autogenerate does not emit `CREATE EXTENSION vector` or HNSW index DDL.

## Decision

The initial migration (`0001_initial_schema.py`) is handwritten and is the
source of truth for extension setup and the HNSW index. Subsequent
migrations use `alembic revision --autogenerate` against the dockerized DB.

## Consequences

- ✅ `docker compose up` provisions a complete schema with no manual steps.
- ❌ Model/migration drift in the initial schema must be caught by review;
  from revision 0002 onward autogenerate diffs guard against it.
