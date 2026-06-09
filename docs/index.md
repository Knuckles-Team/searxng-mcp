# searxng-mcp

A privacy-respecting **metasearch API + MCP Server** (with an optional A2A agent) for
the agent-utilities ecosystem — query the web across many search engines through one
deterministic tool surface.

!!! info "Official documentation"
    This site is the canonical reference for `searxng-mcp`, maintained alongside every
    release.

[![PyPI](https://img.shields.io/pypi/v/searxng-mcp)](https://pypi.org/project/searxng-mcp/)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')
[![License](https://img.shields.io/pypi/l/searxng-mcp)](https://github.com/Knuckles-Team/searxng-mcp/blob/main/LICENSE)
[![GitHub](https://img.shields.io/badge/source-GitHub-181717?logo=github)](https://github.com/Knuckles-Team/searxng-mcp)

## Overview

`searxng-mcp` wraps a [SearXNG](https://docs.searxng.org/) metasearch instance with a
typed, deterministic MCP tool surface, and ships an optional Pydantic-AI agent server
for autonomous and conversational use. It provides:

- **A `web_search` MCP tool** — a single, well-documented search action that accepts a
  query, optional categories, engines, language, and pagination, and returns SearXNG's
  JSON result set.
- **An optional A2A agent server** (`searxng-agent` console script) that exposes the
  search capability over the Agent Control Protocol and an Agent Web UI.
- **Zero-credential operation** — point it at any SearXNG instance, or let it select a
  public instance automatically; results degrade to a clear error rather than raising
  when an instance is unreachable.

## Explore the documentation

<div class="grid cards" markdown>

- :material-rocket-launch: **[Installation](installation.md)** — pip, source, extras, and the prebuilt Docker image.
- :material-server-network: **[Deployment](deployment.md)** — run the MCP and agent servers, Docker Compose, Caddy + Technitium.
- :material-console: **[Usage](usage.md)** — the `web_search` tool, the Python API, and the console scripts.
- :material-magnify: **[Backing Platform](platform.md)** — deploy SearXNG with Docker.
- :material-sitemap: **[Overview](overview.md)** — the ecosystem role and the standardized package pattern.
- :material-tag-multiple: **[Concepts](concepts.md)** — the `CONCEPT:SRX-*` registry.

</div>

## Quick start

```bash
pip install "searxng-mcp[mcp]"
searxng-mcp                       # stdio MCP server (default transport)
```

Point it at a SearXNG instance and run an HTTP server:

```bash
export SEARXNG_URL=http://localhost:8080
searxng-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

See **[Installation](installation.md)** and **[Deployment](deployment.md)** for the
full matrix (PyPI extras, Docker image, all transports, the agent server, reverse
proxy, DNS).
