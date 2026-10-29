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

import json
import logging
import random
import sys
from importlib.metadata import version
from typing import Any

import requests
import yaml
from agent_connector_sdk.config import setting
from fastmcp import Context, FastMCP
from fastmcp.utilities.logging import get_logger
from pydantic import Field

__version__ = version("searxng-mcp")

logger = get_logger("SearXNGMCPServer")
logger.setLevel(logging.INFO)

INSTANCES_LIST_URL = "https://raw.githubusercontent.com/searxng/searx-instances/refs/heads/master/searxinstances/instances.yml"


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
        logger.info("[SearXNG] Selected a configured search instance")
        return random_instance
    except Exception as e:
        logger.error("Operation failed: error_type=%s", type(e).__name__)
        raise ValueError("Failed to fetch SearXNG instances list") from e


def _resolve_embedded_instance() -> str:
    """Zero-config self-contained search (CONCEPT:SR-KG.compute.embedded-instance):
    when no ``SEARXNG_URL``/``SEARXNG_INSTANCE_URL`` is configured, prefer a
    PRIVATE embedded SearXNG instance this server owns over the public
    ``searx.be``/random-instance fallback below. No-op (returns ``""``)
    unless the ``searxng-mcp[embedded]`` extra is installed AND
    ``SEARXNG_EMBEDDED`` isn't explicitly disabled — see
    ``searxng_mcp.embedded.embedded_enabled``. Best-effort: a startup failure
    degrades to the existing public fallback rather than breaking search.
    """
    try:
        from searxng_mcp.embedded import embedded_enabled, get_embedded_instance

        if not embedded_enabled():
            return ""
        return get_embedded_instance().ensure_running()
    except Exception as e:  # noqa: BLE001 - degrade to the public fallback
        logger.warning("Operation failed: error_type=%s", type(e).__name__)
        return ""


def register_prompts(mcp: FastMCP):
    @mcp.prompt
    def search(topic: str) -> str:
        return f"Searching the web for: {topic}."


def register_tools(mcp: FastMCP) -> None:
    """Register the SearXNG tools, prompts and app tools on ``mcp`` (the Connector's verbose_register)."""

    async def _perform_search(
        query: str,
        categories: list[str] | None,
        engines: list[str] | None,
        language: str,
        pageno: int,
    ) -> dict:
        """Run one SearXNG query (plain helper shared by the tools); it writes nothing."""
        instance_url = setting("SEARXNG_INSTANCE_URL", "") or setting("SEARXNG_URL", "")
        if not instance_url:
            instance_url = _resolve_embedded_instance()
        if not instance_url:
            if bool(setting("USE_RANDOM_INSTANCE", False)):
                try:
                    instance_url = get_random_searxng_instance()
                except Exception as e:
                    logger.error("Operation failed: error_type=%s", type(e).__name__)
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
        username = setting("SEARXNG_USERNAME", "")
        password = setting("SEARXNG_PASSWORD", "")
        if username and password:
            auth = (username, password)

        try:
            response = requests.get(url, params=params, auth=auth, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error("Search failed: error_type=%s", type(e).__name__)
            return {"error": "Failed to perform search"}

        # Search results are a short-lived virtual source: web_search never
        # writes them to the graph. searxng_ingest_search is the explicit,
        # opt-in ingest path.
        return data

    @mcp.tool(
        name="web_search",
        tags={"operation"},
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
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
            await ctx.info("Performing configured SearXNG search...")
        return await _perform_search(query, categories, engines, language, pageno)

    @mcp.tool(name="searxng_ingest_search", tags={"misc", "kg"})
    async def searxng_ingest_search(
        query: str = Field(description="Search query to submit to SearXNG"),
        categories: list[str] | None = Field(
            default=None,
            description="Optional list of categories to search in (e.g. general, news, science)",
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
        """Run a SearXNG search and natively ingest its results into epistemic-graph.

        Wire-First: performs the search, then pushes each result into the knowledge graph
        as a search :Document (+ :SearchQuery / :SearchEngine typed nodes and their
        :resultOf / :fromEngine links). Best-effort: ``ingested`` is ``None`` when no engine
        is reachable. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
        """
        from searxng_mcp.kg_ingest import ingest_search_results

        if ctx:
            await ctx.info("Searching and ingesting configured SearXNG results...")
        data = await _perform_search(query, categories, engines, language, pageno)
        if isinstance(data, dict) and data.get("error"):
            return {"listed": 0, "ingested": None, "error": data["error"]}
        results = data.get("results") or [] if isinstance(data, dict) else []
        ingested = await ingest_search_results(query, data, language=language)
        return {"listed": len(results), "ingested": ingested}

    def _embedded_unavailable(action: str) -> dict | None:
        from searxng_mcp.embedded import embedded_available

        if not embedded_available():
            return {
                "action": action,
                "error": "searx package not installed (pip install searxng-mcp[embedded])",
            }
        return None

    @mcp.tool(
        name="searxng_get_settings",
        tags={"misc", "config", "operation"},
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def searxng_get_settings() -> dict:
        """Read the EMBEDDED SearXNG instance's active settings.yml
        (CONCEPT:SR-KG.compute.embedded-instance): the user override at
        ``$XDG_CONFIG_HOME/searxng-mcp/settings.yml`` if one exists, else the
        packaged default, plus its path. Informational only when an external
        ``SEARXNG_URL`` is configured.
        """
        from searxng_mcp.embedded import read_settings, user_settings_path

        if (unavailable := _embedded_unavailable("get")) is not None:
            return unavailable
        return {
            "action": "get",
            "settings_path": str(
                user_settings_path()
                if user_settings_path().is_file()
                else "packaged default"
            ),
            "settings": read_settings(),
        }

    @mcp.tool(
        name="searxng_set_settings",
        tags={"misc", "config", "operation"},
        annotations={"readOnlyHint": False, "destructiveHint": False},
    )
    async def searxng_set_settings(
        overrides_json: str = Field(
            default="",
            description="JSON object of settings.yml overrides "
            '(e.g. \'{"search": {"formats": ["html", "json", "csv"]}}\'). '
            "Deep-merged onto the currently-active settings unless merge=false.",
        ),
        merge: bool = Field(
            default=True,
            description="Deep-merge onto current settings (default) or replace "
            "the override file wholesale.",
        ),
        apply_now: bool = Field(
            default=True,
            description="Stop the running embedded instance (if any) so the NEXT "
            "search respawns it with the new settings.",
        ),
    ) -> dict:
        """Deep-merge ``overrides_json`` into the EMBEDDED SearXNG user override
        settings.yml (created on first use; the packaged default is never
        modified), then stop the running embedded instance so the next search
        respawns with the new settings (unless ``apply_now=false``).
        """
        from searxng_mcp.embedded import (
            get_embedded_instance,
            read_settings,
            write_user_settings,
        )

        if (unavailable := _embedded_unavailable("set")) is not None:
            return unavailable
        try:
            overrides = json.loads(overrides_json) if overrides_json else {}
        except (TypeError, ValueError) as e:
            return {
                "action": "set",
                "error": f"invalid overrides_json: {type(e).__name__}",
            }
        if not isinstance(overrides, dict):
            return {
                "action": "set",
                "error": "overrides_json must decode to an object",
            }
        path = write_user_settings(overrides, merge=merge)
        if apply_now:
            get_embedded_instance().stop()
        return {
            "action": "set",
            "settings_path": str(path),
            "settings": read_settings(),
            "restart_pending": not apply_now,
        }

    @mcp.tool(
        name="searxng_reset_settings",
        tags={"misc", "config", "operation"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
        },
    )
    async def searxng_reset_settings(
        apply_now: bool = Field(
            default=True,
            description="Stop the running embedded instance (if any) so the NEXT "
            "search respawns it with the packaged default settings.",
        ),
    ) -> dict:
        """Delete the EMBEDDED SearXNG user override settings.yml, reverting to
        the packaged default on the next spawn."""
        from searxng_mcp.embedded import (
            get_embedded_instance,
            read_settings,
            reset_user_settings,
        )

        if (unavailable := _embedded_unavailable("reset")) is not None:
            return unavailable
        removed = reset_user_settings()
        if apply_now:
            get_embedded_instance().stop()
        return {"action": "reset", "removed": removed, "settings": read_settings()}

    register_prompts(mcp)

    from searxng_mcp.apps import register_search_app_tools

    register_search_app_tools(mcp)


def get_mcp_instance() -> tuple[Any, Any, Any, list[str]]:
    """Build the connector's server from its Connector declaration."""
    from agent_connector_sdk.connector import build_server

    args, mcp = build_server("searxng_mcp")
    return mcp, args, [], []


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
