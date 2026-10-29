"""The connector line protocol, version 1.

Described in specs/001-event-sources/contracts/connector-protocol.md: UTF-8 JSON
objects, one per line; commands go to a connector's standard input, events come
back on its standard output. Qt-free, so both sides and the tests share it.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

PROTOCOL = 1
MAX_LINE = 65536
KINDS = ("chips", "beam")
STATES = ("connecting", "connected", "disconnected")


@dataclass(frozen=True)
class Hello:
    connector: str
    kind: str
    protocol: int | str  # as sent; anything but PROTOCOL stops the program for good


@dataclass(frozen=True)
class Read:
    chip: str
    time_ms: int | None = None
    device_time: str = ""
    antenna: str = ""
    rssi: float | None = None
    reader: str = ""


@dataclass(frozen=True)
class Break:
    seq: int
    time_ms: int | None = None
    device_time: str = ""


@dataclass(frozen=True)
class Status:
    state: str
    detail: str = ""


@dataclass(frozen=True)
class Error:
    message: str
    fatal: bool = False


@dataclass(frozen=True)
class Pong:
    id: int


@dataclass(frozen=True)
class Ignored:
    """A line that is not protocol: logged by the chronometer, never acted on."""

    reason: str


Event = Hello | Read | Break | Status | Error | Pong | Ignored


def decode(line: bytes | str) -> Event:
    """One output line of a connector as an event, or the reason it is ignored."""
    if len(line) > MAX_LINE:
        return Ignored(f"line longer than {MAX_LINE} bytes")
    text = line.decode("utf-8", "replace") if isinstance(line, bytes) else line
    try:
        obj = json.loads(text)
    except ValueError:
        return Ignored(f"not JSON: {text.strip()[:80]}")
    if not isinstance(obj, dict):
        return Ignored("not a JSON object")
    kind = obj.get("type")
    decoder = _DECODERS.get(kind) if isinstance(kind, str) else None
    if decoder is None:
        return Ignored(f"unknown type {obj.get('type')!r}")
    try:
        return decoder(obj)
    except (TypeError, ValueError) as exc:
        return Ignored(f"bad {obj['type']}: {exc}")


def _text(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key, "")
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise TypeError(f"{key} must be text")
    return str(value)


def _whole(obj: dict[str, Any], key: str) -> int | None:
    value = obj.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{key} must be a whole number")
    return value


# An event's moment: from 2000 up to 2100. Earlier is a device clock never set
# (an uptime, say), which the results file's day count cannot even hold.
EARLIEST_MS = 946_684_800_000
LATEST_MS = 4_102_444_800_000


def _moment(obj: dict[str, Any]) -> int | None:
    """time_ms as a whole millisecond: a JSON number often has a fraction."""
    value = obj.get("time_ms")
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
    ):
        raise TypeError("time_ms must be a number")
    if not EARLIEST_MS <= value < LATEST_MS:
        raise ValueError("time_ms is out of range")
    return round(value)


def _hello(obj: dict[str, Any]) -> Event:
    """Any hello is one: the host checks what it names and stops a program of
    another protocol or kind for good, instead of waiting for a hello forever."""
    protocol = obj.get("protocol")
    if isinstance(protocol, bool) or not isinstance(protocol, int):
        protocol = repr(protocol)
    kind = obj.get("kind")
    connector = obj.get("connector")
    return Hello(
        "" if connector is None else str(connector),
        kind if isinstance(kind, str) else repr(kind),
        protocol,
    )


def _read(obj: dict[str, Any]) -> Event:
    chip = _text(obj, "chip").strip()
    if not chip:
        raise ValueError("chip is empty")
    rssi = obj.get("rssi")
    if rssi is not None and (
        isinstance(rssi, bool)
        or not isinstance(rssi, int | float)
        or not math.isfinite(rssi)
    ):
        raise TypeError("rssi must be a number")
    return Read(
        chip,
        _moment(obj),
        _text(obj, "device_time"),
        _text(obj, "antenna"),
        None if rssi is None else float(rssi),
        _text(obj, "reader"),
    )


def _break(obj: dict[str, Any]) -> Event:
    seq = _whole(obj, "seq")
    if seq is None:
        raise ValueError("seq is missing")
    return Break(seq, _moment(obj), _text(obj, "device_time"))


def _status(obj: dict[str, Any]) -> Event:
    state = obj.get("state")
    if state not in STATES:
        raise ValueError(f"state must be one of {STATES}")
    return Status(state, _text(obj, "detail"))


def _error(obj: dict[str, Any]) -> Event:
    return Error(_text(obj, "message"), obj.get("fatal") is True)


def _pong(obj: dict[str, Any]) -> Event:
    pong_id = _whole(obj, "id")
    if pong_id is None:
        raise ValueError("id is missing")
    return Pong(pong_id)


_DECODERS = {
    "hello": _hello,
    "read": _read,
    "beam": _break,
    "status": _status,
    "error": _error,
    "pong": _pong,
}


def encode(message: dict[str, Any]) -> bytes:
    """One protocol line: a command to a connector, or an event from one."""
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def start(settings: dict[str, Any]) -> bytes:
    return encode({"cmd": "start", "settings": settings})


def stop() -> bytes:
    return encode({"cmd": "stop"})


def ping(ping_id: int) -> bytes:
    return encode({"cmd": "ping", "id": ping_id})
