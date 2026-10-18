"""Search results stay a virtual source (CONN-SEARXNG-MCP-SEARCH-R001.1)."""

from __future__ import annotations

import importlib
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastmcp import Client

import searxng_mcp.kg_ingest as kg_ingest

server_module = importlib.import_module("searxng_mcp.mcp_server")


@pytest.mark.spec("CONN-SEARXNG-MCP-SEARCH-R001.1")
async def test_web_search_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    results = {
        "results": [{"url": "https://a.example/pdb", "title": "A", "engine": "bing"}]
    }
    response = MagicMock()
    response.json.return_value = results
    response.raise_for_status.return_value = None
    monkeypatch.setattr(server_module.requests, "get", lambda *_args, **_kwargs: response)
    monkeypatch.setenv("SEARXNG_INSTANCE_URL", "https://searx.example")
    monkeypatch.setattr("sys.argv", ["searxng-mcp"])
    ingested: list[Any] = []

    async def record(*args: Any, **kwargs: Any) -> dict[str, int]:
        ingested.append(args)
        return {"nodes": 1}

    monkeypatch.setattr(kg_ingest, "ingest_search_results", record)
    mcp, _args, _mw, _tags = server_module.get_mcp_instance()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "web_search", {"query": "pod disruption budget"}
        )
    body = result.structured_content or {}
    assert (
        body.get("results", body.get("result", {}).get("results")) == results["results"]
    )
    assert ingested == []
