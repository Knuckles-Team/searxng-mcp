---
name: searxng-web-search
skill_type: skill
description: >-
  Privacy-respecting web metasearch via the searxng-mcp MCP server. Use when the
  agent needs current, open-web results for a query and must NOT leak the query to a
  single tracking engine — SearXNG aggregates many engines (Google, Bing, DuckDuckGo,
  Wikipedia, …) behind one JSON tool. Use for general lookups, fact-finding, and
  pulling candidate source URLs to read next. Do NOT use for academic papers (use
  scholarx), for reading one already-known URL's full content (use web-fetch /
  web-crawler), or for keyless social/forum research (use pulselink-mcp).
license: MIT
tags: [searxng, search, metasearch, web, privacy, mcp]
metadata:
  author: Genius
  version: '0.1.0'
---
# SearXNG Web Search

Privacy-respecting **metasearch** over the `searxng-mcp` server. One `web_search`
call fans a query across many upstream engines and returns a merged, ranked JSON
result set — without exposing the query to any single tracker.

## When to use
- Answer "what's out there about X" with fresh open-web results.
- Gather candidate source URLs to hand to `web-fetch` / `web-crawler` for full reads.
- Category-scoped search: general, `news`, `science`, `it`, `files`, `images`,
  `videos`, `music`, `social_media`.

## When NOT to use
- Academic / preprint literature → `scholarx`.
- Fetch or scrape the full content of a specific known URL → `web-fetch` /
  `web-crawler`.
- Keyless social-platform research (X, Reddit, YouTube, HN) → `pulselink-mcp`.
- You want results persisted into the knowledge graph → `searxng-kg-ingestion`.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`searxng-mcp`** MCP server.

| Variable | Required | Notes |
|----------|----------|-------|
| `SEARXNG_INSTANCE_URL` | optional | Instance base URL (alias `SEARXNG_URL`). Falls back to `https://searx.be`. |
| `SEARXNG_EMBEDDED` | optional | Default `true`. With no URL configured + the `searxng-mcp[embedded]` extra installed, spawns+uses a private loopback-only instance BEFORE falling to a random/public one — see `searxng-settings-editor`. |
| `USE_RANDOM_INSTANCE` | optional | If truthy and no URL/embedded instance available, pick a random public instance from the SearXNG instances list. |
| `SEARXNG_USERNAME` / `SEARXNG_PASSWORD` | optional | HTTP basic auth for a protected instance. |
| `SEARXNG_KG_INGEST` | optional | Default-on; set falsy to disable the background KG ingest on `web_search`. |
| `MCP_TOOL_MODE` | optional | `condensed` \| `verbose` \| `both`. |

## Tools & actions
| Tool | Purpose |
|------|---------|
| `web_search` | Run a metasearch query and return the raw SearXNG JSON. |

### Key parameters
- `query` — the search string (required).
- `categories` — list, e.g. `["news"]` or `["science"]`.
- `engines` — restrict to specific engines, e.g. `["duckduckgo","wikipedia"]`.
- `language` — BCP-47ish code, default `en-US`.
- `pageno` — 1-based result page for paging deeper.

## Recipes
General search:
```json
{"query": "rootless podman vs docker rootless security"}
```
Restrict engines + language:
```json
{"query": "traefik vs caddy reverse proxy", "engines": ["duckduckgo", "wikipedia"], "language": "en-US"}
```
Page 2 of an IT-category search:
```json
{"query": "kubernetes cilium bgp", "categories": ["it"], "pageno": 2}
```

## Gotchas
- The return shape is SearXNG's raw JSON: read the `results` list (each item has
  `url`, `title`, `content`, `engine`, `category`, `score`, sometimes `publishedDate`).
  Top level also carries `number_of_results`, `suggestions`, `answers`, `infoboxes`.
- A public instance can rate-limit or block JSON `format`; set `SEARXNG_INSTANCE_URL`
  to a self-hosted instance for reliability, or enable `USE_RANDOM_INSTANCE`.
- `web_search` ingests results into the KG by default (best-effort, non-blocking).
  Disable with `SEARXNG_KG_INGEST=false` if you want a pure read.
- Results are snippets, not full pages — follow up with `web-fetch` to read a URL.

## Related
- `searxng-news-research` — the same tool tuned for time-sensitive news monitoring.
- `searxng-kg-ingestion` — persist results into the epistemic-graph knowledge graph.
- `searxng-settings-editor` — inspect/edit the embedded instance's settings.yml, or
  diagnose which instance (embedded / external / random / `searx.be`) is effective.
- `web-fetch` / `web-crawler` — read the full content behind a result URL.
