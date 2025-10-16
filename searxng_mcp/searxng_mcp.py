#!/usr/bin/python
# coding: utf-8
import argparse
import os
import sys
import logging
import requests
import yaml
import random
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP, Context
from pydantic import Field

# Global variables for SearXNG configuration
SEARXNG_INSTANCE_URL = os.environ.get("SEARXNG_INSTANCE_URL", None)
SEARXNG_USERNAME = os.environ.get("SEARXNG_USERNAME", None)
SEARXNG_PASSWORD = os.environ.get("SEARXNG_PASSWORD", None)
HAS_BASIC_AUTH = bool(SEARXNG_USERNAME and SEARXNG_PASSWORD)
INSTANCES_LIST_URL = "https://raw.githubusercontent.com/searxng/searx-instances/refs/heads/master/searxinstances/instances.yml"
USE_RANDOM_INSTANCE = os.environ.get("USE_RANDOM_INSTANCE", "true").lower() not in {"false", "0", "no", "f", "n"}

# Setup logging for MCP server (logs to file)
def setup_logging(is_mcp_server: bool = False, log_file: str = None):
    logger = logging.getLogger("SearXNG")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if is_mcp_server and log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

setup_logging(is_mcp_server=True, log_file="searxng_mcp.log")

mcp = FastMCP(name="SearXNGServer")

# Function to fetch and select a random SearXNG instance
def get_random_searxng_instance() -> str:
    logger = logging.getLogger("SearXNG")
    logger.debug("[SearXNG] Fetching list of SearXNG instances...")
    try:
        response = requests.get(INSTANCES_LIST_URL)
        response.raise_for_status()
        instances_data = yaml.safe_load(response.text)

        # Filter for standard internet instances (not onion or hidden)
        standard_instances: List[str] = []

        for url, data in instances_data.items():
            instance_data = data or {}
            comments = instance_data.get("comments", [])
            network_type = instance_data.get("network_type")

            if (
                    (not comments or ("hidden" not in comments and "onion" not in comments)) and
                    (not network_type or network_type == "normal")
            ):
                standard_instances.append(url)

        logger.debug(f"[SearXNG] Found {len(standard_instances)} standard instances")

        if not standard_instances:
            raise ValueError("No standard SearXNG instances found")

        # Select a random instance
        random_instance = random.choice(standard_instances)
        logger.debug(f"[SearXNG] Selected random instance: {random_instance}")
        return random_instance
    except Exception as e:
        logger.error(f"[SearXNG] Error fetching instances: {str(e)}")
        raise ValueError("Failed to fetch SearXNG instances list") from e

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
async def searxngsearch(
        query: str = Field(description="Search query", default=None),
        language: str = Field(description="Language code for search results (e.g., 'en', 'de', 'fr'). Default: 'en'", default="en"),
        time_range: Optional[str] = Field(description="Time range for search results. Options: 'day', 'week', 'month', 'year'. Default: null (no time restriction).", default=None, enum=["day", "week", "month", "year"]),
        categories: Optional[List[str]] = Field(description="Categories to search in (e.g., 'general', 'images', 'news'). Default: null (all categories).", default=None),
        engines: Optional[List[str]] = Field(description="Specific search engines to use. Default: null (all available engines).", default=None),
        safesearch: int = Field(description="Safe search level: 0 (off), 1 (moderate), 2 (strict). Default: 1 (moderate).", default=1, enum=[0, 1, 2]),
        pageno: int = Field(description="Page number for results. Must be minimum 1. Default: 1.", default=1, ge=1),
        max_results: int = Field(description="Maximum number of search results to return. Range: 1-50. Default: 10.", default=10, ge=1, le=50),
        ctx: Context = Field(description="MCP context for progress reporting.", default=None),
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

        # Prepare search parameters
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

        # Report initial progress if ctx is available
        if ctx:
            await ctx.report_progress(progress=0, total=100)
            logger.debug("Reported initial progress: 0/100")

        # Make request to SearXNG
        auth = (SEARXNG_USERNAME, SEARXNG_PASSWORD) if HAS_BASIC_AUTH else None
        response = requests.get(f"{SEARXNG_INSTANCE_URL}/search", params=search_params, auth=auth)
        response.raise_for_status()
        search_response: Dict[str, Any] = response.json()

        # Limit results
        limited_results = search_response.get("results", [])[:max_results]

        # Construct final response
        final_response = {
            **search_response,
            "results": limited_results,
            "number_of_results": len(limited_results),
        }

        # Report completion
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

def searxng_mcp():
    global SEARXNG_INSTANCE_URL
    logger = logging.getLogger("SearXNG")

    # Determine SearXNG instance
    searxng_url = os.environ.get("SEARXNG_URL")
    if searxng_url:
        SEARXNG_INSTANCE_URL = searxng_url
        logger.debug(f"[SearXNG] Using specified instance: {SEARXNG_INSTANCE_URL}")
    elif USE_RANDOM_INSTANCE:
        logger.debug("[SearXNG] No URL specified, using a random instance")
        try:
            SEARXNG_INSTANCE_URL = get_random_searxng_instance()
            logger.debug(f"[SearXNG] Using random instance: {SEARXNG_INSTANCE_URL}")
        except Exception as e:
            logger.error(f"[SearXNG] Error getting random instance: {str(e)}")
            sys.exit(1)
    else:
        logger.error("[SearXNG] SEARXNG_URL environment variable is required when USE_RANDOM_INSTANCE is false")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Run SearXNG MCP server.")
    parser.add_argument(
        "-t",
        "--transport",
        default="stdio",
        choices=["stdio", "http", "sse"],
        help="Transport method: 'stdio', 'http', or 'sse' [legacy] (default: stdio)",
    )
    parser.add_argument(
        "-s",
        "--host",
        default="0.0.0.0",
        help="Host address for HTTP transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Port number for HTTP transport (default: 8000)",
    )

    args = parser.parse_args()

    if args.port < 0 or args.port > 65535:
        logger.error(f"Error: Port {args.port} is out of valid range (0-65535).")
        sys.exit(1)

    logger.info(f"SearXNG MCP server starting with transport: {args.transport}")
    logger.info(f"Connected to SearXNG instance at: {SEARXNG_INSTANCE_URL}")
    logger.info(f"Basic auth: {'Enabled' if HAS_BASIC_AUTH else 'Disabled'}")
    logger.info(f"Random instance selection: {'Enabled' if USE_RANDOM_INSTANCE else 'Disabled'}")

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        logger.error("Transport not supported")
        sys.exit(1)

if __name__ == "__main__":
    searxng_mcp()