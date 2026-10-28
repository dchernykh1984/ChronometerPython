"""Start a built-in connector, read its hello, ask it to stop.

Usage: connector_smoke.py <command...>. "--connector dummy-beam" is appended, so the
command is the frozen chronometer, or "python -m app.main" in a checkout. Exits 0
when a protocol 1 beam hello comes first and the connector then ends cleanly.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading

HELLO_S = 60  # a onefile build unpacks itself before Python even starts
STOP_S = 30


def main(command: list[str]) -> int:
    child = subprocess.Popen(  # noqa: S603 - the build under test, by its path
        [*command, "--connector", "dummy-beam"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    if child.stdin is None or child.stdout is None:  # both are pipes: never
        return 1
    out = child.stdout
    lines: list[bytes] = []
    reader = threading.Thread(target=lambda: lines.append(out.readline()), daemon=True)
    reader.start()
    reader.join(HELLO_S)
    first = lines[0] if lines else b""
    print(f"first line: {first!r}")
    try:
        hello = json.loads(first)
    except ValueError:
        hello = None
    if not isinstance(hello, dict) or (
        hello.get("type"),
        hello.get("protocol"),
        hello.get("kind"),
    ) != ("hello", 1, "beam"):
        child.kill()
        return 1
    child.stdin.write(b'{"cmd": "stop"}\n')
    child.stdin.close()
    code = child.wait(STOP_S)
    print(f"connector exit code: {code}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
