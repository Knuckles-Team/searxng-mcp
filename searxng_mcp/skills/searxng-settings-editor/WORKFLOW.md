# Searxng Settings Editor

Inspect and edit the EMBEDDED SearXNG instance's settings.yml (the private, loopback-only, zero-config search fallback the searxng-mcp server can own end to end when no external SEARXNG_URL is configured). Use when the agent or operator wants to change what the embedded instance does — enable/ disable formats, flip privacy knobs (image_proxy, enable_metrics), route outgoing requests through a proxy, or diagnose why embedded mode isn't activating. Do NOT use this for an externally-configured instance (SEARXNG_URL set) — that instance's settings.yml lives on its own host and isn't managed by this server; use `searxng-web-search` for plain queries.

# SearXNG Embedded Settings Editor

Reads and edits the **embedded** SearXNG instance's configuration
(`searxng_mcp.embedded`, CONCEPT:SR-KG.compute.embedded-instance) — the private,
loopback-only (`[REDACTED_IPV4]`) SearXNG process the `searxng-mcp` server can spawn
and own end to end when no `SEARXNG_URL`/`SEARXNG_INSTANCE_URL` is configured,
instead of falling back to a public instance.

## When to use
- Turn on/off a response format (e.g. add `csv`/`rss` alongside the default
  `html`+`json`).
- Toggle privacy knobs: `general.enable_metrics`, `server.image_proxy`,
  `search.autocomplete`, `search.favicon_resolver`.
- Route the embedded instance's outbound engine requests through a proxy
  (Tor/VPN/SOCKS) for engine-level anonymity, not just "nothing shared
  between SearXNG instances".
- Diagnose why the server is using the public `[configured-endpoint]` fallback
  instead of a private embedded instance.

## When NOT to use
- An external instance is configured (`SEARXNG_URL` set) — its settings.yml
  lives on that host, not here; this skill only ever touches the EMBEDDED
  instance's config.
- You just want to run a search → `searxng-web-search`.
- You want results persisted to the KG → `searxng-kg-ingestion`.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`searxng-mcp`** MCP server.
Embedded mode requires the `searxng-mcp[embedded]` extra
(`pip install 'searxng-mcp[embedded]'` — installs SearXNG itself from its git
source, since it ships no PyPI release) on the HOST running the MCP server.

| Variable | Required | Notes |
|----------|----------|-------|
| `SEARXNG_EMBEDDED` | optional | Default `true`. Set `false` to force the public/random fallback even with the extra installed. |
| `XDG_CONFIG_HOME` | optional | Where the user settings override lives (`$XDG_CONFIG_HOME/searxng-mcp/settings.yml`); defaults to `~/.config`. |

## Tools & actions
| Tool | Purpose |
|------|---------|
| `searxng_settings` | `get` / `set` / `reset` the embedded instance's settings.yml. |

### `searxng_settings` actions
- **`get`** — return the currently-active settings (the user override if one
  exists, else the packaged default) + which file is in effect.
- **`set`** — deep-merge `overrides_json` into the user override
  (`$XDG_CONFIG_HOME/searxng-mcp/settings.yml`, created on first use; the
  packaged default is never modified), then stop the running embedded
  instance so the NEXT search respawns it with the new settings
  (`apply_now=true`, the default). Pass `merge=false` to replace the override
  file wholesale instead of merging.
- **`reset`** — delete the user override, reverting to the packaged default
  on the next spawn.

A change never affects an ALREADY-RUNNING search mid-flight — SearXNG reads
settings.yml once at process start; `set`/`reset` restart the singleton so
the very next search picks it up.

## CLI: `searxng-doctor`
A standalone diagnostic (no MCP round-trip needed) that resolves the SAME
config the server would actually use right now:
```bash
searxng-doctor                # human-readable report
searxng-doctor --json         # machine-readable
searxng-doctor --verify       # actually spawn the embedded instance end to
                               # end and confirm it becomes healthy, then stop it
```
Prints the resolution order (explicit `SEARXNG_URL` -> embedded ->
`USE_RANDOM_INSTANCE` -> `[configured-endpoint]`), which one is currently
effective, the embedded settings.yml path + its parsed content, and (with
`--verify`) whether a real spawn actually comes up healthy. Exits non-zero on
a resolution/verification failure — use it in CI/preflight the same way as
`agent-utilities-doctor`.

## Recipes
Inspect the active config:
```json
{"action": "get"}
```
Add `csv` to the enabled formats without touching anything else:
```json
{"action": "set", "overrides_json": "{\"search\": {\"formats\": [\"html\", \"json\", \"csv\"]}}"}
```
Route embedded engine requests through Tor for engine-level anonymity:
```json
{"action": "set", "overrides_json": "{\"outgoing\": {\"proxies\": {\"all://\": [\"socks5h://[REDACTED_IPV4]:9050\"]}}}"}
```
Revert every customization:
```json
{"action": "reset"}
```
Stage a change without restarting the instance yet (e.g. batching several
`set` calls before applying once):
```json
{"action": "set", "overrides_json": "{...}", "apply_now": false}
```

## Gotchas
- `overrides_json` must decode to a JSON **object** (not a list/scalar) — it
  becomes the top-level settings.yml mapping to merge/replace.
- `set`/`reset` only affect the EMBEDDED instance. If `SEARXNG_URL` is
  configured, `searxng_settings` still reads/writes the embedded override
  file, but the running server won't be using it at all (see
  `searxng-doctor`'s `effective_source`).
- Without the `[embedded]` extra installed, every action returns
  `{"error": "searx package not installed ..."}` — check with
  `searxng-doctor` first.
- `search.formats` MUST keep `json` (the tool's query path always requests
  `?format=json`) — don't remove it via `set`, or `web_search`/
  `searxng_ingest_search` will start failing against the embedded instance.
- The packaged default settings.yml is intentionally minimal/privacy-first
  (`autocomplete`/`favicon_resolver` OFF, `image_proxy` ON, `enable_metrics`
  OFF, loopback-only bind) — `reset` always returns to that baseline, not to
  upstream SearXNG's own public-instance-oriented defaults.

## Related
- `searxng-web-search` — run an actual search (uses whichever instance
  `searxng-doctor` reports as effective).
- `searxng-kg-ingestion` — persist search results into the knowledge graph.
