#!/usr/bin/python
# coding: utf-8
from dotenv import load_dotenv, find_dotenv
import os
import sys
import requests
import yaml
import random
import logging
from typing import Optional, Dict, List, Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.utilities.logging import get_logger
from agent_utilities.base_utilities import to_boolean
from agent_utilities.mcp_utilities import (
    create_mcp_server,
    config,
)

__version__ = "0.1.33"

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = get_logger("SearXNGMCPServer")


SEARXNG_INSTANCE_URL = os.environ.get("SEARXNG_INSTANCE_URL", None)
SEARXNG_USERNAME = os.environ.get("SEARXNG_USERNAME", None)
SEARXNG_PASSWORD = os.environ.get("SEARXNG_PASSWORD", None)
HAS_BASIC_AUTH = bool(SEARXNG_USERNAME and SEARXNG_PASSWORD)
INSTANCES_LIST_URL = "https://raw.githubusercontent.com/searxng/searx-instances/refs/heads/master/searxinstances/instances.yml"
USE_RANDOM_INSTANCE = to_boolean(os.environ.get("USE_RANDOM_INSTANCE", "false").lower())


def get_random_searxng_instance() -> str:
    logger = logging.getLogger("SearXNG")
    logger.debug("[SearXNG] Fetching list of SearXNG instances...")
    try:
        response = requests.get(INSTANCES_LIST_URL)
        response.raise_for_status()
        instances_data = yaml.safe_load(response.text)

        standard_instances: List[str] = []

        for url, data in instances_data.items():
            instance_data = data or {}
            comments = instance_data.get("comments", [])
            network_type = instance_data.get("network_type")

            if (
                not comments or ("hidden" not in comments and "onion" not in comments)
            ) and (not network_type or network_type == "normal"):
                standard_instances.append(url)

        logger.debug(f"[SearXNG] Found {len(standard_instances)} standard instances")

        if not standard_instances:
            raise ValueError("No standard SearXNG instances found")

        random_instance = random.choice(standard_instances)
        logger.debug(f"[SearXNG] Selected random instance: {random_instance}")
        return random_instance
    except Exception as e:
        logger.error(f"[SearXNG] Error fetching instances: {str(e)}")
        raise ValueError("Failed to fetch SearXNG instances list") from e


def register_misc_tools(mcp: FastMCP):
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "OK"})


def register_search_tools(mcp: FastMCP):
    @mcp.tool(
        annotations={
            "title": "SearXNG Search",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        tags={"search"},
    )
    async def web_search(
        query: str = Field(description="Search query", default=None),
        language: str = Field(
            description="Language code for search results (e.g., 'en', 'de', 'fr'). Default: 'en'",
            default="en",
        ),
        time_range: Optional[str] = Field(
            description="Time range for search results. Options: 'day', 'week', 'month', 'year'. Default: null (no time restriction).",
            default=None,
        ),
        categories: Optional[List[str]] = Field(
            description="Categories to search in (e.g., 'general', 'images', 'news'). Default: null (all categories).",
            default=None,
        ),
        engines: Optional[List[str]] = Field(
            description="Specific search engines to use. Default: null (all available engines).",
            default=None,
        ),
        safesearch: int = Field(
            description="Safe search level: 0 (off), 1 (moderate), 2 (strict). Default: 1 (moderate).",
            default=1,
        ),
        pageno: int = Field(
            description="Page number for results. Must be minimum 1. Default: 1.",
            default=1,
            ge=1,
        ),
        max_results: int = Field(
            description="Maximum number of search results to return. Range: 1-50. Default: 10.",
            default=10,
            ge=1,
            le=50,
        ),
        ctx: Context = Field(
            description="MCP context for progress reporting.", default=None
        ),
    ) -> Dict[str, Any]:
        """
        Perform web searches using SearXNG, a privacy-respecting metasearch engine. Returns relevant web content with customizable parameters.
        Returns a Dictionary response with status, message, data (search results), and error if any.
        """
        logger = logging.getLogger("SearXNG")
        logger.debug(f"[SearXNG] Searching for: {query}")

        try:
            if not query:
                return {
                    "status": 400,
                    "message": "Invalid input: query must not be empty",
                    "data": None,
                    "error": "query must not be empty",
                }

            search_params = {
                "q": query,
                "format": "json",
                "language": language,
                "safesearch": safesearch,
                "pageno": pageno,
            }
            if time_range:
                search_params["time_range"] = time_range
            if categories:
                search_params["categories"] = ",".join(categories)
            if engines:
                search_params["engines"] = ",".join(engines)

            if ctx:
                await ctx.report_progress(progress=0, total=100)
                logger.debug("Reported initial progress: 0/100")

            auth = (SEARXNG_USERNAME, SEARXNG_PASSWORD) if HAS_BASIC_AUTH else None
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(
                f"{SEARXNG_INSTANCE_URL}/search",
                params=search_params,
                auth=auth,
                headers=headers,
            )
            response.raise_for_status()
            search_response: Dict[str, Any] = response.json()

            limited_results = search_response.get("results", [])[:max_results]

            final_response = {
                **search_response,
                "results": limited_results,
                "number_of_results": len(limited_results),
            }

            if ctx:
                await ctx.report_progress(progress=100, total=100)
                logger.debug("Reported final progress: 100/100")

            logger.debug(f"[SearXNG] Search completed for query: {query}")
            return {
                "status": 200,
                "message": "Search completed successfully",
                "data": final_response,
                "error": None,
            }
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            if status_code == 401:
                error_msg = "Authentication failed. Please check your SearXNG username and password."
            else:
                error_msg = f"SearXNG API error: {e.response.json().get('message', str(e)) if e.response else str(e)}"
            logger.error(f"[SearXNG Error] {error_msg}")
            return {
                "status": status_code or 500,
                "message": "Failed to perform search",
                "data": None,
                "error": error_msg,
            }
        except Exception as e:
            logger.error(f"[SearXNG Error] {str(e)}")
            return {
                "status": 500,
                "message": "Failed to perform search",
                "data": None,
                "error": str(e),
            }


def register_prompts(mcp: FastMCP):
    @mcp.prompt
    def search(topic) -> str:
        return f"Searching the web for: {topic}."


def mcp_server():
    load_dotenv(find_dotenv())

    args, mcp, middlewares = create_mcp_server(
        name="SearXNGMCP",
        version=__version__,
        instructions="SearXNG MCP Server — Privacy-respecting metasearch engine to find information across multiple search engines.",
    )

    DEFAULT_MISCTOOL = to_boolean(os.getenv("MISCTOOL", "True"))
    if DEFAULT_MISCTOOL:
        register_misc_tools(mcp)
    DEFAULT_SEARCHTOOL = to_boolean(os.getenv("SEARCHTOOL", "True"))
    if DEFAULT_SEARCHTOOL:
        register_search_tools(mcp)

    for mw in middlewares:
        mcp.add_middleware(mw)

    print(f"SearXNG MCP v{__version__}")
    print("\nStarting SearXNG MCP Server")
    print(f"  Transport: {args.transport.upper()}")
    print(f"  Auth: {args.auth_type}")
    print(f"  Delegation: {'ON' if config['enable_delegation'] else 'OFF'}")
    print(f"  Eunomia: {args.eunomia_type}")

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        logger.error("Invalid transport", extra={"transport": args.transport})
        sys.exit(1)
    DEFAULT_MISCTOOL = to_boolean(os.getenv("MISCTOOL", "True"))
    if DEFAULT_MISCTOOL:
        register_misc_tools(mcp)
    DEFAULT_SEARCHTOOL = to_boolean(os.getenv("SEARCHTOOL", "True"))
    if DEFAULT_SEARCHTOOL:
        register_search_tools(mcp)

    for mw in middlewares:
        mcp.add_middleware(mw)

    print(f"SearXNG MCP v{__version__}")
    print("\nStarting SearXNG MCP Server")
    print(f"  Transport: {args.transport.upper()}")
    print(f"  Auth: {args.auth_type}")
    print(f"  Delegation: {'ON' if config['enable_delegation'] else 'OFF'}")
    print(f"  Eunomia: {args.eunomia_type}")

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
