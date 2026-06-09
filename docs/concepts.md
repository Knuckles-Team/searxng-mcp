# Concept Registry — searxng-mcp

> **Prefix**: `CONCEPT:SRX-*`
> **Version**: 0.14.0
> **Bridge**: [`CONCEPT:ECO-4.0`](https://knuckles-team.github.io/agent-utilities/concepts/) (Unified Toolkit Ingestion)

---

## Project-Specific Concepts

| Concept ID | Name | Description |
|------------|------|-------------|
| `CONCEPT:SRX-001` | Core API Client | Primary API client for SearXNG Search Engine MCP Server for Agentic AI! |
| `CONCEPT:SRX-002` | MCP Server | Model Context Protocol server entry point |
| `CONCEPT:SRX-003` | A2A Agent | Agent-to-Agent protocol server |

## Cross-Project References (from agent-utilities)

| Concept ID | Name | Origin |
|------------|------|--------|
| `CONCEPT:ECO-4.0` | Unified Toolkit Ingestion | agent-utilities |
| `CONCEPT:ORCH-1.2` | Confidence-Gated Router | agent-utilities |
| `CONCEPT:OS-5.1` | Prompt Injection Defense | agent-utilities |
| `CONCEPT:OS-5.2` | Cognitive Scheduler | agent-utilities |
| `CONCEPT:OS-5.3` | Guardrail Engine | agent-utilities |
| `CONCEPT:OS-5.4` | Audit Logging | agent-utilities |
| `CONCEPT:KG-2.0` | Knowledge Graph Core | agent-utilities |

## Synergy with agent-utilities

This project integrates with `agent-utilities` via `CONCEPT:ECO-4.0` (Unified Toolkit Ingestion). The `searxng_mcp` MCP server registers its tools with the agent-utilities FastMCP middleware, enabling automatic discovery, telemetry, and Knowledge Graph ingestion of all SRX-* concepts.
