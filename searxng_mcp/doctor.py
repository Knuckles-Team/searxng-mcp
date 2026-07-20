#!/usr/bin/env python
"""``searxng-doctor`` — resolve + verify the effective SearXNG configuration
(CONCEPT:SR-KG.compute.embedded-instance).

Prints which instance URL this MCP server would ACTUALLY use right now, given
the current env (explicit config -> embedded -> random public instance ->
``https://searx.be`` — the exact order ``mcp_server._perform_search`` runs),
resolves + validates the embedded-mode ``settings.yml``, and (with
``--verify``) spawns a throwaway embedded instance end to end to confirm it
comes up healthy, then stops it. Mirrors the fleet's ``*-doctor`` preflight
convention (e.g. ``agent-utilities-doctor``) — a diagnostic CLI, never a
second config-resolution implementation (the resolution logic itself lives
once in ``searxng_mcp.mcp_server``/``searxng_mcp.embedded``, this module only
surfaces it).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import yaml
from agent_utilities.core.config import setting

from searxng_mcp.embedded import (
    EmbeddedSearXNG,
    _settings_path,
    embedded_available,
    embedded_enabled,
)

_RESOLUTION_ORDER = [
    "SEARXNG_INSTANCE_URL / SEARXNG_URL (explicit config)",
    "embedded (SEARXNG_EMBEDDED, requires searxng-mcp[embedded])",
    "USE_RANDOM_INSTANCE (public instance pool)",
    "https://searx.be (last-resort public fallback)",
]

_STEP_BY_SOURCE = {
    "explicit": 1,
    "embedded": 2,
    "random-public-instance": 3,
    "public-fallback": 4,
}


def resolve_config() -> dict[str, Any]:
    """The SAME resolution order ``_perform_search`` runs, surfaced for
    inspection — one source of truth, not a second implementation."""
    instance_url = setting("SEARXNG_INSTANCE_URL", "") or setting("SEARXNG_URL", "")
    embedded_avail = embedded_available()
    embedded_on = embedded_enabled()
    use_random = bool(setting("USE_RANDOM_INSTANCE", False))

    report: dict[str, Any] = {
        "configured_instance_url": instance_url or None,
        "embedded_extra_installed": embedded_avail,
        "embedded_enabled_setting": bool(setting("SEARXNG_EMBEDDED", True)),
        "embedded_would_activate": bool(embedded_on and not instance_url),
        "use_random_instance": use_random,
        "resolution_order": _RESOLUTION_ORDER,
    }

    if instance_url:
        report["effective_source"] = "explicit"
        report["effective_url"] = instance_url
    elif embedded_on:
        report["effective_source"] = "embedded"
    elif use_random:
        report["effective_source"] = "random-public-instance"
    else:
        report["effective_source"] = "public-fallback"
        report["effective_url"] = "https://searx.be"

    settings_file = _settings_path()
    report["embedded_settings_path"] = settings_file
    try:
        with open(settings_file, encoding="utf-8") as f:
            report["embedded_settings_overrides"] = yaml.safe_load(f)
        report["embedded_settings_valid_yaml"] = True
    except (OSError, yaml.YAMLError) as e:
        report["embedded_settings_valid_yaml"] = False
        report["embedded_settings_error"] = type(e).__name__

    return report


def verify_embedded() -> dict[str, Any]:
    """Actually spawn a throwaway embedded instance and confirm it comes up
    healthy, then stop it — the real end-to-end check, not just config
    inspection. Requires the ``[embedded]`` extra."""
    if not embedded_available():
        return {
            "ok": False,
            "error": "searx package not installed (pip install searxng-mcp[embedded])",
        }
    instance = EmbeddedSearXNG()
    try:
        url = instance.ensure_running()
        return {"ok": True, "url": url}
    except Exception as e:  # noqa: BLE001 - report, don't crash the doctor
        return {"ok": False, "error": "Operation failed"}
    finally:
        instance.stop()


def _print_human(report: dict[str, Any]) -> None:
    print("searxng-doctor -- effective SearXNG configuration\n")
    print(
        f"  configured instance URL    : {report['configured_instance_url'] or '(none)'}"
    )
    print(f"  [embedded] extra installed : {report['embedded_extra_installed']}")
    print(f"  SEARXNG_EMBEDDED setting   : {report['embedded_enabled_setting']}")
    print(f"  embedded would activate    : {report['embedded_would_activate']}")
    print(f"  USE_RANDOM_INSTANCE        : {report['use_random_instance']}")
    print(f"  >> effective source        : {report['effective_source']}")
    if report.get("effective_url"):
        print("  >> effective URL configured: yes")

    print(f"\n  embedded settings.yml      : {report['embedded_settings_path']}")
    print(f"  valid YAML                 : {report['embedded_settings_valid_yaml']}")
    if report.get("embedded_settings_error"):
        print(f"  ERROR                      : {report['embedded_settings_error']}")
    else:
        print(f"  overrides                  : {report['embedded_settings_overrides']}")

    print("\n  resolution order (first match wins):")
    active_step = _STEP_BY_SOURCE.get(report["effective_source"])
    for i, step in enumerate(report["resolution_order"], 1):
        marker = "  <-- effective" if i == active_step else ""
        print(f"    {i}. {step}{marker}")

    if "verify" in report:
        v = report["verify"]
        status = "OK" if v["ok"] else f"FAILED - {v.get('error')}"
        print(f"\n  --verify: {status}")
        if v.get("url"):
            print(f"    embedded instance came up healthy at {v['url']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="searxng-doctor",
        description=(
            "Resolve + verify the effective SearXNG configuration "
            "(embedded / external / random-public / searx.be fallback)."
        ),
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Actually spawn the embedded instance end to end and confirm it "
            "becomes healthy (requires the [embedded] extra), then stop it."
        ),
    )
    parser.add_argument(
        "--json", action="store_true", help="Machine-readable JSON output."
    )
    args = parser.parse_args()

    report = resolve_config()
    ok = report["embedded_settings_valid_yaml"] and (
        report["effective_source"] != "embedded" or report["embedded_extra_installed"]
    )

    if args.verify and report["embedded_would_activate"]:
        report["verify"] = verify_embedded()
        ok = ok and report["verify"]["ok"]

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _print_human(report)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
