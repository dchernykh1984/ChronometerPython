"""Tests for the chronometer site-upload HTTP client (urllib mocked)."""

from __future__ import annotations

import io
import json

import pytest

from app import http_io


def _fake_urlopen(captured: dict):
    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _open(req, timeout=10):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp(
            json.dumps({"count": len(captured["body"].get("items", []))}).encode()
        )

    return _open


@pytest.fixture
def captured(monkeypatch):
    cap: dict = {}
    monkeypatch.setattr(http_io.urllib.request, "urlopen", _fake_urlopen(cap))
    return cap


def test_upload_finish_times(captured) -> None:
    n = http_io.upload_finish_times("https://s/", "tok", "dev", ["1#0 0:0:1#"], 3)
    assert n == 1
    assert captured["url"] == "https://s/api/v1/finish-times/"
    assert captured["body"] == {
        "competition_token": "tok",
        "device_id": "dev",
        "items": ["1#0 0:0:1#"],
        "client_revision": 3,
    }


def test_upload_group_times(captured) -> None:
    http_io.upload_group_times("https://s", "tok", "dev", ["G#0 0:0:1#"], 1)
    assert captured["url"] == "https://s/api/v1/group-times/"


def test_upload_remote_points_sends_point_number(captured) -> None:
    http_io.upload_remote_points("https://s", "tok", "dev", 2, ["1#0 0:1:0#"], 5)
    assert captured["url"] == "https://s/api/v1/remote-points/"
    assert captured["body"]["point_number"] == 2


def test_http_error_raises_valueerror(monkeypatch) -> None:
    import urllib.error

    def _boom(req, timeout=10):
        raise urllib.error.HTTPError(req.full_url, 409, "Conflict", {}, None)

    monkeypatch.setattr(http_io.urllib.request, "urlopen", _boom)
    with pytest.raises(ValueError, match="409"):
        http_io.upload_finish_times("https://s", "t", "d", [], 1)


def test_url_error_raises_valueerror(monkeypatch) -> None:
    import urllib.error

    def _boom(req, timeout=10):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(http_io.urllib.request, "urlopen", _boom)
    with pytest.raises(ValueError, match="Connection error"):
        http_io.upload_group_times("https://s", "t", "d", [], 1)


def test_invalid_json_raises_valueerror(monkeypatch) -> None:
    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        http_io.urllib.request, "urlopen", lambda req, timeout=10: _Resp(b"not json")
    )
    with pytest.raises(ValueError, match="Invalid response"):
        http_io.upload_remote_points("https://s", "t", "d", 1, [], 1)


# -- fetch_groups ----------------------------------------------------------


def _groups_response(categories: list[dict]):
    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return _Resp(json.dumps({"categories": categories}).encode())


def test_fetch_groups_returns_names_only(monkeypatch) -> None:
    cats: list[dict] = [{"name": "Elite", "laps": 5}, {"name": "Junior", "laps": None}]
    monkeypatch.setattr(
        http_io.urllib.request,
        "urlopen",
        lambda url, timeout=10: _groups_response(cats),
    )
    assert http_io.fetch_groups("https://s", "tok") == ["Elite", "Junior"]


def test_fetch_groups_skips_blanks_and_dedups(monkeypatch) -> None:
    cats = [{"name": "A"}, {"name": "  "}, {"name": "A"}, {"name": "B"}]
    monkeypatch.setattr(
        http_io.urllib.request,
        "urlopen",
        lambda url, timeout=10: _groups_response(cats),
    )
    assert http_io.fetch_groups("https://s", "tok") == ["A", "B"]


def test_fetch_groups_url_and_token(monkeypatch) -> None:
    captured: dict = {}

    def _open(url, timeout=10):
        captured["url"] = url
        captured["timeout"] = timeout
        return _groups_response([])

    monkeypatch.setattr(http_io.urllib.request, "urlopen", _open)
    http_io.fetch_groups("https://s/", "abc-uuid")
    assert captured["url"].startswith("https://s/api/v1/participants/")
    assert "competition_token=abc-uuid" in captured["url"]
    assert captured["timeout"] == 10


def test_fetch_groups_http_error_raises(monkeypatch) -> None:
    import urllib.error

    def _boom(url, timeout=10):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(http_io.urllib.request, "urlopen", _boom)
    with pytest.raises(ValueError, match="401"):
        http_io.fetch_groups("https://s", "bad")


def test_fetch_groups_offline_raises(monkeypatch) -> None:
    import urllib.error

    def _boom(url, timeout=10):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(http_io.urllib.request, "urlopen", _boom)
    with pytest.raises(ValueError, match="Connection error"):
        http_io.fetch_groups("https://s", "tok")


def test_fetch_groups_invalid_json_raises(monkeypatch) -> None:
    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        http_io.urllib.request, "urlopen", lambda url, timeout=10: _Resp(b"not json")
    )
    with pytest.raises(ValueError, match="Invalid response"):
        http_io.fetch_groups("https://s", "tok")
