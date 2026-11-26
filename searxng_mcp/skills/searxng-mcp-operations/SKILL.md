---
name: searxng-mcp-operations
skill_type: skill
description: >-
  Operate searxng-mcp through its governed MCP and Arbora capabilities, including searxng kg ingestion, searxng news research, searxng settings editor, searxng web search. Use when a request requires this provider's read, change, automation, ingestion, troubleshooting, or evidence workflows.
---

# Searxng Mcp Operations

Use the provider's governed MCP tools through Arbora delegation.

## Workflow

1. Establish the verified GraphSession and tenant before discovery or retrieval.
2. Discover the current condensed tool surface; never assume a stale tool name or schema.
3. Prefer read-only inspection first. For changes, present impact and use the provider's
   dry-run or preview mode when available.
4. Execute mutations as fenced WorkItems so retries remain idempotent and auditable.
5. Ingest source data only through the signed connector preset and ChangeEnvelope path.
6. Verify the durable result and its trace/evidence before reporting completion.

## Steps

1. Establish the verified GraphSession and tenant, and discover the tool surface with the fleet `find` call.
   Verify `web_search` is listed.
2. Run a read-only call first, such as `web_search` with a `query`.
   Verify the response has a `results` list.
3. For a settings change, preview impact and edit with `searxng_settings`.
   Verify the active configuration with `get` before and after.
4. Ingest only through the signed connector preset, for example `searxng_ingest_search`.
   Verify the response reports `listed` and `ingested`.
5. Confirm the durable result with a read such as `searxng_settings` (`action` get) and cite the trace.
   Verify the evidence matches the request before reporting.

## Failure recovery

| Failure | Cause | Recovery |
|---------|-------|----------|
| Tool name or schema not found | The tool list was assumed rather than discovered | Rediscover the condensed tool surface through the fleet `find` call, and use the exact name returned |
| Unknown ACL or tenant state | Governance prerequisites are absent | Treat it as a hard failure, report it, and ask the operator to supply them |
| `ingested` is null | No medulla engine is reachable | Report that nothing was written, and rerun `searxng_ingest_search` once the engine is reachable |

## Safety contract

- Never persist credentials, endpoints, raw personal identifiers, hostnames, or local paths.
- Resolve TLS trust and verification from environment/configuration; never hardcode bypasses.
- Treat unknown ACL, tenant, schema, or tool-contract state as a hard failure.
- Require explicit approval for destructive, externally visible, or irreversible actions.
- Keep runtime traces policy-scoped and privacy-sanitized.

## Specialized workflows

Read [the workflow catalog](references/catalog.md) only when the request needs a
provider-specific procedure, parameter map, script, or reference asset.
