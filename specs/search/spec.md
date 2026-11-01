# CONN-SEARXNG-MCP-SEARCH — Web search results as a virtual source

Owner: searxng-mcp. Cross-repo IDs: `MEDULLA-UNIFIED-DATA-PLANE-R038.7.7`, `ARBORA-OPS-R067`.

## Purpose and user stories

A caller of `research.web` searches the web and selects pages to fetch. The search results are a short-lived source with provenance (query, engine, rank, time). They must not become graph records. Only the pages the caller selects are fetched and ingested.

## Why a new spec

The repository had no local spec. The engine row `MEDULLA-UNIFIED-DATA-PLANE-R038.7.7` owns the virtual-source rule; this spec holds the connector side of it.

## Scope and interfaces

Owned: the side effects of the `web_search` and `searxng_ingest_search` tools. Not owned: search provenance records (the engine) and page selection (the engine decision method).

## Delivery mapping

Component: searxng-mcp connector

Code: ../../searxng_mcp/__init__.py

## User Scenarios & Testing

### User Story 1 - Search results stay virtual (rollup) (Priority: P1)

The fleet operator and the engine rely on this behaviour of `searxng-mcp`: Search results are a short-lived source for `MEDULLA-UNIFIED-DATA-PLANE-R038.7.7`. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `searxng-mcp` connector built from the default branch, **When** `the planned test of this row` runs, **Then** see the child.

### User Story 2 - No ingest side effect (Priority: P1)

The fleet operator and the engine rely on this behaviour of `searxng-mcp`: `web_search` in `searxng_mcp/mcp_server.py` must return the SearXNG results and must not submit them to the graph. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `searxng-mcp` connector built from the default branch, **When** `tests/test_search_virtual.py::test_web_search_writes_nothing` runs, **Then** a served `web_search` call returns the results and the ingest service receives nothing.

### User Story 3 - Knowledge-base entity candidates (Priority: P1)

The fleet operator and the engine rely on this behaviour of `searxng-mcp`: The default `settings.yml` must keep the `wikidata` engine enabled. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `searxng-mcp` connector built from the default branch, **When** `tests/test_search_virtual.py::test_wikidata_engine_returns_entity_candidates` runs, **Then** test: `tests/test_search_virtual.py::test_wikidata_engine_returns_entity_candidates` loads the default settings and asserts the engine, its display types and an entity IRI result from a recorded response.

### Edge Cases

- The vendor service is unreachable or rejects the credential: the connector returns the SDK typed error and never a partial result.
- An argument outside the documented inputs is refused with the SDK typed refusal and causes no effect on the vendor service.

## Requirements

- **FR-001**: Search results stay virtual (rollup). Rows: `CONN-SEARXNG-MCP-SEARCH-R001`.
- **FR-002**: No ingest side effect. Rows: `CONN-SEARXNG-MCP-SEARCH-R001.1`.
- **FR-003**: Knowledge-base entity candidates. Rows: `CONN-SEARXNG-MCP-SEARCH-R002`.

## Success Criteria

- **SC-001**: See the child. Rows: `CONN-SEARXNG-MCP-SEARCH-R001`.
- **SC-002**: A served `web_search` call returns the results and the ingest service receives nothing. Rows: `CONN-SEARXNG-MCP-SEARCH-R001.1`.
- **SC-003**: Test: `tests/test_search_virtual.py::test_wikidata_engine_returns_entity_candidates` loads the default settings and asserts the engine, its display types and an entity IRI result from a recorded response. Rows: `CONN-SEARXNG-MCP-SEARCH-R002`.

## Assumptions

- The `searxng-mcp` package keeps the entry point and module layout named in the rows.
- The shared SDK supplies the transport, authentication, retry and certification helpers the rows reuse.

## Traceability

| Label | Rows | Design section | Test ID | Evidence |
|---|---|---|---|---|
| FR-001 | `CONN-SEARXNG-MCP-SEARCH-R001` | plan.md Production caller chain | T-001 | planned |
| FR-002 | `CONN-SEARXNG-MCP-SEARCH-R001.1` | plan.md Production caller chain | T-002 | tests/test_search_virtual.py::test_web_search_writes_nothing |
| FR-003 | `CONN-SEARXNG-MCP-SEARCH-R002` | plan.md Production caller chain | T-003 | tests/test_search_virtual.py::test_wikidata_engine_returns_entity_candidates |
