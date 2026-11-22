"""Start the built-in connectors, read their hello, ask them to stop.

Usage: connector_smoke.py <command...>. "--connector <name>" is appended, so the
command is the frozen chronometer, or "python -m app.main" in a checkout. Exits 0 when
each connector says a protocol 1 beam hello first and then ends cleanly. Beam boards
must also try a board on USB, which only a build with pyserial in it can, and look for
one on Bluetooth, which only a build with bleak's backend can: on a runner with no
Bluetooth either says its board is not there. The search must say what it found.
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
PICKS = [
    {"link": "usb", "port": NO_PORT, "kind": "beam-rp2040", "name": "cable"},
    {"link": "ble", "device": NO_BOARD, "name": "radio"},
]


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


def boards_tried(stdin: IO[bytes], out: IO[bytes]) -> bool:
    """Beam boards started on a board on each link: each said not there."""
    start = {"cmd": "start", "settings": {"boards": PICKS}}
    stdin.write((json.dumps(start) + "\n").encode())
    stdin.flush()
    unseen = {pick["name"] for pick in PICKS}
    while unseen:
        status = read_line(out, LINE_S)
        if status is None:
            return False
        if status.get("state") == "disconnected":
            unseen.discard(str(status.get("detail")).split(":")[0])
    return True


def searched(out: IO[bytes]) -> bool:
    """The search said what it found, after what it could not look on."""
    while (message := read_line(out, LINE_S)) is not None:
        if message.get("type") == "found":
            return True
    return False


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
    if ok and name == "beam-boards":
        ok = boards_tried(child.stdin, child.stdout)
    elif ok and name == "beam-scan":
        ok = searched(child.stdout)
    if not ok:
        child.kill()
        return 1
    if name != "beam-scan":  # the search ends by itself
        child.stdin.write(b'{"cmd": "stop"}\n')
    child.stdin.close()
    code = child.wait(STOP_S)
    print(f"{name} exit code: {code}")
    return code


def main(command: list[str]) -> int:
    for name in ("dummy-beam", "beam-boards", "beam-scan"):
        if code := smoke(command, name):
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
