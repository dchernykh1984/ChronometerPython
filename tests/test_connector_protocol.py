"""The connector line protocol: every event, every malformed line, the commands."""

from __future__ import annotations

import json

import pytest

from app import connector_protocol as cp


def _line(**fields) -> str:
    return json.dumps(fields)


def test_every_event_decodes():
    assert cp.decode(
        _line(type="hello", protocol=1, connector="dummy", kind="chips")
    ) == (cp.Hello("dummy", "chips", 1))
    assert cp.decode(
        _line(type="read", chip="a1", time_ms=5, antenna=2, rssi=-58.5, reader="r")
    ) == cp.Read("a1", 5, "", "2", -58.5, "r")
    assert cp.decode(_line(type="read", chip="A1")) == cp.Read("A1")
    assert cp.decode(_line(type="beam", seq=12, device_time="812")) == cp.Break(
        12, None, "812"
    )
    assert cp.decode(_line(type="status", state="connected")) == cp.Status("connected")
    assert cp.decode(_line(type="error", message="lost", fatal=True)) == cp.Error(
        "lost", True
    )
    assert cp.decode(_line(type="pong", id=7)) == cp.Pong(7)
    assert cp.decode(_line(type="pong", id=7).encode()) == cp.Pong(7)


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("not json", "not JSON"),
        ("[1, 2]", "not a JSON object"),
        (_line(type="mystery"), "unknown type"),
        (_line(cmd="ping"), "unknown type"),
        (_line(type="read", chip="  "), "chip is empty"),
        (_line(type="read", chip="A1", time_ms="5"), "whole number"),
        (_line(type="read", chip="A1", time_ms=True), "whole number"),
        (_line(type="read", chip="A1", rssi="loud"), "rssi"),
        (_line(type="read", chip={"x": 1}), "text"),
        (_line(type="beam"), "seq is missing"),
        (_line(type="status", state="sleeping"), "state"),
        (_line(type="hello", protocol=1, kind="video"), "kind"),
        (_line(type="hello", kind="beam"), "protocol"),
        (_line(type="pong"), "id"),
    ],
)
def test_a_line_that_is_not_protocol_is_ignored_with_a_reason(line, reason):
    event = cp.decode(line)
    assert isinstance(event, cp.Ignored)
    assert reason in event.reason


def test_a_line_over_the_limit_is_ignored():
    event = cp.decode("x" * (cp.MAX_LINE + 1))
    assert isinstance(event, cp.Ignored) and "longer" in event.reason


def test_unknown_fields_are_ignored():
    assert cp.decode(_line(type="pong", id=1, extra="later")) == cp.Pong(1)


def test_commands_are_json_lines():
    assert (
        cp.start({"chips": ["A1"]}) == b'{"cmd":"start","settings":{"chips":["A1"]}}\n'
    )
    assert cp.stop() == b'{"cmd":"stop"}\n'
    assert json.loads(cp.ping(3)) == {"cmd": "ping", "id": 3}
