"""Start the built-in connectors, read their hello, ask them to stop.

Usage: connector_smoke.py <command...>. "--connector <name>" is appended, so the
command is the frozen chronometer, or "python -m app.main" in a checkout. Exits 0 when
each connector says a protocol 1 beam hello first and then ends cleanly; a beam board
on USB must also try a port, which only a build with pyserial in it can, and one on
Bluetooth must look for its board, which only a build with bleak's backend can: on a
runner with no Bluetooth either says the board is not there.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from typing import IO, Any

HELLO_S = 60  # a onefile build unpacks itself before Python even starts
LINE_S = 30
STOP_S = 30
# A port no computer has: opening it fails, which says pyserial is there to try.
NO_PORT = "COM250" if sys.platform == "win32" else "/dev/no-such-beam-board"
NO_BOARD = "beam-0000"  # a Bluetooth board no runner has in range
TRIES = {
    "beam-rp2040": {"port": NO_PORT},
    "beam-esp32c3-ble": {"device": NO_BOARD},
}


def read_line(out: IO[bytes], seconds: float) -> dict[str, Any] | None:
    """The connector's next line as JSON, or None when none came in time."""
    lines: list[bytes] = []
    reader = threading.Thread(target=lambda: lines.append(out.readline()), daemon=True)
    reader.start()
    reader.join(seconds)
    first = lines[0] if lines else b""
    print(f"line: {first!r}")
    try:
        message = json.loads(first)
    except ValueError:
        return None
    return message if isinstance(message, dict) else None


def smoke(command: list[str], name: str) -> int:
    child = subprocess.Popen(  # noqa: S603 - the build under test, by its path
        [*command, "--connector", name],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    if child.stdin is None or child.stdout is None:  # both are pipes: never
        return 1
    hello = read_line(child.stdout, HELLO_S)
    ok = hello is not None and (
        hello.get("type"),
        hello.get("protocol"),
        hello.get("kind"),
    ) == ("hello", 1, "beam")
    if ok and name in TRIES:
        start = {"cmd": "start", "settings": TRIES[name]}
        child.stdin.write((json.dumps(start) + "\n").encode())
        child.stdin.flush()
        status = read_line(child.stdout, LINE_S)
        ok = status is not None and status.get("state") == "disconnected"
    if not ok:
        child.kill()
        return 1
    child.stdin.write(b'{"cmd": "stop"}\n')
    child.stdin.close()
    code = child.wait(STOP_S)
    print(f"{name} exit code: {code}")
    return code


def main(command: list[str]) -> int:
    for name in ("dummy-beam", *TRIES):
        if code := smoke(command, name):
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
