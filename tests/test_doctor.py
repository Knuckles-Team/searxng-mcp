"""Regression tests for ``searxng-doctor``
(``searxng_mcp.doctor``, CONCEPT:SR-KG.compute.embedded-instance) — resolves
+ verifies the effective SearXNG configuration (explicit / embedded / random
public / ``searx.be`` fallback) without spawning a real subprocess.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from searxng_mcp import doctor


def _setting_stub(overrides):
    def _stub(key, default=None):
        return overrides.get(key, default)

    return _stub


def test_resolve_config_prefers_explicit_instance_url():
    with patch(
        "searxng_mcp.doctor.setting",
        _setting_stub({"SEARXNG_URL": "http://localhost:8080"}),
    ):
        report = doctor.resolve_config()
    assert report["effective_source"] == "explicit"
    assert report["effective_url"] == "http://localhost:8080"
    assert report["embedded_would_activate"] is False


def test_resolve_config_prefers_embedded_when_available():
    with (
        patch("searxng_mcp.doctor.setting", _setting_stub({})),
        patch("searxng_mcp.doctor.embedded_available", return_value=True),
        patch("searxng_mcp.doctor.embedded_enabled", return_value=True),
    ):
        report = doctor.resolve_config()
    assert report["effective_source"] == "embedded"
    assert report["embedded_would_activate"] is True
    assert "effective_url" not in report


def test_resolve_config_falls_back_to_random_instance():
    with (
        patch(
            "searxng_mcp.doctor.setting",
            _setting_stub({"USE_RANDOM_INSTANCE": True}),
        ),
        patch("searxng_mcp.doctor.embedded_available", return_value=False),
        patch("searxng_mcp.doctor.embedded_enabled", return_value=False),
    ):
        report = doctor.resolve_config()
    assert report["effective_source"] == "random-public-instance"


def test_resolve_config_falls_back_to_searx_be():
    with (
        patch("searxng_mcp.doctor.setting", _setting_stub({})),
        patch("searxng_mcp.doctor.embedded_available", return_value=False),
        patch("searxng_mcp.doctor.embedded_enabled", return_value=False),
    ):
        report = doctor.resolve_config()
    assert report["effective_source"] == "public-fallback"
    assert report["effective_url"] == "https://searx.be"


def test_resolve_config_reports_the_embedded_settings_file():
    with patch("searxng_mcp.doctor.setting", _setting_stub({})):
        report = doctor.resolve_config()
    assert report["embedded_settings_valid_yaml"] is True
    assert report["embedded_settings_overrides"]["search"]["formats"] == [
        "html",
        "json",
    ]


def test_verify_embedded_reports_missing_extra():
    with patch("searxng_mcp.doctor.embedded_available", return_value=False):
        result = doctor.verify_embedded()
    assert result["ok"] is False
    assert "embedded" in result["error"]


def test_verify_embedded_reports_success():
    class _FakeInstance:
        def ensure_running(self):
            return "http://127.0.0.1:18888"

        def stop(self):
            pass

    with (
        patch("searxng_mcp.doctor.embedded_available", return_value=True),
        patch("searxng_mcp.doctor.EmbeddedSearXNG", return_value=_FakeInstance()),
    ):
        result = doctor.verify_embedded()
    assert result == {"ok": True, "url": "http://127.0.0.1:18888"}


def test_verify_embedded_reports_failure_and_still_stops():
    calls = []

    class _FakeInstance:
        def ensure_running(self):
            raise RuntimeError("boom")

        def stop(self):
            calls.append("stopped")

    with (
        patch("searxng_mcp.doctor.embedded_available", return_value=True),
        patch("searxng_mcp.doctor.EmbeddedSearXNG", return_value=_FakeInstance()),
    ):
        result = doctor.verify_embedded()
    assert result == {"ok": False, "error": "boom"}
    assert calls == ["stopped"]


def test_main_exits_zero_on_explicit_config(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["searxng-doctor"])
    with patch(
        "searxng_mcp.doctor.setting",
        _setting_stub({"SEARXNG_URL": "http://localhost:8080"}),
    ):
        with pytest.raises(SystemExit) as exc:
            doctor.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "effective source" in out


def test_main_json_output(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["searxng-doctor", "--json"])
    with patch(
        "searxng_mcp.doctor.setting",
        _setting_stub({"SEARXNG_URL": "http://localhost:8080"}),
    ):
        with pytest.raises(SystemExit) as exc:
            doctor.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert '"effective_source": "explicit"' in out


def test_main_verify_flag_runs_end_to_end_check(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["searxng-doctor", "--verify"])
    with (
        patch("searxng_mcp.doctor.setting", _setting_stub({})),
        patch("searxng_mcp.doctor.embedded_available", return_value=True),
        patch("searxng_mcp.doctor.embedded_enabled", return_value=True),
        patch(
            "searxng_mcp.doctor.verify_embedded",
            return_value={"ok": True, "url": "http://127.0.0.1:18888"},
        ),
    ):
        with pytest.raises(SystemExit) as exc:
            doctor.main()
    assert exc.value.code == 0
    assert "came up healthy" in capsys.readouterr().out
