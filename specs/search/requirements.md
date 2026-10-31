# CONN-SEARXNG-MCP-SEARCH — Requirements

Governing spec: [spec.md](spec.md).

Each row is one requirement. A child row `.n` is one five-minute unit of work. A row names the file it touches and the test that proves it. The generator sets each row's state in `status.json`.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-SEARXNG-MCP-SEARCH-R001` | **Search results stay virtual (rollup).** Search results are a short-lived source for `MEDULLA-UNIFIED-DATA-PLANE-R038.7.7`. Child `.1` delivers it. | See the child. |
| `CONN-SEARXNG-MCP-SEARCH-R001.1` | **No ingest side effect.** `web_search` in `searxng_mcp/mcp_server.py` must return the SearXNG results and must not submit them to the graph. `searxng_ingest_search` stays the explicit, opt-in ingest tool. Proving test: `tests/test_search_virtual.py::test_web_search_writes_nothing`. | A served `web_search` call returns the results and the ingest service receives nothing. |
| `CONN-SEARXNG-MCP-SEARCH-R002` | **Knowledge-base entity candidates.** The default `settings.yml` must keep the `wikidata` engine enabled. Its `display_type` must include `list`, so entity matches return as search results. Each result carries the entity IRI as its URL. Results stay virtual (R001). It serves `MEDULLA-DECISION-ENGINE-R099`. | Test: `tests/test_search_virtual.py::test_wikidata_engine_returns_entity_candidates` loads the default settings and asserts the engine, its display types and an entity IRI result from a recorded response. |
