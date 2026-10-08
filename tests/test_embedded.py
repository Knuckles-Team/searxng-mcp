"""Regression tests for the embedded/in-process SearXNG fallback
(``searxng_mcp.embedded``, CONCEPT:SR-KG.compute.embedded-instance) — a
private, loopback-only SearXNG subprocess this MCP server can own end to end
when no external instance is configured, instead of leaking queries to a
public instance. No real ``searx`` package or subprocess is spawned in these
tests — ``subprocess.Popen``/``requests.get`` are mocked throughout.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
import requests

from searxng_mcp import embedded


def _fake_running_proc(returncode=None):
    proc = MagicMock(spec=subprocess.Popen)
    proc.poll.return_value = returncode
    proc.returncode = returncode
    return proc


def _fake_response(status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# ── availability / enablement ───────────────────────────────────────────────


def test_embedded_available_false_without_searx_package():
    with patch("importlib.util.find_spec", return_value=None):
        assert embedded.embedded_available() is False


def test_embedded_available_true_when_searx_importable():
    with patch("importlib.util.find_spec", return_value=MagicMock()):
        assert embedded.embedded_available() is True


def test_embedded_enabled_default_true_when_available():
    with (
        patch("searxng_mcp.embedded.setting", return_value=True),
        patch("searxng_mcp.embedded.embedded_available", return_value=True),
    ):
        assert embedded.embedded_enabled() is True


def test_embedded_enabled_false_when_extra_not_installed():
    with (
        patch("searxng_mcp.embedded.setting", return_value=True),
        patch("searxng_mcp.embedded.embedded_available", return_value=False),
    ):
        assert embedded.embedded_enabled() is False


def test_embedded_enabled_respects_explicit_opt_out():
    with (
        patch("searxng_mcp.embedded.setting", return_value=False),
        patch("searxng_mcp.embedded.embedded_available", return_value=True),
    ):
        assert embedded.embedded_enabled() is False


# ── EmbeddedSearXNG lifecycle ───────────────────────────────────────────────


def test_ensure_running_spawns_a_subprocess_and_returns_its_url():
    instance = embedded.EmbeddedSearXNG(port=18888)
    fake_proc = _fake_running_proc()

    with (
        patch("searxng_mcp.embedded.subprocess.Popen", return_value=fake_proc) as popen,
        patch("searxng_mcp.embedded.requests.get", return_value=_fake_response()),
        patch("searxng_mcp.embedded.atexit.register"),
    ):
        url = instance.ensure_running()

    assert url == "http://127.0.0.1:18888"
    args, kwargs = popen.call_args
    assert args[0][-2:] == ["-m", "searx.webapp"]
    env = kwargs["env"]
    assert env["SEARXNG_BIND_ADDRESS"] == "127.0.0.1"
    assert env["SEARXNG_PORT"] == "18888"
    assert env["SEARXNG_LIMITER"] == "false"
    assert env["SEARXNG_PUBLIC_INSTANCE"] == "false"
    assert "SEARXNG_SETTINGS_PATH" in env
    assert "SEARXNG_SECRET" in env


def test_ensure_running_is_idempotent_when_already_healthy():
    instance = embedded.EmbeddedSearXNG(port=18889)
    fake_proc = _fake_running_proc()

    with (
        patch("searxng_mcp.embedded.subprocess.Popen", return_value=fake_proc) as popen,
        patch("searxng_mcp.embedded.requests.get", return_value=_fake_response()),
        patch("searxng_mcp.embedded.atexit.register"),
    ):
        first = instance.ensure_running()
        second = instance.ensure_running()

    assert first == second
    popen.assert_called_once()


def test_ensure_running_raises_when_process_exits_early():
    instance = embedded.EmbeddedSearXNG(port=18890)
    fake_proc = _fake_running_proc(returncode=1)

    with (
        patch("searxng_mcp.embedded.subprocess.Popen", return_value=fake_proc),
        patch("searxng_mcp.embedded.atexit.register"),
    ):
        with pytest.raises(RuntimeError, match="exited early"):
            instance.ensure_running()


def test_ensure_running_raises_on_health_check_timeout():
    instance = embedded.EmbeddedSearXNG(port=18891)
    fake_proc = _fake_running_proc()

    with (
        patch("searxng_mcp.embedded.subprocess.Popen", return_value=fake_proc),
        patch(
            "searxng_mcp.embedded.requests.get",
            side_effect=requests.ConnectionError("down"),
        ),
        patch("searxng_mcp.embedded.atexit.register"),
        patch("searxng_mcp.embedded._STARTUP_TIMEOUT_S", 0.05),
        patch("searxng_mcp.embedded._POLL_INTERVAL_S", 0.01),
    ):
        with pytest.raises(RuntimeError, match="did not become healthy"):
            instance.ensure_running()


def test_stop_terminates_a_running_process():
    instance = embedded.EmbeddedSearXNG(port=18892)
    fake_proc = _fake_running_proc()
    instance._proc = fake_proc
    instance._url = "http://127.0.0.1:18892"

    instance.stop()

    fake_proc.terminate.assert_called_once()
    assert instance._proc is None
    assert instance._url is None


def test_stop_is_a_noop_when_nothing_is_running():
    instance = embedded.EmbeddedSearXNG()
    instance.stop()  # must not raise


def test_get_embedded_instance_is_a_process_wide_singleton():
    embedded._instance = None
    try:
        first = embedded.get_embedded_instance()
        second = embedded.get_embedded_instance()
        assert first is second
    finally:
        embedded._instance = None


# ── settings.yml edit surface (user override over the packaged default) ────


@pytest.fixture
def xdg_home(tmp_path, monkeypatch):
    monkeypatch.setattr(
        embedded,
        "setting",
        lambda key, default=None: (
            str(tmp_path) if key == "XDG_CONFIG_HOME" else default
        ),
    )
    return tmp_path


def test_user_settings_path_is_xdg_scoped(xdg_home):
    assert embedded.user_settings_path() == xdg_home / "searxng-mcp" / "settings.yml"


def test_read_settings_falls_back_to_packaged_default(xdg_home):
    assert not embedded.user_settings_path().is_file()
    settings = embedded.read_settings()
    assert settings["search"]["formats"] == ["html", "json"]


def test_write_user_settings_merges_onto_the_packaged_default(xdg_home):
    path = embedded.write_user_settings({"general": {"enable_metrics": True}})
    assert path == embedded.user_settings_path()
    assert path.is_file()

    merged = embedded.read_settings()
    assert merged["general"]["enable_metrics"] is True
    assert merged["search"]["formats"] == ["html", "json"]  # preserved
    assert embedded._settings_path() == str(path)  # override now wins


def test_write_user_settings_replace_mode_discards_prior_overrides(xdg_home):
    embedded.write_user_settings({"general": {"enable_metrics": True}})
    embedded.write_user_settings({"search": {"formats": ["json"]}}, merge=False)

    assert embedded.read_settings() == {"search": {"formats": ["json"]}}


def test_reset_user_settings_reverts_to_the_packaged_default(xdg_home):
    embedded.write_user_settings({"general": {"enable_metrics": True}})
    assert embedded.reset_user_settings() is True
    assert not embedded.user_settings_path().is_file()
    assert embedded.read_settings()["general"]["enable_metrics"] is False


def test_reset_user_settings_is_idempotent(xdg_home):
    assert embedded.reset_user_settings() is False
