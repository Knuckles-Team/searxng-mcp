import warnings

# Filter RequestsDependencyWarning early to prevent log spam
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        from requests.exceptions import RequestsDependencyWarning

        warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
    except ImportError:
        pass

# General urllib3/chardet mismatch warnings
warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")
warnings.filterwarnings("ignore", message=".*urllib3.*or charset_normalizer.*")
"""
SearXNG MCP Server.

Privacy-respecting metasearch engine to query search results across various platforms.
"""

import logging
import os
import random
import sys
from typing import Any

import requests
import yaml
from agent_utilities.base_utilities import to_boolean
from agent_utilities.mcp_utilities import (
    create_mcp_server,
)
from dotenv import find_dotenv, load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.utilities.logging import get_logger
from pydantic import Field

__version__ = "0.35.0"

logger = get_logger("SearXNGMCPServer")
logger.setLevel(logging.INFO)

SEARXNG_INSTANCE_URL = os.environ.get("SEARXNG_INSTANCE_URL") or os.environ.get(
    "SEARXNG_URL", None
)
SEARXNG_USERNAME = os.environ.get("SEARXNG_USERNAME", None)
SEARXNG_PASSWORD = os.environ.get("SEARXNG_PASSWORD", None)
HAS_BASIC_AUTH = bool(SEARXNG_USERNAME and SEARXNG_PASSWORD)
INSTANCES_LIST_URL = "https://raw.githubusercontent.com/searxng/searx-instances/refs/heads/master/searxinstances/instances.yml"
USE_RANDOM_INSTANCE = to_boolean(os.environ.get("USE_RANDOM_INSTANCE", "false"))


def get_random_searxng_instance() -> str:
    logger.info("[SearXNG] Fetching list of SearXNG instances...")
    try:
        response = requests.get(INSTANCES_LIST_URL, timeout=10)
        response.raise_for_status()
        instances_data = yaml.safe_load(response.text)

        standard_instances: list[str] = []

        for url, data in instances_data.items():
            instance_data = data or {}
            comments = instance_data.get("comments", [])
            network_type = instance_data.get("network_type")

            if (
                not comments or ("hidden" not in comments and "onion" not in comments)
            ) and (not network_type or network_type == "normal"):
                standard_instances.append(url)

        logger.info(f"[SearXNG] Found {len(standard_instances)} standard instances")

        if not standard_instances:
            raise ValueError("No standard SearXNG instances found")

        random_instance = random.SystemRandom().choice(standard_instances)  # noqa: S311
        logger.info(f"[SearXNG] Selected random instance: {random_instance}")
        return random_instance
    except Exception as e:
        logger.error(f"[SearXNG] Error fetching instances: {str(e)}")
        raise ValueError("Failed to fetch SearXNG instances list") from e


def register_prompts(mcp: FastMCP):
    @mcp.prompt
    def search(topic: str) -> str:
        return f"Searching the web for: {topic}."


def get_mcp_instance() -> tuple[Any, Any, Any, list[str]]:
    """Initialize and return the MCP instance, args, and middlewares."""
    load_dotenv(find_dotenv())

    args, mcp, middlewares = create_mcp_server(
        name="SearXNGMCP",
        version=__version__,
        instructions="SearXNG MCP Server — Privacy-respecting metasearch engine to find information across multiple search engines.",
    )

    @mcp.tool(name="web_search")
    async def web_search(
        query: str = Field(description="Search query to submit to SearXNG"),
        categories: list[str] | None = Field(
            default=None,
            description="Optional list of categories to search in (e.g. general, news, science, files, images, videos, music, it, social_media)",
        ),
        engines: list[str] | None = Field(
            default=None, description="Optional list of specific search engines to use"
        ),
        language: str = Field(
            default="en-US",
            description="Language code for search results (e.g. en-US)",
        ),
        pageno: int = Field(default=1, description="Page number of results to fetch"),
        ctx: Context | None = Field(
            default=None, description="MCP context for progress reporting"
        ),
    ) -> dict:
        """Perform a web search using a privacy-respecting SearXNG metasearch instance."""
        if ctx:
            await ctx.info(f"Performing SearXNG search for '{query}'...")

        instance_url = SEARXNG_INSTANCE_URL
        if not instance_url:
            if USE_RANDOM_INSTANCE:
                try:
                    instance_url = get_random_searxng_instance()
                except Exception as e:
                    logger.error(f"Failed to choose random instance: {e}")
                    instance_url = "https://searx.be"
            else:
                instance_url = "https://searx.be"

        instance_url = instance_url.rstrip("/")
        url = f"{instance_url}/search"

        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": pageno,
            "language": language,
        }
        if categories:
            params["categories"] = ",".join(categories)
        if engines:
            params["engines"] = ",".join(engines)

        auth: tuple[str, str] | None = None
        if SEARXNG_USERNAME is not None and SEARXNG_PASSWORD is not None:
            auth = (SEARXNG_USERNAME, SEARXNG_PASSWORD)

        try:
            response = requests.get(url, params=params, auth=auth, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"error": f"Failed to perform search: {str(e)}"}

    register_prompts(mcp)

    for mw in middlewares:
        mcp.add_middleware(mw)
    registered_tags: list[str] = []
    return mcp, args, middlewares, registered_tags


def mcp_server() -> None:
    mcp, args, middlewares, registered_tags = get_mcp_instance()
    print(f"{'searxng-mcp'} MCP v{__version__}", file=sys.stderr)
    print("\nStarting MCP Server", file=sys.stderr)
    print(f"  Transport: {args.transport.upper()}", file=sys.stderr)
    print(f"  Auth: {args.auth_type}", file=sys.stderr)
    print(f"  Dynamic Tags Loaded: {len(set(registered_tags))}", file=sys.stderr)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        logger.error("Invalid transport", extra={"transport": args.transport})
        sys.exit(1)


if __name__ == "__main__":
    mcp_server()
