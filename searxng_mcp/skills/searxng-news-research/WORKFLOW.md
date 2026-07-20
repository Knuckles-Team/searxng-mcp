# Searxng News Research

Time-sensitive news and topic monitoring via the searxng-mcp MCP server. Use when the agent must gather what multiple news/social engines are currently reporting on a topic — breaking events, product/security announcements, or ongoing coverage — by scoping `web_search` to the `news`/`social_media` categories and paging for breadth. Do NOT use for evergreen reference facts (use searxng-web-search), academic sources (scholarx), or deep single-source reads (web-fetch).

# SearXNG News Research

News- and topic-monitoring workflow over the `searxng-mcp` server. Same `web_search`
tool as general search, but scoped to the **`news`** (and optionally `social_media`)
categories and paged to collect broad, recent coverage from many outlets at once.

## When to use
- Track breaking events or ongoing coverage of a topic across many outlets.
- Sweep recent announcements (releases, CVEs, incidents) before summarizing.
- Build a dated reading list of candidate articles to fetch and synthesize.

## When NOT to use
- Stable reference facts / general lookups → `searxng-web-search`.
- Peer-reviewed or preprint literature → `scholarx`.
- Reading / extracting one known article in full → `web-fetch` / `web-crawler`.
- Structured social-platform pulls (X/Reddit/YouTube/HN) → `pulselink-mcp`.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`searxng-mcp`** MCP server. Same env
matrix as `searxng-web-search` (`SEARXNG_INSTANCE_URL`, `USE_RANDOM_INSTANCE`,
`SEARXNG_USERNAME`/`SEARXNG_PASSWORD`, `SEARXNG_KG_INGEST`, `MCP_TOOL_MODE`). For news
freshness, prefer a self-hosted `SEARXNG_INSTANCE_URL` so JSON output is not rate-limited.

## Tools & actions
| Tool | Purpose |
|------|---------|
| `web_search` | Metasearch, scoped via `categories:["news"]`. |
| `searxng_ingest_search` | Same search + persist results to the KG (for a monitoring corpus). |

### Key parameters
- `query` — the topic/entity to monitor.
- `categories` — `["news"]` (add `"social_media"` for chatter).
- `pageno` — increment to widen coverage; news pages fall off fast, so 1–3 pages is typical.
- `language` — outlet language, default `en-US`.

## Recipes
Latest news on a topic:
```json
{"query": "openbao 2.0 release", "categories": ["news"]}
```
News + social chatter, page 2:
```json
{"query": "kubernetes 1.31 CVE", "categories": ["news", "social_media"], "pageno": 2}
```
Monitor + persist into the KG for later synthesis (via `searxng_ingest_search`):
```json
{"query": "nvidia [REDACTED_IBAN]", "categories": ["news"]}
```

## Gotchas
- Not every engine dates its results — sort/filter on `publishedDate` when present, but
  expect gaps; treat ordering as relevance, not strict recency.
- News results churn fast: capture URLs you care about immediately (or ingest them) —
  a repeat query minutes later may return a different set.
- The `news` category depends on which engines the instance enables; a locked-down
  instance may return sparse news — switch `SEARXNG_INSTANCE_URL` if coverage is thin.

## Related
- `searxng-web-search` — general (non-news) metasearch.
- `searxng-kg-ingestion` — persist a monitoring corpus into the knowledge graph.
- `web-fetch` / `web-crawler` — read the full article behind a result URL.
