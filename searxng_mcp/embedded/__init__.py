#!/usr/bin/env python
"""Embedded/in-process SearXNG fallback instance (CONCEPT:SR-KG.compute.embedded-instance).

Zero-config, self-contained search: when no external ``SEARXNG_URL``/
``SEARXNG_INSTANCE_URL`` is configured, this MCP server can own a PRIVATE
SearXNG process end to end — spawn it lazily on first search, bind it to
loopback only, and terminate it when the MCP process exits — instead of
falling back to a public instance (``searx.be`` / a random public instance),
which leaks queries to a third party and carries no reliability/rate-limit
guarantees. An operator who already runs a real instance (the fleet's own
``services/searxng`` on Kubernetes) sets ``SEARXNG_URL``, which always wins
and skips this module entirely — see ``mcp_server._perform_search``'s
resolution order (config -> embedded -> random public -> ``searx.be``).

**Opt-in dependency, opt-out behavior.** The ``searx`` package (installed via
the ``searxng-mcp[embedded]`` extra — SearXNG ships no PyPI release, only a
pip-installable git source, ``searxng @ git+https://github.com/searxng/searxng.git``)
is a heavy, optional dependency (Flask + lxml + a full engine suite), so it is
never imported unless installed (:func:`embedded_available`). When it IS
installed, embedding is the default (``SEARXNG_EMBEDDED=true``,
:func:`embedded_enabled`) — installing the extra is itself the opt-in; no
further config needed for zero-config self-contained search.

Runs ``python -m searx.webapp`` (the documented dev-server entrypoint —
SearXNG's own ``webapp.py`` ends with ``if __name__ == "__main__": run()``)
as a real SUBPROCESS, never a thread, so a crash is isolated and shutdown is
a clean SIGTERM. Bind/port/secret/limiter are pushed via the SAME env vars
SearXNG's own ``searx/settings_defaults.py`` reads
(``SEARXNG_BIND_ADDRESS``/``SEARXNG_PORT``/``SEARXNG_SECRET``/
``SEARXNG_LIMITER``/``SEARXNG_PUBLIC_INSTANCE``) rather than templating YAML —
the packaged ``embedded/settings.yml`` carries only the ONE setting with no
env-var equivalent (``search.formats`` must include ``json`` for
``_perform_search``'s ``format=json`` query param; upstream disables the JSON
API by default for public instances).

**Editable.** The packaged settings.yml ships read-only inside the wheel; a
user-writable override at :func:`user_settings_path` (XDG-style,
``$XDG_CONFIG_HOME/searxng-mcp/settings.yml``) takes precedence when present.
:func:`write_user_settings`/:func:`reset_user_settings` are the edit surface
— driven by the ``searxng_settings`` MCP tool (``mcp_server.py``) and the
``searxng-settings-editor`` skill, both effective only in embedded mode (an
externally-configured ``SEARXNG_URL`` owns its own settings.yml elsewhere).
"""

from __future__ import annotations

import atexit
import importlib.util
import logging
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from importlib import resources
from pathlib import Path
from typing import Any

import requests
import yaml
from agent_utilities.core.config import setting

logger = logging.getLogger("SearXNGMCPServer.embedded")

__all__ = [
    "EmbeddedSearXNG",
    "embedded_available",
    "embedded_enabled",
    "get_embedded_instance",
    "user_settings_path",
    "read_settings",
    "write_user_settings",
    "reset_user_settings",
]

_STARTUP_TIMEOUT_S = 20.0
_POLL_INTERVAL_S = 0.25
_HEALTH_TIMEOUT_S = 2.0


def embedded_available() -> bool:
    """Whether the ``searx`` package (the ``[embedded]`` extra) is installed."""
    return importlib.util.find_spec("searx") is not None


def embedded_enabled() -> bool:
    """``SEARXNG_EMBEDDED`` (default True) AND the extra is actually
    installed — an opt-out flag over an opt-in dependency (Native by default:
    an operator who installs the extra gets zero-config search with no
    further action; one who doesn't install it is unaffected — the existing
    random-instance/``searx.be`` fallback is unchanged)."""
    return bool(setting("SEARXNG_EMBEDDED", True)) and embedded_available()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _packaged_settings_path() -> Path:
    """Path to the packaged (read-only, ships-with-the-wheel) default
    embedded-mode settings.yml."""
    return Path(str(resources.files("searxng_mcp.embedded") / "settings.yml"))


def user_settings_path() -> Path:
    """The user-writable override (XDG-style, mirrors
    ``agent_utilities.core.workspace_config``'s
    ``XDG_CONFIG_HOME/agent-utilities`` convention). When present, this file
    — not the packaged default — is what the embedded instance actually
    loads; :func:`write_user_settings`/:func:`reset_user_settings` are the
    edit surface the ``searxng_settings`` MCP tool and the
    ``searxng-settings-editor`` skill drive."""
    base = Path(setting("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "searxng-mcp" / "settings.yml"


def _settings_path() -> str:
    """Path to the settings.yml the embedded instance loads: the user
    override when one exists, else the packaged default."""
    override = user_settings_path()
    if override.is_file():
        return str(override)
    return str(_packaged_settings_path())


def read_settings() -> dict[str, Any]:
    """The currently-active embedded settings.yml, parsed — whichever
    :func:`_settings_path` resolves to (user override if present, else the
    packaged default)."""
    with open(_settings_path(), encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def write_user_settings(overrides: dict[str, Any], *, merge: bool = True) -> Path:
    """Write ``overrides`` into the user-writable settings.yml override
    (:func:`user_settings_path`), creating the file/directory if needed.

    ``merge=True`` (default) deep-merges ``overrides`` onto whatever is
    currently active (the user override if one exists, else the packaged
    default) — so a caller only needs to name the keys it's changing, exactly
    like SearXNG's own settings.yml merge semantics
    (``searx/settings_loader.py:update_settings``). ``merge=False`` replaces
    the override file wholesale with ``overrides``.

    Does NOT restart a running embedded instance — SearXNG reads settings.yml
    once at process start, so a change here only takes effect on the NEXT
    spawn. Callers that want it applied immediately should
    ``get_embedded_instance().stop()`` afterward (the next search respawns
    with the new file) — this is exactly what the ``searxng_settings`` MCP
    tool's ``set`` action does.
    """
    path = user_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = read_settings() if merge else {}
    merged = _deep_merge(current, overrides) if merge else overrides
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(merged, f, sort_keys=False)
    return path


def reset_user_settings() -> bool:
    """Delete the user override, reverting to the packaged default on the
    next spawn. Returns whether a file was actually removed."""
    path = user_settings_path()
    if path.is_file():
        path.unlink()
        return True
    return False


class EmbeddedSearXNG:
    """Owns the lifecycle of ONE private, loopback-only SearXNG subprocess.

    :meth:`ensure_running` is idempotent + thread-safe: the first caller
    spawns the process and blocks (bounded by ``_STARTUP_TIMEOUT_S``) until it
    answers; every later caller (concurrent search calls) reuses the same
    instance. Registers an ``atexit`` handler so the subprocess never outlives
    the MCP server process.
    """

    def __init__(self, *, port: int | None = None) -> None:
        self._fixed_port = port
        self._proc: subprocess.Popen | None = None
        self._url: str | None = None
        self._lock = threading.Lock()
        self._secret = secrets.token_hex(16)

    @property
    def base_url(self) -> str | None:
        return self._url

    def _is_healthy(self) -> bool:
        if self._proc is None or self._proc.poll() is not None or not self._url:
            return False
        for path in ("/healthz", ""):
            try:
                resp = requests.get(f"{self._url}{path}", timeout=_HEALTH_TIMEOUT_S)
            except Exception as e:  # noqa: BLE001 — not up yet; try the next probe
                logger.debug("[SearXNG] health probe %s failed: %s", path or "/", e)
                continue
            if resp.status_code == 200 or (path == "" and resp.status_code < 500):
                return True
        return False

    def ensure_running(self) -> str:
        """Return the base URL of a running private instance, spawning one on
        first call. Raises ``RuntimeError`` if it fails to come up within the
        startup timeout — callers degrade to the existing public fallback."""
        with self._lock:
            if self._url and self._is_healthy():
                return self._url
            self._spawn()
            assert self._url is not None  # noqa: S101 — set unconditionally in _spawn
            return self._url

    def _spawn(self) -> None:
        self.stop()
        port = self._fixed_port or _free_port()
        env = {
            **os.environ,
            "SEARXNG_SETTINGS_PATH": _settings_path(),
            "SEARXNG_BIND_ADDRESS": "127.0.0.1",
            "SEARXNG_PORT": str(port),
            "SEARXNG_SECRET": self._secret,
            "SEARXNG_LIMITER": "false",
            "SEARXNG_PUBLIC_INSTANCE": "false",
            "SEARXNG_DEBUG": "false",
        }
        logger.info(f"[SearXNG] spawning embedded instance on 127.0.0.1:{port}")
        self._proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", "searx.webapp"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._url = f"http://127.0.0.1:{port}"
        atexit.register(self.stop)

        deadline = time.monotonic() + _STARTUP_TIMEOUT_S
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                code = self._proc.returncode
                self._url = None
                raise RuntimeError(f"embedded SearXNG exited early (code {code})")
            if self._is_healthy():
                return
            time.sleep(_POLL_INTERVAL_S)
        self.stop()
        raise RuntimeError("embedded SearXNG did not become healthy in time")

    def stop(self) -> None:
        """Terminate the subprocess (idempotent, safe to call repeatedly)."""
        proc, self._proc = self._proc, None
        self._url = None
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


_instance: EmbeddedSearXNG | None = None
_instance_lock = threading.Lock()


def get_embedded_instance() -> EmbeddedSearXNG:
    """The process-wide singleton — ONE embedded instance per MCP server
    process, shared by every search call."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = EmbeddedSearXNG()
        return _instance
