# Usage — MCP / API / CLI

`searxng-mcp` exposes the same capability three ways: as an **MCP tool** an agent
calls, as a **Python API** you import, and as **console scripts** you run. The
ecosystem role and the standardized package pattern are in [Overview](overview.md).

## As an MCP server

Once [deployed](deployment.md), the server registers the `web_search` tool. It needs no
configuration beyond a reachable SearXNG instance (or `USE_RANDOM_INSTANCE=true`).

| Tool | Parameters | Returns |
|---|---|---|
| `web_search` | `query`, `categories?`, `engines?`, `language?`, `pageno?` | SearXNG JSON result set |

The tool accepts:

- `query` — the search string submitted to SearXNG.
- `categories` — optional list (`general`, `news`, `science`, `files`, `images`,
  `videos`, `music`, `it`, `social_media`).
- `engines` — optional list of specific search engines.
- `language` — a language code such as `en-US` (default `en-US`).
- `pageno` — the result page to fetch (default `1`).

Example agent prompts that map onto the tool:

- *"Search the web for the latest SearXNG release notes"* → `web_search`
- *"Find recent news articles about privacy-respecting search"* → `web_search` with `categories=["news"]`
- *"Look up images of the Material for MkDocs theme"* → `web_search` with `categories=["images"]`

## As a Python API

The search capability is implemented in `searxng_mcp.mcp_server`. You can perform a
search directly against any SearXNG instance with `requests`:

```python
import requests

instance_url = "http://localhost:8080"      # your SEARXNG_URL
response = requests.get(
    f"{instance_url}/search",
    params={
        "q": "privacy respecting search",
        "format": "json",
        "language": "en-US",
        "pageno": 1,
        "categories": "general,news",
    },
    timeout=15,
)
response.raise_for_status()
results = response.json()                    # SearXNG JSON result set
for hit in results.get("results", []):
    print(hit["title"], hit["url"])
```

To let the package pick a public SearXNG instance for you (the behaviour behind
`USE_RANDOM_INSTANCE=true`):

```python
from searxng_mcp.mcp_server import get_random_searxng_instance

instance_url = get_random_searxng_instance()   # a vetted public instance
```

## As a CLI

The package installs two console scripts.

### `searxng-mcp` — the MCP server

```bash
searxng-mcp --help
searxng-mcp                                          # stdio (default)
searxng-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

### `searxng-agent` — the A2A agent server

```bash
export SEARXNG_URL=http://localhost:8080
searxng-agent --provider openai --model-id gpt-4o   # ACP + Agent Web UI
```

The agent connects to the MCP server (via `MCP_URL` or `mcp_config.json`) and exposes
the search capability conversationally. See [Deployment](deployment.md#agent-server)
for the combined Compose stack.
