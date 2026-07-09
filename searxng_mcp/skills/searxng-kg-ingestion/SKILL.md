---
name: searxng-kg-ingestion
skill_type: skill
description: >-
  Persist SearXNG search results into the epistemic-graph knowledge graph via the
  searxng-mcp MCP server. Use when the agent must turn a web search into durable,
  semantically-searchable KG memory — each result becomes a :Document (plus :SearchQuery
  and :SearchEngine typed nodes with :resultOf / :fromEngine links) so later reasoning
  can recall and cite it. Do NOT use for one-off reads you don't need to remember (use
  searxng-web-search) or to ingest a specific page's full text (use web-crawler).
license: MIT
tags: [searxng, ingestion, knowledge-graph, documents, mcp]
metadata:
  author: Genius
  version: '0.1.0'
---
# SearXNG KG Ingestion

Native "maximum ingestion" of SearXNG results into the ONE epistemic-graph knowledge
graph. Runs a metasearch and pushes each result as a shared **`:Document`** (carrying
the result text + `source_uri`) alongside a **`:SearchQuery`** node and per-engine
**`:SearchEngine`** nodes, wired with `:resultOf` / `:fromEngine`. This builds a
recallable, citable corpus from the open web.

## When to use
- Build durable KG memory of what the web says about a topic (for later recall/citation).
- Seed a research corpus that hub-side enrichment can chunk and embed for semantic search.
- Capture a monitoring snapshot you want to query again later, not just read once.

## When NOT to use
- Throwaway lookups you don't need to persist → `searxng-web-search`.
- Ingesting the full body of one known page → `web-crawler` / `web-fetch`.
- Structured records from an enterprise system → that system's own ingest tool.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`searxng-mcp`** MCP server. A reachable
epistemic-graph engine is required for anything to land; with no engine the tool is a
clean no-op (`ingested: null`). Same env matrix as `searxng-web-search`. Note:
`SEARXNG_KG_INGEST` (default-on) already ingests on every `web_search` — use the explicit
tool below when you want the ingest confirmation payload or ingest without a prior read.

## Tools & actions
| Tool | Purpose |
|------|---------|
| `searxng_ingest_search` | Run a search AND push results to the KG; returns `{listed, ingested}`. |
| `web_search` | Plain search; also ingests by default unless `SEARXNG_KG_INGEST=false`. |

### Key parameters (`searxng_ingest_search`)
- `query` — the search string (required); also becomes the `:SearchQuery` node.
- `categories` / `engines` / `language` / `pageno` — same semantics as `web_search`.

## Recipes
Search + ingest a topic:
```json
{"query": "zero trust network access self-hosted", "categories": ["it"]}
```
Ingest news coverage for a monitoring corpus:
```json
{"query": "cilium 1.16 release notes", "categories": ["news"]}
```

## Gotchas
- Best-effort by design: `ingested` is `null` when no engine is reachable and the search
  results are still returned — never assume persistence succeeded without checking it.
- Result `:Document` ids are `searxng:result:<url>`, so re-ingesting the same URL MERGEs
  (updates) rather than duplicating; the `:SearchQuery` id is a hash of query+language.
- Only results with usable text (title/snippet) are ingested; empty-snippet results are
  skipped. The count in `listed` may exceed the nodes actually written.
- `web_search` already ingests by default — don't double-invoke both tools for the same
  query unless you specifically want the `{listed, ingested}` confirmation.

## Related
- `searxng-web-search` / `searxng-news-research` — the read-side skills.
- `kg-ingest` (universal) — the broader knowledge-graph ingestion workflow.
- The `searxng_mcp.ontology` `searxng.ttl` defines the classes/links written here.
