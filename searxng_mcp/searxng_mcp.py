#!/usr/bin/python
# coding: utf-8
import argparse
import os
import sys
import logging
import requests
import yaml
import random
from typing import Optional, Dict, List, Union, Any
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.auth import OAuthProxy, RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware


def to_boolean(string: Union[str, bool] = None) -> bool:
    if isinstance(string, bool):
        return string
    if not string:
        return False
    normalized = str(string).strip().lower()
    true_values = {"t", "true", "y", "yes", "1"}
    false_values = {"f", "false", "n", "no", "0"}
    if normalized in true_values:
        return True
    elif normalized in false_values:
        return False
    else:
        raise ValueError(f"Cannot convert '{string}' to boolean")


# Global variables for SearXNG configuration
SEARXNG_INSTANCE_URL = os.environ.get("SEARXNG_INSTANCE_URL", None)
SEARXNG_USERNAME = os.environ.get("SEARXNG_USERNAME", None)
SEARXNG_PASSWORD = os.environ.get("SEARXNG_PASSWORD", None)
HAS_BASIC_AUTH = bool(SEARXNG_USERNAME and SEARXNG_PASSWORD)
INSTANCES_LIST_URL = "https://raw.githubusercontent.com/searxng/searx-instances/refs/heads/master/searxinstances/instances.yml"
USE_RANDOM_INSTANCE = to_boolean(os.environ.get("USE_RANDOM_INSTANCE", "true").lower())


# Setup logging for MCP server (logs to file)
def setup_logging(is_mcp_server: bool = False, log_file: str = None):
    logger = logging.getLogger("SearXNG")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

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
                not comments or ("hidden" not in comments and "onion" not in comments)
            ) and (not network_type or network_type == "normal"):
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
        response = requests.get(
            f"{SEARXNG_INSTANCE_URL}/search", params=search_params, auth=auth
        )
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
    parser.add_argument(
        "--auth-type",
        default="none",
        choices=["none", "static", "jwt", "oauth-proxy", "oidc-proxy", "remote-oauth"],
        help="Authentication type for MCP server: 'none' (disabled), 'static' (internal), 'jwt' (external token verification), 'oauth-proxy', 'oidc-proxy', 'remote-oauth' (external) (default: none)",
    )
    # JWT/Token params
    parser.add_argument(
        "--token-jwks-uri", default=None, help="JWKS URI for JWT verification"
    )
    parser.add_argument(
        "--token-issuer", default=None, help="Issuer for JWT verification"
    )
    parser.add_argument(
        "--token-audience", default=None, help="Audience for JWT verification"
    )
    # OAuth Proxy params
    parser.add_argument(
        "--oauth-upstream-auth-endpoint",
        default=None,
        help="Upstream authorization endpoint for OAuth Proxy",
    )
    parser.add_argument(
        "--oauth-upstream-token-endpoint",
        default=None,
        help="Upstream token endpoint for OAuth Proxy",
    )
    parser.add_argument(
        "--oauth-upstream-client-id",
        default=None,
        help="Upstream client ID for OAuth Proxy",
    )
    parser.add_argument(
        "--oauth-upstream-client-secret",
        default=None,
        help="Upstream client secret for OAuth Proxy",
    )
    parser.add_argument(
        "--oauth-base-url", default=None, help="Base URL for OAuth Proxy"
    )
    # OIDC Proxy params
    parser.add_argument(
        "--oidc-config-url", default=None, help="OIDC configuration URL"
    )
    parser.add_argument("--oidc-client-id", default=None, help="OIDC client ID")
    parser.add_argument("--oidc-client-secret", default=None, help="OIDC client secret")
    parser.add_argument("--oidc-base-url", default=None, help="Base URL for OIDC Proxy")
    # Remote OAuth params
    parser.add_argument(
        "--remote-auth-servers",
        default=None,
        help="Comma-separated list of authorization servers for Remote OAuth",
    )
    parser.add_argument(
        "--remote-base-url", default=None, help="Base URL for Remote OAuth"
    )
    # Common
    parser.add_argument(
        "--allowed-client-redirect-uris",
        default=None,
        help="Comma-separated list of allowed client redirect URIs",
    )
    # Eunomia params
    parser.add_argument(
        "--eunomia-type",
        default="none",
        choices=["none", "embedded", "remote"],
        help="Eunomia authorization type: 'none' (disabled), 'embedded' (built-in), 'remote' (external) (default: none)",
    )
    parser.add_argument(
        "--eunomia-policy-file",
        default="mcp_policies.json",
        help="Policy file for embedded Eunomia (default: mcp_policies.json)",
    )
    parser.add_argument(
        "--eunomia-remote-url", default=None, help="URL for remote Eunomia server"
    )

    args = parser.parse_args()

    if args.port < 0 or args.port > 65535:
        print(f"Error: Port {args.port} is out of valid range (0-65535).")
        sys.exit(1)

    # Set auth based on type
    auth = None
    allowed_uris = (
        args.allowed_client_redirect_uris.split(",")
        if args.allowed_client_redirect_uris
        else None
    )

    if args.auth_type == "none":
        auth = None
    elif args.auth_type == "static":
        # Internal static tokens (hardcoded example)
        auth = StaticTokenVerifier(
            tokens={
                "test-token": {"client_id": "test-user", "scopes": ["read", "write"]},
                "admin-token": {"client_id": "admin", "scopes": ["admin"]},
            }
        )
    elif args.auth_type == "jwt":
        if not (args.token_jwks_uri and args.token_issuer and args.token_audience):
            print(
                "Error: jwt requires --token-jwks-uri, --token-issuer, --token-audience"
            )
            sys.exit(1)
        auth = JWTVerifier(
            jwks_uri=args.token_jwks_uri,
            issuer=args.token_issuer,
            audience=args.token_audience,
        )
    elif args.auth_type == "oauth-proxy":
        if not (
            args.oauth_upstream_auth_endpoint
            and args.oauth_upstream_token_endpoint
            and args.oauth_upstream_client_id
            and args.oauth_upstream_client_secret
            and args.oauth_base_url
            and args.token_jwks_uri
            and args.token_issuer
            and args.token_audience
        ):
            print(
                "Error: oauth-proxy requires --oauth-upstream-auth-endpoint, --oauth-upstream-token-endpoint, --oauth-upstream-client-id, --oauth-upstream-client-secret, --oauth-base-url, --token-jwks-uri, --token-issuer, --token-audience"
            )
            sys.exit(1)
        token_verifier = JWTVerifier(
            jwks_uri=args.token_jwks_uri,
            issuer=args.token_issuer,
            audience=args.token_audience,
        )
        auth = OAuthProxy(
            upstream_authorization_endpoint=args.oauth_upstream_auth_endpoint,
            upstream_token_endpoint=args.oauth_upstream_token_endpoint,
            upstream_client_id=args.oauth_upstream_client_id,
            upstream_client_secret=args.oauth_upstream_client_secret,
            token_verifier=token_verifier,
            base_url=args.oauth_base_url,
            allowed_client_redirect_uris=allowed_uris,
        )
    elif args.auth_type == "oidc-proxy":
        if not (
            args.oidc_config_url
            and args.oidc_client_id
            and args.oidc_client_secret
            and args.oidc_base_url
        ):
            print(
                "Error: oidc-proxy requires --oidc-config-url, --oidc-client-id, --oidc-client-secret, --oidc-base-url"
            )
            sys.exit(1)
        auth = OIDCProxy(
            config_url=args.oidc_config_url,
            client_id=args.oidc_client_id,
            client_secret=args.oidc_client_secret,
            base_url=args.oidc_base_url,
            allowed_client_redirect_uris=allowed_uris,
        )
    elif args.auth_type == "remote-oauth":
        if not (
            args.remote_auth_servers
            and args.remote_base_url
            and args.token_jwks_uri
            and args.token_issuer
            and args.token_audience
        ):
            print(
                "Error: remote-oauth requires --remote-auth-servers, --remote-base-url, --token-jwks-uri, --token-issuer, --token-audience"
            )
            sys.exit(1)
        auth_servers = [url.strip() for url in args.remote_auth_servers.split(",")]
        token_verifier = JWTVerifier(
            jwks_uri=args.token_jwks_uri,
            issuer=args.token_issuer,
            audience=args.token_audience,
        )
        auth = RemoteAuthProvider(
            token_verifier=token_verifier,
            authorization_servers=auth_servers,
            base_url=args.remote_base_url,
        )
    mcp.auth = auth
    if args.eunomia_type != "none":
        from eunomia_mcp import create_eunomia_middleware

        if args.eunomia_type == "embedded":
            if not args.eunomia_policy_file:
                print("Error: embedded Eunomia requires --eunomia-policy-file")
                sys.exit(1)
            middleware = create_eunomia_middleware(policy_file=args.eunomia_policy_file)
            mcp.add_middleware(middleware)
        elif args.eunomia_type == "remote":
            if not args.eunomia_remote_url:
                print("Error: remote Eunomia requires --eunomia-remote-url")
                sys.exit(1)
            middleware = create_eunomia_middleware(
                use_remote_eunomia=args.eunomia_remote_url
            )
            mcp.add_middleware(middleware)

    mcp.add_middleware(
        ErrorHandlingMiddleware(include_traceback=True, transform_errors=True)
    )
    mcp.add_middleware(
        RateLimitingMiddleware(max_requests_per_second=10.0, burst_capacity=20)
    )
    mcp.add_middleware(TimingMiddleware())
    mcp.add_middleware(LoggingMiddleware())

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        logger = logging.getLogger("SearXNG")
        logger.error("Transport not supported")
        sys.exit(1)


if __name__ == "__main__":
    searxng_mcp()
