import pytest
from searxng_mcp.mcp_server import get_mcp_instance
from fastmcp import FastMCP

def test_mcp_instance_creation():
    """Test that the MCP instance can be created successfully."""
    mcp, args, middlewares, registered_tags = get_mcp_instance()
    assert isinstance(mcp, FastMCP)
    assert "searxng" in mcp.name

def test_import_searxng_mcp():
    """Test that the package can be imported."""
    import searxng_mcp
    assert searxng_mcp.__version__ is not None
