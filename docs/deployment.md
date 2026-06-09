# Deployment

This page covers running `searxng-mcp` as a long-lived server: the transports, a
Docker Compose stack, the optional A2A agent server, putting it behind a Caddy reverse
proxy, and giving it a DNS name with Technitium. To provision the **SearXNG instance**
it queries, see [Backing Platform](platform.md).

> `searxng-mcp` ships an **MCP server** (console script `searxng-mcp`) and an optional
> **A2A agent server** (console script `searxng-agent`). The MCP server is a typed,
> deterministic tool surface a policy router / agent calls; the agent server wraps it
> with a Pydantic-AI graph and an Agent Web UI.

## Run the MCP server

The transport is selected with `--transport` (or the `TRANSPORT` env var):

=== "stdio (default)"

    ```bash
    searxng-mcp
    ```
    For IDE / desktop MCP clients that launch the server as a subprocess.

=== "streamable-http"

    ```bash
    searxng-mcp --transport streamable-http --host 0.0.0.0 --port 8000
    ```
    A network server with a `/health` endpoint and `/mcp` route.

=== "sse"

    ```bash
    searxng-mcp --transport sse --host 0.0.0.0 --port 8000
    ```

Health check (HTTP transports):

```bash
curl -s http://localhost:8000/health        # {"status":"OK"}
```

## Configuration (environment)

`searxng-mcp` is configured entirely from the environment. The **required** set:

| Var | Default | Meaning |
|---|---|---|
| `SEARXNG_URL` | `http://localhost:8080` | SearXNG instance base URL (alias: `SEARXNG_INSTANCE_URL`) |
| `USE_RANDOM_INSTANCE` | `false` | Select a public SearXNG instance when no URL is set |
| `SEARXNG_USERNAME` | _(unset)_ | HTTP basic-auth user (optional) |
| `SEARXNG_PASSWORD` | _(unset)_ | HTTP basic-auth password (optional) |
| `HOST` | `0.0.0.0` | Bind address for HTTP transports |
| `PORT` | `8000` | Listen port for HTTP transports |
| `TRANSPORT` | `stdio` | `stdio`, `streamable-http`, or `sse` |

The ecosystem governance and telemetry variables (`EUNOMIA_TYPE`, `ENABLE_OTEL`,
`OTEL_EXPORTER_OTLP_*`) are also read; the full set is documented in
[`.env.example`](https://github.com/Knuckles-Team/searxng-mcp/blob/main/.env.example).
Copy it to `.env` and fill in only what you use.

## Docker Compose

The repo ships [`docker/mcp.compose.yml`](https://github.com/Knuckles-Team/searxng-mcp/blob/main/docker/mcp.compose.yml).
It reads a sibling `.env` and publishes the HTTP server on `:8000`:

```yaml
services:
  searxng-mcp-mcp:
    image: knucklessg1/searxng-mcp:latest
    container_name: searxng-mcp-mcp
    hostname: searxng-mcp-mcp
    restart: always
    env_file:
      - ../.env
    environment:
      - PYTHONUNBUFFERED=1
      - HOST=0.0.0.0
      - PORT=8000
      - TRANSPORT=streamable-http
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```bash
cp .env.example .env          # then set SEARXNG_URL
docker compose -f docker/mcp.compose.yml up -d
docker compose -f docker/mcp.compose.yml logs -f
```

## Agent server

`searxng-mcp` also ships a Pydantic-AI **A2A agent server** (console script
`searxng-agent`) that connects to the MCP server and exposes the search capability over
the Agent Control Protocol and an Agent Web UI. The repo ships
[`docker/agent.compose.yml`](https://github.com/Knuckles-Team/searxng-mcp/blob/main/docker/agent.compose.yml),
which runs the MCP server and the agent together — the agent reaches the MCP server by
container name via `MCP_URL` and publishes its Web UI on `:9001`:

```bash
searxng-agent --provider openai --model-id gpt-4o
```

```yaml
services:
  searxng-mcp-mcp:
    image: knucklessg1/searxng-mcp:latest
    container_name: searxng-mcp-mcp
    hostname: searxng-mcp-mcp
    restart: always
    env_file:
      - ../.env
    environment:
      - PYTHONUNBUFFERED=1
      - HOST=0.0.0.0
      - PORT=8000
      - TRANSPORT=streamable-http
    ports:
      - "8000:8000"

  searxng-mcp-agent:
    image: knucklessg1/searxng-mcp:latest
    container_name: searxng-mcp-agent
    hostname: searxng-mcp-agent
    restart: always
    depends_on:
      - searxng-mcp-mcp
    env_file:
      - ../.env
    command: ["searxng-agent"]
    environment:
      - PYTHONUNBUFFERED=1
      - HOST=0.0.0.0
      - PORT=9001
      - MCP_URL=http://searxng-mcp-mcp:8000/mcp
      - PROVIDER=${PROVIDER:-openai}
      - MODEL_ID=${MODEL_ID:-gpt-4o}
      - ENABLE_WEB_UI=True
    ports:
      - "9001:9001"
```

```bash
docker compose -f docker/agent.compose.yml up -d
```

## Behind a Caddy reverse proxy

Expose the HTTP server on a hostname with automatic TLS. Add to your `Caddyfile`:

```caddy
# Internal (self-signed) — homelab .arpa zone
searxng-mcp.arpa {
    tls internal
    reverse_proxy searxng-mcp-mcp:8000
}
```

```caddy
# Public — automatic Let's Encrypt
searxng-mcp.example.com {
    reverse_proxy searxng-mcp-mcp:8000
}
```

Reload Caddy:

```bash
docker compose -f services/caddy/compose.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## DNS with Technitium

Point the hostname at the host running Caddy. Via the Technitium API:

```bash
curl -s "http://technitium.arpa:5380/api/zones/records/add" \
  --data-urlencode "token=$TECHNITIUM_DNS_TOKEN" \
  --data-urlencode "domain=searxng-mcp.arpa" \
  --data-urlencode "zone=arpa" \
  --data-urlencode "type=A" \
  --data-urlencode "ipAddress=10.0.0.10" \
  --data-urlencode "ttl=3600"
```

…or add an **A record** `searxng-mcp.arpa → <caddy-host-ip>` in the Technitium web
console (`http://technitium.arpa:5380`). The ecosystem
[`technitium-dns-mcp`](https://knuckles-team.github.io/technitium-dns-mcp/) automates
this as a tool.

## Register with an MCP client

Add to your client's `mcp_config.json`:

```json
{
  "mcpServers": {
    "searxng-mcp": {
      "command": "uv",
      "args": ["run", "searxng-mcp"],
      "env": {
        "SEARXNG_URL": "http://your-searxng:8080"
      }
    }
  }
}
```

For a remote HTTP server, point the client at `http://searxng-mcp.arpa/mcp` instead.
