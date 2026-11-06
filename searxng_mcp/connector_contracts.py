"""Surface contracts: tool use, links, data locations and business roles."""

from scion_sdk.surface_contracts import (
    BusinessRole,
    DataLocation,
    Refusal,
    SurfaceLink,
    ToolStep,
    ToolUseContract,
)

_DENIED = Refusal("ACCESS_DENIED", "the instance rejects the request or is unreachable")
_NO_EMBED = Refusal(
    "EMBEDDED_UNAVAILABLE", "the embedded searx package is not installed"
)

CONTRACTS = (
    ToolUseContract(
        "research-a-question",
        (
            ToolStep(
                "web_search",
                params=("query", "categories", "engines", "language", "pageno"),
                result=("results", "query", "number_of_results"),
                refusals=(_DENIED,),
            ),
        ),
    ),
    ToolUseContract(
        "capture-search-to-graph",
        (
            ToolStep(
                "web_search",
                params=("query", "categories", "language"),
                result=("results",),
                refusals=(_DENIED,),
            ),
            ToolStep(
                "searxng_ingest_search",
                params=("query", "categories", "engines", "language", "pageno"),
                result=("listed", "ingested"),
                refusals=(
                    Refusal(
                        "NO_ENGINE",
                        "no knowledge-graph engine is reachable, ingested is null",
                    ),
                ),
            ),
        ),
    ),
    ToolUseContract(
        "browse-results-in-app",
        (
            ToolStep(
                "searxng_search_app",
                params=("query",),
                result=("results",),
                refusals=(_DENIED,),
            ),
        ),
    ),
    ToolUseContract(
        "tune-embedded-engines",
        (
            ToolStep(
                "searxng_get_settings",
                result=("settings_path", "settings"),
                refusals=(_NO_EMBED,),
            ),
            ToolStep(
                "searxng_set_settings",
                params=("overrides_json", "merge", "apply_now"),
                result=("settings_path", "applied"),
                refusals=(
                    _NO_EMBED,
                    Refusal(
                        "INVALID_ARGUMENT",
                        "overrides_json is not valid settings YAML or JSON",
                    ),
                ),
            ),
            ToolStep(
                "web_search",
                params=("query",),
                result=("results",),
                refusals=(_DENIED,),
            ),
        ),
    ),
    ToolUseContract(
        "reset-embedded-settings",
        (
            ToolStep(
                "searxng_get_settings",
                result=("settings_path", "settings"),
                refusals=(_NO_EMBED,),
            ),
            ToolStep(
                "searxng_reset_settings",
                params=("apply_now",),
                result=("settings_path", "removed"),
                refusals=(
                    _NO_EMBED,
                    Refusal(
                        "CONFIRMATION_REQUIRED",
                        "the operator has not approved discarding the override",
                    ),
                ),
            ),
        ),
    ),
)

LINKS = (
    SurfaceLink(
        "research-a-question",
        tools=("web_search",),
        prompts=("searxng-mcp-operator", "searxng-research-analyst"),
        skills=("searxng-web-search", "searxng-news-research"),
    ),
    SurfaceLink(
        "capture-search-to-graph",
        tools=("web_search", "searxng_ingest_search"),
        prompts=("searxng-mcp-operator", "searxng-research-analyst"),
        skills=("searxng-kg-ingestion",),
    ),
    SurfaceLink(
        "browse-results-in-app",
        tools=("searxng_search_app",),
        prompts=("searxng-mcp-operator", "searxng-research-analyst"),
        skills=("searxng-web-search",),
    ),
    SurfaceLink(
        "tune-embedded-engines",
        tools=("searxng_get_settings", "searxng_set_settings", "web_search"),
        prompts=("searxng-mcp-operator", "searxng-search-administrator"),
        skills=("searxng-settings-editor",),
    ),
    SurfaceLink(
        "reset-embedded-settings",
        tools=("searxng_get_settings", "searxng_reset_settings"),
        prompts=("searxng-mcp-operator", "searxng-search-administrator"),
        skills=("searxng-settings-editor",),
    ),
    SurfaceLink(
        "searxng-mcp-operations",
        tools=(
            "web_search",
            "searxng_ingest_search",
            "searxng_search_app",
            "searxng_get_settings",
            "searxng_set_settings",
            "searxng_reset_settings",
        ),
        skills=("searxng-mcp-operations",),
    ),
)

LOCATIONS = (
    DataLocation(
        "searxng-web-search",
        ("SearchResult", "SearchQuery", "SearchEngine"),
        "SEARXNG_INSTANCE_URL",
        "web_search",
    ),
    DataLocation(
        "searxng-embedded-settings",
        ("SearxngInstance",),
        "XDG_CONFIG_HOME/searxng-mcp/settings.yml",
        "searxng_get_settings",
    ),
)

ROLES = (
    BusinessRole(
        "research-analyst",
        tasks=(
            "research-a-question",
            "capture-search-to-graph",
            "browse-results-in-app",
        ),
    ),
    BusinessRole(
        "search-administrator",
        tasks=("tune-embedded-engines", "reset-embedded-settings"),
    ),
)
