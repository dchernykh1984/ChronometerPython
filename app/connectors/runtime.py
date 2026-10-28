"""What a built-in connector runs: hello, then commands in and events out.

The chronometer starts ``<chronometer> --connector <name>``; this module answers on
standard input and output with app.connector_protocol. Commands are read on a
thread of their own so a pending event is never held up by a blocked read, and the
end of standard input (the chronometer is gone) ends the connector.
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
from collections.abc import Callable
from typing import IO, Any

from app import connector_protocol as cp
from app.connectors import Events, builtin

_EOF = None


def run(name: str) -> int:
    """The process entry for ``--connector <name>``; returns the exit code."""
    found = builtin(name)
    if found is None:
        print(f"no built-in connector {name!r}", file=sys.stderr)
        return 2
    kind, events_for = found
    commands: queue.Queue[dict[str, Any] | None] = queue.Queue()
    reader = threading.Thread(
        target=read_commands, args=(sys.stdin.buffer, commands), daemon=True
    )
    reader.start()
    return serve(name, kind, events_for, commands, sys.stdout.buffer)


def read_commands(
    stream: IO[bytes], commands: queue.Queue[dict[str, Any] | None]
) -> None:
    for line in stream:
        try:
            command = json.loads(line)
        except ValueError:
            continue
        if isinstance(command, dict):
            commands.put(command)
    commands.put(_EOF)


def serve(
    name: str,
    kind: str,
    events_for: Callable[[dict[str, Any]], Events],
    commands: queue.Queue[dict[str, Any] | None],
    out: IO[bytes],
    clock: Callable[[], float] = time.monotonic,
) -> int:
    """Say hello, then emit events when due and answer commands until stopped."""

    def send(message: dict[str, Any]) -> None:
        out.write(cp.encode(message))
        out.flush()

    send({"type": "hello", "protocol": cp.PROTOCOL, "connector": name, "kind": kind})
    events: Events | None = None
    due: tuple[float, dict[str, Any]] | None = None
    while True:
        # A command that has arrived goes first: a stop must never wait behind events.
        try:
            if due is not None and clock() >= due[0]:
                command = commands.get_nowait()
            else:
                wait = None if due is None else max(0.0, due[0] - clock())
                command = commands.get(timeout=wait)
        except queue.Empty:
            if due is not None and clock() >= due[0]:
                send(_stamped(due[1]))
                due = _next(events, clock)
            continue
        if command is _EOF or command.get("cmd") == "stop":
            return 0
        if command.get("cmd") == "ping":
            send({"type": "pong", "id": command.get("id")})
        elif command.get("cmd") == "start" and events is None:
            events = events_for(command.get("settings") or {})
            due = _next(events, clock)


def _next(
    events: Events | None, clock: Callable[[], float]
) -> tuple[float, dict] | None:
    if events is None:
        return None
    try:
        pause, event = next(events)
    except StopIteration:
        return None
    return clock() + pause, event


def _stamped(event: dict[str, Any]) -> dict[str, Any]:
    """A read or a break carries the moment it happened on this computer's clock."""
    return {**event, "time_ms": event.get("time_ms", round(time.time() * 1000))}
