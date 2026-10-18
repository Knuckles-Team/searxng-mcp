# Searxng Mcp
## CLI or API | MCP

![PyPI - Version](https://img.shields.io/pypi/v/searxng-mcp)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')
![PyPI - Downloads](https://img.shields.io/pypi/dd/searxng-mcp)
![GitHub Repo stars](https://img.shields.io/github/stars/Knuckles-Team/searxng-mcp)
![GitHub forks](https://img.shields.io/github/forks/Knuckles-Team/searxng-mcp)
![GitHub contributors](https://img.shields.io/github/contributors/Knuckles-Team/searxng-mcp)
![PyPI - License](https://img.shields.io/pypi/l/searxng-mcp)
![GitHub](https://img.shields.io/github/license/Knuckles-Team/searxng-mcp)
![GitHub last commit (by committer)](https://img.shields.io/github/last-commit/Knuckles-Team/searxng-mcp)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Knuckles-Team/searxng-mcp)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Knuckles-Team/searxng-mcp)
![GitHub issues](https://img.shields.io/github/issues/Knuckles-Team/searxng-mcp)
![GitHub top language](https://img.shields.io/github/languages/top/Knuckles-Team/searxng-mcp)
![GitHub language count](https://img.shields.io/github/languages/count/Knuckles-Team/searxng-mcp)
![GitHub repo size](https://img.shields.io/github/repo-size/Knuckles-Team/searxng-mcp)
![GitHub repo file count (file type)](https://img.shields.io/github/directory-file-count/Knuckles-Team/searxng-mcp)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/searxng-mcp)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/searxng-mcp)

*Version: 2.3.1*

> **Documentation** — Installation, deployment, usage across the MCP tool, Python API,
> and console scripts, and guidance for provisioning the SearXNG instance are
> maintained in the [official documentation](https://knuckles-team.github.io/searxng-mcp/).

---

## Overview

**Searxng Mcp** is a production-grade Agent and Model Context Protocol (MCP) server designed to interface directly with SearXNG Search Engine MCP Server for Agentic AI!.

---

## Key Features

- **Consolidated Action-Routed MCP Tools:** Minimizes token overhead and eliminates tool bloat in LLM contexts by grouping methods into optimized, togglable tool modules.
- **Enterprise-Grade Security:** Complete support for Eunomia policies, OIDC token delegation, and granular execution context tracking.
- **Native Telemetry & Tracing:** Out-of-the-box OpenTelemetry exports and native Langfuse tracing.

---

## CLI or API

This agent wraps the SearXNG Search Engine MCP Server for Agentic AI! API. The operator can interact with it programmatically or via its integrated execution entrypoints.

Detailed instructions on how to use the underlying API wrappers, extended schema bindings, and developer SDK references are maintained in [docs/index.md](docs/index.md).

---

## MCP

This server use dynamic Action-Routed tools to optimize token overhead and maximize IDE compatibility.

### Available MCP Tools

The table below is auto-generated from the MCP server — do not edit by hand.

<!-- MCP-TOOLS-TABLE:START -->

#### Condensed action-routed tools (`MCP_TOOL_MODE=condensed`)

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `searxng_ingest_search` | `KGTOOL` | Run a SearXNG search and natively ingest its results into epistemic-graph. |
| `searxng_search_app` | `SEARCH_APPTOOL` | Launch an interactive SearXNG search-UI app: a query box, category filters, and a clickable results list, backed by the existing web_search tool through the host-mediated MCP Apps bridge. Use this when a human should see and interact with search results visually rather than read raw JSON. Does NOT drive a browser or render arbitrary web pages -- only this search workflow. |
| `searxng_settings` | `CONFIGTOOL` | Read/edit the EMBEDDED SearXNG instance's settings.yml |
| `web_search` | — | Perform a web search using a privacy-respecting SearXNG metasearch instance. |

_4 action-routed tool(s) · 0 verbose 1:1 tool(s). Each is enabled unless its `<DOMAIN>TOOL` toggle is set false; `MCP_TOOL_MODE` selects the surface (**`intent` default** — the six verb-tools, granular set loaded on demand · `condensed` action-routed · `verbose` 1:1 · `both`). Auto-generated — do not edit._
<!-- MCP-TOOLS-TABLE:END -->

Detailed tool schemas, parameter shapes, and validation constraints are preserved in [docs/usage.md](docs/usage.md).

### Dynamic Tool Selection & Visibility

This MCP server supports dynamic toolset selection and visibility filtering at runtime. This allows the operator to restrict the set of exposed tools to prevent blowing up the LLM's context window.

The operator can configure tool filtering via multiple input channels:

- **CLI Arguments:** Pass `--tools` or `--toolsets` (or their disabled counterparts `--disabled-tools` and `--disabled-toolsets`) during startup.
- **Environment Variables:** Define standard environment variables:
  - `MCP_ENABLED_TOOLS` / `MCP_DISABLED_TOOLS`
  - `MCP_ENABLED_TAGS` / `MCP_DISABLED_TAGS`
- **HTTP SSE Request Headers:** Pass custom headers during transport initialization:
  - `x-mcp-enabled-tools` / `x-mcp-disabled-tools`
  - `x-mcp-enabled-tags` / `x-mcp-disabled-tags`
- **HTTP SSE Request Query Parameters:** Append query parameters directly to the operator's transport connection URL:
  - `?tools=tool1,tool2`
  - `?tags=tag1`

When query strings or parameters are supplied, an LLM-free **Knowledge Graph resolution layer** (using `DynamicToolOrchestrator`) matches query intents against known tool tags, names, or descriptions, with safe fallback and automated 24-hour background cache refreshing.

---

### MCP Configuration Examples

<!-- MCP-CONFIG-EXAMPLES:START -->

> **Install the connector-focused `[mcp]` extra.** Examples use `searxng-mcp[mcp]` to add
> FastMCP / FastAPI through `agent-connector-sdk`; the required Agent Connector SDK core
> still carries `epistemic-graph[full]`. The `[agent-runtime]` extra additionally
> enables model orchestration.

#### stdio Transport (local IDEs — Cursor, Claude Desktop, VS Code)

```json
{
  "mcpServers": {
    "searxng-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "searxng-mcp[mcp]",
        "searxng-mcp"
      ],
      "env": {
        "MCP_TOOL_MODE": "intent",
        "SEARCH_APPTOOL": "true",
        "SEARXNG_EMBEDDED": "true",
        "SEARXNG_KG_INGEST": "true",
        "USE_RANDOM_INSTANCE": "false"
      }
    }
  }
}
```

Runtime references require an alias-aware launcher such as Arbora. Other
launchers must omit those entries and inject the resolved values through their
own runtime secret boundary.

#### Streamable-HTTP Transport (networked / production)

```json
{
  "mcpServers": {
    "searxng-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "searxng-mcp[mcp]",
        "searxng-mcp",
        "--transport",
        "streamable-http",
        "--port",
        "8000"
      ],
      "env": {
        "TRANSPORT": "streamable-http",
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "MCP_TOOL_MODE": "intent",
        "SEARCH_APPTOOL": "true",
        "SEARXNG_EMBEDDED": "true",
        "SEARXNG_KG_INGEST": "true",
        "USE_RANDOM_INSTANCE": "false"
      }
    }
  }
}
```

Alternatively, connect to a pre-deployed Streamable-HTTP instance by `url`:

```json
{
  "mcpServers": {
    "searxng-mcp": {
      "url": "http://localhost:8000/searxng-mcp/mcp"
    }
  }
}
```

Run a reviewed container image as a least-privilege stdio child (no
listener or published port):

```bash
docker run -i --rm \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=256 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  -e TRANSPORT=stdio \
  -e MCP_TOOL_MODE=intent \
  -e SEARCH_APPTOOL=true \
  -e SEARXNG_EMBEDDED=true \
  -e SEARXNG_KG_INGEST=true \
  -e USE_RANDOM_INSTANCE=false \
  registry.example.invalid/searxng-mcp@sha256:<digest> searxng-mcp
```

For containerized network HTTP, supply an authenticated TLS ingress (or
direct server TLS), exact `MCP_ALLOWED_HOSTS`, and an exact trusted-proxy
CIDR policy through the operator-owned deployment profile. The generator
does not emit an unauthenticated non-loopback listener.

_Auto-generated from the code-read env surface (`MCP_TOOL_MODE` + package vars) — do not edit._
<!-- MCP-CONFIG-EXAMPLES:END -->

<!-- BEGIN GENERATED: additional-deployment-options -->
### Additional Deployment Options

`searxng-mcp` can run as a local stdio process or container, or behind a remote
network boundary. The
[Deployment guide](https://knuckles-team.github.io/searxng-mcp/deployment/) carries
the detailed transport contract.

- **Local container** — launch a reviewed immutable image as a least-privilege
  stdio child with no listener or published port.
- **Remote URL** — connect through an operator-supplied authenticated HTTPS
  ingress. Keep its URL, outbound identity references, trust profile, and exact
  `MCP_ALLOWED_HOSTS` in `AgentConfig`.
<!-- END GENERATED: additional-deployment-options -->

## Agent

# Set credentials
export SEARXNG_URL="your_value"

# Connector-focused MCP server (includes the shared graph engine)
uv pip install "searxng-mcp[mcp]"

# Everything (development)
uv pip install "searxng-mcp[all]"      # or: python -m pip install "searxng-mcp[all]"
```

### Container images (`:mcp`)

One multi-stage `docker/Dockerfile` builds the MCP-only image (`--target mcp`):

| Image tag | Build target | Contents | Entrypoint |
|-----------|--------------|----------|------------|
| `example/searxng-mcp:mcp` | `--target mcp` | `searxng-mcp[mcp]` — **connector-focused**, includes `epistemic-graph[full]`; no model-orchestration stack | `searxng-mcp` |

```bash
docker build --target mcp   -t example/searxng-mcp:mcp    docker/   # connector-focused MCP server
