# CONN-SEARXNG-MCP-CONNECTOR-CONTENT — Requirements

Governing spec: [spec.md](spec.md).

Each row is one requirement. A row names the file it touches and the test that proves it. The generator sets each row's state in `status.json`.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R002` | **Pass through per-engine result counts and unresponsive_engines.** Pass through per-engine result counts and unresponsive_engines from the SearXNG response. Medulla abstains on the searxng competency question naming this operation until it lands. | Test: the tool result includes both fields. |
| `CONN-SEARXNG-MCP-CONNECTOR-CONTENT-R001` | **Default content.** `pyproject.toml` declares `searxng-mcp` as the single `scion_sdk.connector` entry point. The server lists the packaged `skill://` and `ontology://` resources and the packaged prompts with no `content=` argument. Proving test: `tests/test_default_content_surfaces.py`. | `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt. |
