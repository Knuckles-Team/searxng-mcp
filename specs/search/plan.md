# CONN-SEARXNG-MCP-SEARCH — Design and implementation plan

Governing spec: [spec.md](spec.md).

## Existing system and reuse

`web_search` and `searxng_ingest_search` share `_perform_search` in `searxng_mcp/mcp_server.py`. `searxng_ingest_search` already ingests explicitly through `searxng_mcp/kg_ingest.py`.

## Architecture

`_perform_search` only queries SearXNG. Ingest happens only in `searxng_ingest_search`. The `SEARXNG_KG_INGEST` setting is removed with the side effect it controlled.
