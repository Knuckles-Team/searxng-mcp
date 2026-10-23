# CONN-SEARXNG-MCP-CONNECTOR-CONTENT — Design and implementation plan

Governing spec: [spec.md](spec.md).

## Architecture

`pyproject.toml` declares `searxng-mcp` as the connector identity. `create_mcp_server` resolves the packaged content of `searxng_mcp` from it.
