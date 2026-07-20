import asyncio
import runpy
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

import searxng_mcp
from searxng_mcp.agent_server import agent_server
from searxng_mcp.mcp_server import (
    get_mcp_instance,
    get_random_searxng_instance,
    mcp_server,
)


def _setting_stub(overrides):
    """Build a stand-in for ``setting(key, default)`` driven by ``overrides``.

    The server reads its config exclusively through
    ``agent_utilities.core.config.setting`` (not module-level constants), so
    tests patch that callable to control instance URL / auth / random-instance
    behaviour. Unspecified keys fall back to the caller-supplied default.
    """

    def _stub(key, default=None):
        return overrides.get(key, default)

    return _stub


@pytest.fixture(autouse=True)
def _no_embedded_by_default():
    """Every pre-existing test in this file predates embedded-instance
    support (CONCEPT:SR-KG.compute.embedded-instance) and asserts the legacy
    public-fallback behavior — pin ``embedded_available()`` False so running
    under ``--all-extras`` (which DOES install the ``[embedded]`` extra)
    doesn't change their outcome. The tests that specifically exercise the
    embedded path patch ``embedded_enabled``/``get_embedded_instance``
    directly, bypassing this."""
    with patch("searxng_mcp.embedded.embedded_available", return_value=False):
        yield


# ==========================================
# 1. Tests for searxng_mcp/__init__.py
# ==========================================


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce")
def test_init_getattr_available():
    """Test dynamic attributes _MCP_AVAILABLE and _AGENT_AVAILABLE."""
    assert searxng_mcp._MCP_AVAILABLE is True
    assert searxng_mcp._AGENT_AVAILABLE is True


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce")
def test_init_getattr_unavailable_keys():
    """Test getattr when OPTIONAL_MODULES are missing."""
    with patch.dict(searxng_mcp.OPTIONAL_MODULES, {}, clear=True):
        assert searxng_mcp._MCP_AVAILABLE is False
        assert searxng_mcp._AGENT_AVAILABLE is False


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce")
def test_init_getattr_nonexistent():
    """Test attribute lookup failure raises AttributeError."""
    with pytest.raises(
        AttributeError, match="module 'searxng_mcp' has no attribute 'nonexistent'"
    ):
        _ = searxng_mcp.nonexistent


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce")
def test_init_dir():
    """Test __dir__ includes expected members."""
    directory = dir(searxng_mcp)
    assert "get_mcp_instance" in directory
    assert "agent_server" in directory


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce")
def test_init_import_error_handling():
    """Test import error handling in _import_module_safely."""
    with patch(
        "importlib.import_module", side_effect=ImportError("mocked import error")
    ):
        from searxng_mcp import _import_module_safely

        assert _import_module_safely("some_module") is None


# ==========================================
# 2. Tests for searxng_mcp/__main__.py
# ==========================================


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-3")
@patch("searxng_mcp.agent_server.agent_server")
def test_main_execution(mock_agent_server):
    """Test running searxng_mcp module executes the agent server."""
    with patch.object(sys, "argv", ["searxng-mcp"]):
        runpy.run_module("searxng_mcp", run_name="__main__")
        mock_agent_server.assert_called_once()


# ==========================================
# 3. Tests for searxng_mcp/agent_server.py
# ==========================================


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-2")
@patch("agent_utilities.create_agent_server")
@patch("agent_utilities.initialize_workspace")
@patch("agent_utilities.load_identity")
def test_agent_server(mock_load_identity, mock_initialize, mock_create_server):
    """Test starting the agent server with parsed CLI arguments."""
    mock_load_identity.return_value = {
        "name": "Test Searxng Mcp",
        "description": "Test Description",
        "content": "Test Prompt",
    }
    with patch.object(sys, "argv", ["agent_server", "--debug"]):
        agent_server()
        mock_initialize.assert_called_once()
        mock_load_identity.assert_called_once()
        mock_create_server.assert_called_once()


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-2")
@patch("agent_utilities.create_agent_server")
@patch("agent_utilities.initialize_workspace")
@patch("agent_utilities.load_identity")
def test_agent_server_main_execution(
    mock_load_identity, mock_initialize, mock_create_server
):
    """Test running searxng_mcp.agent_server module as main."""
    mock_load_identity.return_value = {
        "name": "Test Searxng Mcp",
        "description": "Test Description",
        "content": "Test Prompt",
    }
    with patch.object(sys, "argv", ["agent_server", "--debug"]):
        runpy.run_module("searxng_mcp.agent_server", run_name="__main__")
        mock_initialize.assert_called_once()
        mock_load_identity.assert_called_once()
        mock_create_server.assert_called_once()


# ==========================================
# 4. Tests for searxng_mcp/mcp_server.py
# ==========================================


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-5")
@patch("searxng_mcp.mcp_server.requests.get")
def test_get_random_searxng_instance_success(mock_get):
    """Test fetching random SearXNG instance with valid response."""
    mock_response = MagicMock()
    mock_response.text = """
    https://searx.be:
      comments: []
      network_type: normal
    https://searx.me:
      comments: ["hidden"]
    """
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    instance = get_random_searxng_instance()
    assert instance == "https://searx.be"


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-5")
@patch("searxng_mcp.mcp_server.requests.get")
def test_get_random_searxng_instance_empty(mock_get):
    """Test fetching random SearXNG instance when standard instances list is empty."""
    mock_response = MagicMock()
    mock_response.text = "{}"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    with pytest.raises(ValueError, match="Failed to fetch SearXNG instances list"):
        get_random_searxng_instance()


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-5")
@patch("searxng_mcp.mcp_server.requests.get")
def test_get_random_searxng_instance_failure(mock_get):
    """Test fetching random SearXNG instance raises failure on request exception."""
    mock_get.side_effect = requests.RequestException("Network error")
    with pytest.raises(ValueError, match="Failed to fetch SearXNG instances list"):
        get_random_searxng_instance()


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
def test_search_prompt():
    """Test registering search prompt."""
    mcp, _, _, _ = get_mcp_instance()
    prompts = asyncio.run(mcp.list_prompts())
    assert len(prompts) > 0
    search_prompt = next(p for p in prompts if p.name == "search")
    res = search_prompt.fn("hello")
    assert res == "Searching the web for: hello."


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
@pytest.mark.asyncio
@patch("searxng_mcp.mcp_server.requests.get")
async def test_web_search_default(mock_get):
    """Test web_search tool with default values."""
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    web_search_tool = next(t for t in tools if t.name == "web_search")

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"title": "Example"}]}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    # Explicitly pass all parameters to prevent Pydantic Field default descriptors (FieldInfo objects)
    with patch("searxng_mcp.mcp_server.setting", _setting_stub({})):
        res = await web_search_tool.fn(
            query="test query",
            categories=None,
            engines=None,
            language="en-US",
            pageno=1,
            ctx=None,
        )
    assert "results" in res
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "https://searx.be/search" in args[0]
    assert kwargs["params"]["q"] == "test query"


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
@pytest.mark.asyncio
@patch("searxng_mcp.mcp_server.requests.get")
async def test_web_search_custom(mock_get):
    """Test web_search tool with custom params and context."""
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    web_search_tool = next(t for t in tools if t.name == "web_search")

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    mock_ctx = MagicMock()
    mock_ctx.info = AsyncMock()

    with patch(
        "searxng_mcp.mcp_server.setting",
        _setting_stub({"SEARXNG_INSTANCE_URL": "https://custom.searxng.org/"}),
    ):
        res = await web_search_tool.fn(
            query="test",
            categories=["general", "news"],
            engines=["google", "bing"],
            language="en-US",
            pageno=2,
            ctx=mock_ctx,
        )
    assert res == {"results": []}
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "https://custom.searxng.org/search" in args[0]
    assert kwargs["params"]["categories"] == "general,news"
    assert kwargs["params"]["engines"] == "google,bing"
    mock_ctx.info.assert_called_once_with("Performing configured SearXNG search...")


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
@pytest.mark.asyncio
@patch("searxng_mcp.mcp_server.requests.get")
async def test_web_search_random_instance(mock_get):
    """Test web_search tool with random instance enabled."""
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    web_search_tool = next(t for t in tools if t.name == "web_search")

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    with (
        patch(
            "searxng_mcp.mcp_server.setting",
            _setting_stub({"USE_RANDOM_INSTANCE": True}),
        ),
        patch(
            "searxng_mcp.mcp_server.get_random_searxng_instance",
            return_value="https://random.searx.be",
        ),
    ):
        res = await web_search_tool.fn(
            query="test",
            categories=None,
            engines=None,
            language="en-US",
            pageno=1,
            ctx=None,
        )

    assert res == {"results": []}
    args, kwargs = mock_get.call_args
    assert "https://random.searx.be/search" in args[0]


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
@pytest.mark.asyncio
@patch("searxng_mcp.mcp_server.requests.get")
async def test_web_search_random_instance_failure(mock_get):
    """Test web_search tool default when random instance selection fails."""
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    web_search_tool = next(t for t in tools if t.name == "web_search")

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    with (
        patch(
            "searxng_mcp.mcp_server.setting",
            _setting_stub({"USE_RANDOM_INSTANCE": True}),
        ),
        patch(
            "searxng_mcp.mcp_server.get_random_searxng_instance",
            side_effect=ValueError("Test Failure"),
        ),
    ):
        res = await web_search_tool.fn(
            query="test",
            categories=None,
            engines=None,
            language="en-US",
            pageno=1,
            ctx=None,
        )

    assert res == {"results": []}
    args, kwargs = mock_get.call_args
    assert "https://searx.be/search" in args[0]


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
@pytest.mark.asyncio
@patch("searxng_mcp.mcp_server.requests.get")
async def test_web_search_basic_auth(mock_get):
    """Test web_search tool with basic auth config."""
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    web_search_tool = next(t for t in tools if t.name == "web_search")

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    with patch(
        "searxng_mcp.mcp_server.setting",
        _setting_stub({"SEARXNG_USERNAME": "admin", "SEARXNG_PASSWORD": "secret"}),
    ):
        res = await web_search_tool.fn(
            query="test",
            categories=None,
            engines=None,
            language="en-US",
            pageno=1,
            ctx=None,
        )

    assert res == {"results": []}
    args, kwargs = mock_get.call_args
    assert kwargs["auth"] == ("admin", "secret")


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
@pytest.mark.asyncio
@patch("searxng_mcp.mcp_server.requests.get")
async def test_web_search_failure(mock_get):
    """Test web_search tool failure handling."""
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    web_search_tool = next(t for t in tools if t.name == "web_search")

    mock_get.side_effect = Exception("Request timeout")
    res = await web_search_tool.fn(
        query="test",
        categories=None,
        engines=None,
        language="en-US",
        pageno=1,
        ctx=None,
    )
    assert "error" in res
    assert "Failed to perform search: Request timeout" in res["error"]


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
@pytest.mark.asyncio
@patch("searxng_mcp.mcp_server.requests.get")
async def test_web_search_prefers_embedded_over_public_fallback(mock_get):
    """No explicit config, embedded available+enabled -> use the embedded URL
    instead of the public searx.be fallback (CONCEPT:SR-KG.compute.embedded-instance)."""
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    web_search_tool = next(t for t in tools if t.name == "web_search")

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    with (
        patch("searxng_mcp.mcp_server.setting", _setting_stub({})),
        patch("searxng_mcp.embedded.embedded_enabled", return_value=True),
        patch(
            "searxng_mcp.embedded.get_embedded_instance",
            return_value=MagicMock(
                ensure_running=MagicMock(return_value="http://127.0.0.1:18888")
            ),
        ),
    ):
        res = await web_search_tool.fn(
            query="test",
            categories=None,
            engines=None,
            language="en-US",
            pageno=1,
            ctx=None,
        )
    assert res == {"results": []}
    args, _kwargs = mock_get.call_args
    assert "http://127.0.0.1:18888/search" in args[0]


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
@pytest.mark.asyncio
@patch("searxng_mcp.mcp_server.requests.get")
async def test_web_search_falls_back_to_searx_be_when_embedded_disabled(mock_get):
    """embedded_enabled()=False (extra not installed, or SEARXNG_EMBEDDED=false)
    -> unchanged behavior, falls straight through to the public fallback."""
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    web_search_tool = next(t for t in tools if t.name == "web_search")

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    with (
        patch("searxng_mcp.mcp_server.setting", _setting_stub({})),
        patch("searxng_mcp.embedded.embedded_enabled", return_value=False),
    ):
        res = await web_search_tool.fn(
            query="test",
            categories=None,
            engines=None,
            language="en-US",
            pageno=1,
            ctx=None,
        )
    assert res == {"results": []}
    args, _kwargs = mock_get.call_args
    assert "https://searx.be/search" in args[0]


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-4")
@pytest.mark.asyncio
@patch("searxng_mcp.mcp_server.requests.get")
async def test_web_search_degrades_when_embedded_start_fails(mock_get):
    """A best-effort startup failure degrades to the public fallback rather
    than breaking search."""
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    web_search_tool = next(t for t in tools if t.name == "web_search")

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    with (
        patch("searxng_mcp.mcp_server.setting", _setting_stub({})),
        patch("searxng_mcp.embedded.embedded_enabled", return_value=True),
        patch(
            "searxng_mcp.embedded.get_embedded_instance",
            return_value=MagicMock(
                ensure_running=MagicMock(side_effect=RuntimeError("boom"))
            ),
        ),
    ):
        res = await web_search_tool.fn(
            query="test",
            categories=None,
            engines=None,
            language="en-US",
            pageno=1,
            ctx=None,
        )
    assert res == {"results": []}
    args, _kwargs = mock_get.call_args
    assert "https://searx.be/search" in args[0]


@pytest.mark.concept("CONCEPT:SR-KG.compute.embedded-instance")
@pytest.mark.asyncio
async def test_searxng_settings_get_returns_active_settings():
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    settings_tool = next(t for t in tools if t.name == "searxng_settings")

    with (
        patch("searxng_mcp.embedded.embedded_available", return_value=True),
        patch(
            "searxng_mcp.embedded.read_settings",
            return_value={"search": {"formats": ["html", "json"]}},
        ),
        patch(
            "searxng_mcp.embedded.user_settings_path",
            return_value=MagicMock(is_file=MagicMock(return_value=False)),
        ),
    ):
        res = await settings_tool.fn(
            action="get", overrides_json="", merge=True, apply_now=True
        )
    assert res["action"] == "get"
    assert res["settings"]["search"]["formats"] == ["html", "json"]


@pytest.mark.concept("CONCEPT:SR-KG.compute.embedded-instance")
@pytest.mark.asyncio
async def test_searxng_settings_set_merges_and_restarts_the_instance():
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    settings_tool = next(t for t in tools if t.name == "searxng_settings")

    fake_instance = MagicMock()
    with (
        patch("searxng_mcp.embedded.embedded_available", return_value=True),
        patch(
            "searxng_mcp.embedded.write_user_settings",
            return_value="/fake/settings.yml",
        ) as mock_write,
        patch(
            "searxng_mcp.embedded.read_settings",
            return_value={"general": {"enable_metrics": True}},
        ),
        patch("searxng_mcp.embedded.get_embedded_instance", return_value=fake_instance),
    ):
        res = await settings_tool.fn(
            action="set",
            overrides_json='{"general": {"enable_metrics": true}}',
            merge=True,
            apply_now=True,
        )
    mock_write.assert_called_once_with(
        {"general": {"enable_metrics": True}}, merge=True
    )
    fake_instance.stop.assert_called_once()
    assert res["action"] == "set"
    assert res["restart_pending"] is False


@pytest.mark.concept("CONCEPT:SR-KG.compute.embedded-instance")
@pytest.mark.asyncio
async def test_searxng_settings_set_apply_now_false_skips_restart():
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    settings_tool = next(t for t in tools if t.name == "searxng_settings")

    fake_instance = MagicMock()
    with (
        patch("searxng_mcp.embedded.embedded_available", return_value=True),
        patch(
            "searxng_mcp.embedded.write_user_settings",
            return_value="/fake/settings.yml",
        ),
        patch("searxng_mcp.embedded.read_settings", return_value={}),
        patch("searxng_mcp.embedded.get_embedded_instance", return_value=fake_instance),
    ):
        res = await settings_tool.fn(
            action="set", overrides_json="{}", merge=True, apply_now=False
        )
    fake_instance.stop.assert_not_called()
    assert res["restart_pending"] is True


@pytest.mark.concept("CONCEPT:SR-KG.compute.embedded-instance")
@pytest.mark.asyncio
async def test_searxng_settings_set_rejects_invalid_json():
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    settings_tool = next(t for t in tools if t.name == "searxng_settings")

    with patch("searxng_mcp.embedded.embedded_available", return_value=True):
        res = await settings_tool.fn(
            action="set", overrides_json="not json", merge=True, apply_now=True
        )
    assert "error" in res


@pytest.mark.concept("CONCEPT:SR-KG.compute.embedded-instance")
@pytest.mark.asyncio
async def test_searxng_settings_reset_reverts_and_restarts():
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    settings_tool = next(t for t in tools if t.name == "searxng_settings")

    fake_instance = MagicMock()
    with (
        patch("searxng_mcp.embedded.embedded_available", return_value=True),
        patch("searxng_mcp.embedded.reset_user_settings", return_value=True),
        patch("searxng_mcp.embedded.read_settings", return_value={}),
        patch("searxng_mcp.embedded.get_embedded_instance", return_value=fake_instance),
    ):
        res = await settings_tool.fn(
            action="reset", overrides_json="", merge=True, apply_now=True
        )
    assert res == {"action": "reset", "removed": True, "settings": {}}
    fake_instance.stop.assert_called_once()


@pytest.mark.concept("CONCEPT:SR-KG.compute.embedded-instance")
@pytest.mark.asyncio
async def test_searxng_settings_without_the_embedded_extra_is_informational():
    mcp, _, _, _ = get_mcp_instance()
    tools = await mcp.list_tools()
    settings_tool = next(t for t in tools if t.name == "searxng_settings")

    with patch("searxng_mcp.embedded.embedded_available", return_value=False):
        res = await settings_tool.fn(
            action="get", overrides_json="", merge=True, apply_now=True
        )
    assert "error" in res


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-6")
@pytest.mark.parametrize(
    "transport,expected_kwargs",
    [
        ("stdio", {"transport": "stdio"}),
        ("sse", {"transport": "sse", "host": "localhost", "port": 8000}),
        (
            "streamable-http",
            {"transport": "streamable-http", "host": "localhost", "port": 8000},
        ),
    ],
)
@patch("searxng_mcp.mcp_server.get_mcp_instance")
def test_mcp_server_run_transports(mock_get_instance, transport, expected_kwargs):
    """Test mcp_server startup with various transports."""
    mock_mcp = MagicMock()
    mock_mcp.run = MagicMock()
    mock_args = MagicMock()
    mock_args.transport = transport
    mock_args.auth_type = "none"
    mock_args.host = "localhost"
    mock_args.port = 8000
    mock_get_instance.return_value = (mock_mcp, mock_args, [], ["tag"])

    mcp_server()
    mock_mcp.run.assert_called_once_with(**expected_kwargs)


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-6")
@patch("searxng_mcp.mcp_server.get_mcp_instance")
def test_mcp_server_run_invalid_transport(mock_get_instance):
    """Test mcp_server startup fails with invalid transport."""
    mock_mcp = MagicMock()
    mock_args = MagicMock()
    mock_args.transport = "invalid"
    mock_args.auth_type = "none"
    mock_get_instance.return_value = (mock_mcp, mock_args, [], [])

    with pytest.raises(SystemExit):
        mcp_server()


@pytest.mark.concept("CONCEPT:SR-KG.compute.ce-3")
@patch("fastmcp.FastMCP.run")
def test_mcp_server_main_execution(mock_run):
    """Test running searxng_mcp.mcp_server module as main."""
    runpy.run_module("searxng_mcp.mcp_server", run_name="__main__")
    mock_run.assert_called_once_with(transport="stdio")
