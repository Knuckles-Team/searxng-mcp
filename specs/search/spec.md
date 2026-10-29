# CONN-SEARXNG-MCP-SEARCH — Web search results as a virtual source

Owner: searxng-mcp. Cross-repo IDs: `MEDULLA-UNIFIED-DATA-PLANE-R038.7.7`, `ARBORA-OPS-R067`.

## Purpose and user stories

A caller of `research.web` searches the web and selects pages to fetch. The search results are a short-lived source with provenance (query, engine, rank, time). They must not become graph records. Only the pages the caller selects are fetched and ingested.

## Requirements and acceptance

- FR-001: `web_search` returns SearXNG results and writes nothing to the graph.
- FR-002: `searxng_ingest_search` is the explicit, opt-in way to ingest results.

## Why a new spec

The repository had no local spec. The engine row `MEDULLA-UNIFIED-DATA-PLANE-R038.7.7` owns the virtual-source rule; this spec holds the connector side of it.

## Scope and interfaces

Owned: the side effects of the `web_search` and `searxng_ingest_search` tools. Not owned: search provenance records (the engine) and page selection (the engine decision method).

## Traceability

| Requirement | Design section | Test ID | Evidence |
|---|---|---|---|
| FR-001 | [plan.md](plan.md) | T-001 |  |
