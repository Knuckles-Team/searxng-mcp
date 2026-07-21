# Backing Platform — SearXNG

`searxng-mcp` is a **client** of a [SearXNG](https://docs.searxng.org/) metasearch
instance. This page provides a Docker recipe for deploying one locally to serve as the
target of `SEARXNG_URL`. For production topologies, follow the upstream
[SearXNG documentation](https://docs.searxng.org/admin/installation-docker.html).

!!! note "Backing-system recipe"
    Each connector in the ecosystem follows the same convention — a
    `docs/platform.md` recipe for the system it integrates with, accompanied by a
    sample Compose stack that mirrors [`services/`](https://github.com/Knuckles-Team).
    Systems offered only as a managed service have no local recipe.

## Single-node deployment (Compose)

SearXNG publishes the `searxng/searxng` image. The following stack runs one instance on
`:8080` with a persistent config and result cache:

```yaml
# docker/searxng.compose.yml
services:
  searxng:
    image: docker.io/searxng/searxng@sha256:<digest>
    container_name: searxng
    hostname: searxng
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - SEARXNG_BASE_URL=http://localhost:8080/
      - UWSGI_WORKERS=6
      - UWSGI_THREADS=6
    volumes:
      - searxng_config:/etc/searxng:rw
      - searxng_data:/var/cache/searxng:rw
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/healthz"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 20s

volumes:
  searxng_config:
  searxng_data:
```

```bash
docker compose -f docker/searxng.compose.yml up -d

# Confirm the instance answers
curl -s "http://localhost:8080/search?q=test&format=json" | head -c 200
```

!!! tip "Enable the JSON API"
    SearXNG must permit the `json` response format for `searxng-mcp` to read results.
    In the generated `searxng_config/settings.yml`, ensure `json` is listed under
    `search.formats`.

## Connect searxng-mcp

```bash
export SEARXNG_URL=http://localhost:8080
searxng-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

## Combined deployment

A combined stack places SearXNG and the MCP server on one Docker network, so the server
reaches SearXNG by container name:

```yaml
# docker/stack.compose.yml
services:
  searxng:
    image: docker.io/searxng/searxng@sha256:<digest>
    hostname: searxng
    ports: ["8080:8080"]
    environment:
      - SEARXNG_BASE_URL=http://localhost:8080/
    volumes:
      - searxng_config:/etc/searxng:rw
      - searxng_data:/var/cache/searxng:rw

  searxng-mcp:
    image: example/searxng-mcp@sha256:<digest>
    depends_on: [searxng]
    environment:
      - SEARXNG_URL=http://searxng:8080
      - TRANSPORT=streamable-http
      - HOST=0.0.0.0
      - PORT=8000
    ports: ["8000:8000"]

volumes:
  searxng_config:
  searxng_data:
```

```bash
docker compose -f docker/stack.compose.yml up -d
```
