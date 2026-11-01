# CONN-SEARXNG-MCP-CONNECTOR-CONTENT — The connector serves its packaged content

Owner: searxng-mcp. Cross-repo IDs: `SCION-CONNECTOR-CONTROL-R071`, `SCION-CONNECTOR-CONTROL-R073`.

## Purpose and user stories

The `searxng-mcp` server serves its packaged skills, prompts and ontology to any client, with no wiring of its own.

## Delivery mapping

Component: searxng-mcp connector

Code: ../../searxng_mcp/__init__.py

## User Scenarios & Testing

### User Story 1 - Pass through per-engine result counts and unresponsive_engines (Priority: P1)

The fleet operator and the engine rely on this behaviour of `searxng-mcp`: Pass through per-engine result counts and unresponsive_engines from the SearXNG response. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `searxng-mcp` connector built from the default branch, **When** `tests/test_search_virtual.py::test_unresponsive_engines_are_passed_through` runs, **Then** test: the tool result includes both fields.

### User Story 2 - Default content (Priority: P1)

The fleet operator and the engine rely on this behaviour of `searxng-mcp`: `pyproject.toml` declares `searxng-mcp` as the single `scion_sdk.connector` entry point. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `searxng-mcp` connector built from the default branch, **When** `tests/test_default_content_surfaces.py::test_default_content_surfaces` runs, **Then** `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt.

### Edge Cases

- The vendor service is unreachable or rejects the credential: the connector returns the SDK typed error and never a partial result.
- An argument outside the documented inputs is refused with the SDK typed refusal and causes no effect on the vendor service.

## Requirements

- **FR-001**: Pass through per-engine result counts and unresponsive_engines. Rows: `CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R002`.
- **FR-002**: Default content. Rows: `CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R001`.

## Success Criteria

- **SC-001**: Test: the tool result includes both fields. Rows: `CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R002`.
- **SC-002**: `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt. Rows: `CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R001`.

## Assumptions

- The `searxng-mcp` package keeps the entry point and module layout named in the rows.
- The shared SDK supplies the transport, authentication, retry and certification helpers the rows reuse.

## Why a new spec

Searched `specs/` of `searxng-mcp` with `git grep` for the terms of this spec. No other spec of this repository owns the capability, so this spec owns it.

## Traceability

| Label | Rows | Design section | Test ID | Evidence |
|---|---|---|---|---|
| FR-001 | `CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R002` | plan.md Production caller chain | T-001 | tests/test_search_virtual.py::test_unresponsive_engines_are_passed_through |
| FR-002 | `CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R001` | plan.md Production caller chain | T-002 | tests/test_default_content_surfaces.py::test_default_content_surfaces |
