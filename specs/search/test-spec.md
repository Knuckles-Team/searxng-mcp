# CONN-SEARXNG-MCP-SEARCH — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Proving test | Expected observation |
|---|---|---|---|
| T-001 | `CONN-SEARXNG-MCP-SEARCH-R001` | covered by the child rows | See the child. |
| T-002 | `CONN-SEARXNG-MCP-SEARCH-R001.1` | `tests/test_search_virtual.py::test_web_search_writes_nothing` | A served `web_search` call returns the results and the ingest service receives nothing. |
| T-003 | `CONN-SEARXNG-MCP-SEARCH-R002` | `tests/test_search_virtual.py::test_wikidata_engine_returns_entity_candidates` (planned) | Test: `tests/test_search_virtual.py::test_wikidata_engine_returns_entity_candidates` loads the default settings and asserts the engine, its display types and an entity IRI result from a recorded response. |

## Negative and boundary cases

Each proving test above includes the refusal or error case that its row names. A vendor outage or an unauthorised call must return the SDK typed error.

## Quality and release proof

Run `uv run pytest tests` and `pre-commit run --all-files` from the repository root. A planned test is added by the code change that lands the row.
