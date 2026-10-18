# CONN-SEARXNG-MCP-SEARCH — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Level | Setup and input | Expected observation | Evidence |
|---|---|---|---|---|---|
| T-001 | `CONN-SEARXNG-MCP-SEARCH-R001.1` | Unit | `tests/test_search_virtual.py::test_web_search_writes_nothing` | A served `web_search` returns results and the ingest service receives nothing. |  |
