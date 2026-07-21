# Installation

`searxng-mcp` is a standard Python package and a prebuilt container image. Pick the
path that matches how you want to run it.

## Requirements

- **Python 3.11 – 3.14**.
- A reachable **SearXNG instance** — see [Backing Platform](platform.md) to deploy one
  locally, or set `USE_RANDOM_INSTANCE=true` to select a public instance automatically.

## From PyPI (recommended)

```bash
pip install searxng-mcp
```

### Optional extras

The base install is intentionally minimal. Install the extra for what you need:

| Extra | Install | Pulls in |
|---|---|---|
| `mcp` | `pip install "searxng-mcp[mcp]"` | FastMCP MCP-server runtime (`agent-utilities[mcp]`) |
| `agent` | `pip install "searxng-mcp[agent]"` | Pydantic-AI agent + Logfire tracing (`agent-utilities[agent-runtime,logfire]`) |
| `all` | `pip install "searxng-mcp[all]"` | The MCP server and the agent together |
| `test` | `pip install "searxng-mcp[test]"` | `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-xdist` |

```bash
# Typical: run the MCP server and the A2A agent
pip install "searxng-mcp[all]"
```

## From source

```bash
git clone https://github.com/Knuckles-Team/searxng-mcp.git
cd searxng-mcp
pip install -e ".[all]"          # editable install with every extra
```

With [`uv`](https://docs.astral.sh/uv/):

```bash
uv pip install -e ".[all]"
uv run searxng-mcp
```

## Prebuilt Docker image

A multi-stage runtime image is published on every release (entrypoint `searxng-mcp`):

```bash
docker pull example/searxng-mcp@sha256:<digest>

docker run --rm -i \
  -e SEARXNG_URL=http://your-searxng:8080 \
  example/searxng-mcp@sha256:<digest>        # stdio transport (default)
```

For an HTTP server with a published port and the agent server, see
[Deployment](deployment.md).

## Verify the install

```bash
searxng-mcp --help
python -c "import searxng_mcp; print(searxng_mcp.__version__)"
```

## Next steps

- **[Deployment](deployment.md)** — run it as a long-lived MCP server (and agent) behind Caddy + DNS.
- **[Usage](usage.md)** — call the tool, the Python API, and the console scripts.
- **[Configuration](deployment.md#configuration-environment)** — every environment variable.
