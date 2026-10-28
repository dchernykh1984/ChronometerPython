"""The connector host with real child processes: events, restarts, give-ups, stop."""

from __future__ import annotations

import sys
import time

import shiboken6
from PySide6.QtWidgets import QApplication

from app import connector_host as ch
from app import connector_protocol as cp

HELLO = (
    'print(json.dumps({"type": "hello", "protocol": %d, "connector": "fake",'
    ' "kind": "%s"}), flush=True)'
)
GOOD = "\n".join(
    [
        "import json, sys",
        HELLO % (1, "beam"),
        "for line in sys.stdin:",
        "    cmd = json.loads(line)",
        "    if cmd.get('cmd') == 'start':",
        "        print('garbage', flush=True)",
        "        beam = {'type': 'beam', 'seq': 1, 'time_ms': 5}",
        "        print(json.dumps(beam), flush=True)",
        "    elif cmd.get('cmd') == 'ping':",
        "        print(json.dumps({'type': 'pong', 'id': cmd['id']}), flush=True)",
        "    elif cmd.get('cmd') == 'stop':",
        "        break",
    ]
)
# Waits for the end of its input, as a connector must when the chronometer goes.
SLEEP = "import sys; sys.stdin.read()"


def _python(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def _wait_until(condition, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


def _host(**kwargs) -> tuple[ch.ConnectorHost, list, list, list]:
    host = ch.ConnectorHost("beam", pause_scale=0.01, **kwargs)
    events: list[object] = []
    states: list[str] = []
    logs: list[str] = []
    host.received.connect(events.append)
    host.state_changed.connect(states.append)
    host.log.connect(logs.append)
    return host, events, states, logs


def test_a_running_connector_reports_its_events_and_stops():
    host, events, states, logs = _host()
    host.start(_python(GOOD), {"x": 1})
    assert _wait_until(lambda: events)
    assert events[0] == cp.Break(1, 5)
    assert states[:2] == ["starting", "running"]
    assert any("ignored" in line for line in logs)
    host.stop(wait=True)
    assert host.state == "stopped"


def test_a_crashing_connector_restarts_after_a_growing_pause():
    host, _, states, _ = _host()
    host.start(_python("import sys; sys.exit(3)"), {})
    assert _wait_until(lambda: "restarting in 4 s" in states)
    assert states.index("restarting in 1 s") < states.index("restarting in 2 s")
    host.stop(wait=True)


def test_a_connector_that_says_no_hello_is_restarted():
    host, _, states, logs = _host(hello_timeout_ms=300)
    host.start(_python(SLEEP), {})
    assert _wait_until(lambda: any("said no hello" in line for line in logs))
    assert "restarting in 1 s" in states
    host.stop(wait=True)


def test_a_connector_that_stops_answering_pings_is_restarted():
    deaf = "import json\n" + HELLO % (1, "beam") + "\n" + SLEEP
    host, _, _, logs = _host(ping_ms=100, pong_timeout_ms=300)
    host.start(_python(deaf), {})
    assert _wait_until(lambda: any("stopped answering" in line for line in logs))
    host.stop(wait=True)


def test_a_program_of_another_protocol_or_kind_is_stopped_for_good():
    for protocol, kind, why in (
        (2, "beam", "protocol 2"),
        (1, "chips", "chips connector"),
    ):
        host, _, states, _ = _host()
        host.start(
            _python("import json\n" + HELLO % (protocol, kind) + "\n" + SLEEP), {}
        )
        assert _wait_until(lambda h=host: h.state.startswith("failed"))
        assert why in host.state
        assert not _wait_until(lambda s=states: "starting" in s[2:], timeout=0.3)


def test_a_fatal_error_restarts_the_connector():
    fatal = "\n".join(
        [
            "import json, sys",
            HELLO % (1, "beam"),
            "sys.stdin.readline()",
            "print(json.dumps({'type': 'error', 'message': 'lost', 'fatal': True}),"
            " flush=True)",
            SLEEP,
        ]
    )
    host, events, _, logs = _host()
    host.start(_python(fatal), {})
    assert _wait_until(lambda: any("gave up: lost" in line for line in logs))
    assert events[0] == cp.Error("lost", True)
    host.stop(wait=True)


def test_a_program_that_cannot_start_is_retried():
    host, _, _, logs = _host()
    host.start(["/no/such/program"], {})
    assert _wait_until(lambda: any("could not start" in line for line in logs))
    host.stop()
    assert host.state == "stopped"


def test_the_pause_doubles_up_to_thirty_seconds_and_resets_after_a_steady_run():
    assert ch.next_pause(None, 0) == 1000
    assert ch.next_pause(1000, 10) == 2000
    assert ch.next_pause(16_000, 10) == 30_000
    assert ch.next_pause(30_000, 10) == 30_000
    assert ch.next_pause(8000, ch.STEADY_MS) == 1000


def test_built_in_connectors_run_from_the_chronometer_itself(monkeypatch):
    assert ch.builtin_command("dummy-beam")[1:] == [
        "-m",
        "app.main",
        "--connector",
        "dummy-beam",
    ]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert ch.builtin_command("dummy-beam") == [
        sys.executable,
        "--connector",
        "dummy-beam",
    ]


def test_a_stopped_connector_gets_its_grace_time_after_its_host_is_freed(tmp_path):
    closed = tmp_path / "closed"
    # Takes its time to stop, as a reader closing its session does.
    slow = "\n".join(
        [
            "import json, sys, time",
            HELLO % (1, "beam"),
            "sys.stdin.read()",
            "time.sleep(0.3)",
            f"open({str(closed)!r}, 'w').close()",
        ]
    )
    host, _, states, _ = _host()
    host.start(_python(slow), {})
    assert _wait_until(lambda: "running" in states)
    host.stop()
    shiboken6.delete(host)  # what the window's deleteLater does on its next turn
    assert _wait_until(closed.exists, timeout=5)
