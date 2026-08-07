"""Unit tests for ``searxng_mcp.apps`` (CONCEPT:SR-ECO.ui.mcp-app-frontend).

Mirrors ``agent_utilities.mcp.tools.mcp_apps``'s own test shape
(``tests/unit/mcp/test_mcp_apps.py`` in agent-utilities): the entry-point tool
registers with the correct ``AppConfig``/``resource_uri``, returns the exact
prop shape its HTML expects on init, and the paired ``ui://`` resource returns
self-contained HTML that calls back through ``web_search`` over the postMessage
bridge -- never a raw external network/script/style load.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from searxng_mcp import apps


class _CollectingMCP:
    """Minimal FastMCP stand-in that captures ``@mcp.tool``/``@mcp.resource``
    registered functions and their config."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}
        self.tool_configs: dict[str, dict[str, Any]] = {}
        self.resources: dict[str, Any] = {}
        self.resource_configs: dict[str, dict[str, Any]] = {}

    def tool(self, *, name: str, description: str = "", tags=None, app=None):
        def _deco(fn):
            self.tools[name] = fn
            self.tool_configs[name] = {
                "description": description,
                "tags": tags,
                "app": app,
            }
            return fn

        return _deco

    def resource(
        self, *, uri: str, name: str = "", description: str = "", mime_type: str = ""
    ):
        def _deco(fn):
            self.resources[uri] = fn
            self.resource_configs[uri] = {
                "name": name,
                "description": description,
                "mime_type": mime_type,
            }
            return fn

        return _deco


@pytest.fixture
def mcp() -> _CollectingMCP:
    server = _CollectingMCP()
    apps.register_search_app_tools(server)
    return server


def test_search_app_registers_a_tool_and_matching_resource(mcp: _CollectingMCP) -> None:
    assert set(mcp.tools) == {"searxng_search_app"}
    assert set(mcp.resources) == {apps.SEARCH_APP_RESOURCE_URI}
    app_cfg = mcp.tool_configs["searxng_search_app"]["app"]
    assert app_cfg.resource_uri == apps.SEARCH_APP_RESOURCE_URI
    assert app_cfg.visibility == ["model"]


def test_search_app_disabled_via_search_apptool_toggle() -> None:
    server = _CollectingMCP()
    with patch("searxng_mcp.apps.setting", return_value=False):
        apps.register_search_app_tools(server)
    assert server.tools == {}
    assert server.resources == {}


def test_register_search_app_tools_skips_resource_on_a_tool_only_test_double() -> None:
    """Some server construction paths (mirroring server_factory.py's own
    custom_route registration and mcp_apps.py's identical guard) build against
    a minimal FastMCP stand-in exposing only ``.tool()``, not ``.resource()``
    -- registration must not raise; the resource half is just skipped."""

    class _ToolOnlyMCP:
        def __init__(self) -> None:
            self.tools: dict[str, Any] = {}

        def tool(self, *, name: str, description: str = "", tags=None, app=None):
            def _deco(fn):
                self.tools[name] = fn
                return fn

            return _deco

    server = _ToolOnlyMCP()
    apps.register_search_app_tools(server)
    assert set(server.tools) == {"searxng_search_app"}


@pytest.mark.asyncio
@pytest.mark.concept("CONCEPT:SR-ECO.ui.mcp-app-frontend")
async def test_search_app_tool_returns_query_prop(mcp: _CollectingMCP) -> None:
    result = await mcp.tools["searxng_search_app"](query="rust ownership")
    assert result == {"query": "rust ownership"}


@pytest.mark.asyncio
@pytest.mark.concept("CONCEPT:SR-ECO.ui.mcp-app-frontend")
async def test_search_app_resource_is_self_contained_and_calls_web_search(
    mcp: _CollectingMCP,
) -> None:
    html = await mcp.resources[apps.SEARCH_APP_RESOURCE_URI]()
    assert "<script>" in html
    assert "web_search" in html
    assert "mcpapp/ready" in html and "mcpapp/init" in html
    # Self-contained: no external network/script/style/font load (result URLs
    # are injected dynamically at runtime via JS, never hardcoded here).
    for banned in ("http://", "https://", "<link ", "<script src"):
        assert banned not in html
