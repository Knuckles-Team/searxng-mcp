# CONN-SEARXNG-MCP-SEARCH — Quickstart

The shortest path that shows the served behaviour working.

```text
uv run pytest tests/test_search_virtual.py
```

The command starts the connector in process and calls the served tools through the MCP client. A test marked planned in `test-spec.md` runs once the code change that lands its row adds it.
