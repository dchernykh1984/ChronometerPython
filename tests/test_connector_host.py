"""The connector host with real child processes: events, restarts, give-ups, stop."""

from __future__ import annotations

import sys
import time

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
        "        beam = {'type': 'beam', 'seq': 1, 'time_ms': 1761725400005}",
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
    assert events[0] == cp.Break(1, 1761725400005)
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
        ended: list[int] = []
        host.stopped.connect(lambda e=ended: e.append(1))
        host.start(
            _python("import json\n" + HELLO % (protocol, kind) + "\n" + SLEEP), {}
        )
        assert _wait_until(lambda h=host: h.state.startswith("failed"))
        assert why in host.state
        assert not _wait_until(lambda s=states: "starting" in s[2:], timeout=0.3)
        assert _wait_until(lambda e=ended: e)  # its program has ended, too


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


def test_a_stopped_connector_ends_in_its_own_time_and_then_says_so(tmp_path):
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
    ended: list[int] = []
    host.stopped.connect(lambda: ended.append(1))
    host.start(_python(slow), {})
    assert _wait_until(lambda: "running" in states)
    host.stop()
    assert not ended  # still closing its session
    assert _wait_until(closed.exists, timeout=5)
    assert _wait_until(lambda: ended)


def test_the_pause_grows_for_a_connector_that_never_says_hello(monkeypatch):
    # The hello wait is as long as a steady run; time without a hello is no run.
    monkeypatch.setattr(ch, "STEADY_MS", 200)
    host, _, states, _ = _host(hello_timeout_ms=300)
    host.start(_python(SLEEP), {})
    assert _wait_until(lambda: "restarting in 2 s" in states)
    host.stop(wait=True)


def test_a_line_without_an_end_is_dropped_before_it_fills_the_memory():
    flood = "\n".join(
        [
            "import json, sys",
            HELLO % (1, "beam"),
            "sys.stdin.readline()",
            "sys.stdout.write('x' * 200000)",
            "sys.stdout.flush()",
            "sys.stdin.readline()",  # the first ping, 2 s later
            "print()",
            "beam = {'type': 'beam', 'seq': 1, 'time_ms': 1761725400005}",
            "print(json.dumps(beam), flush=True)",
            SLEEP,
        ]
    )
    host, events, _, logs = _host(ping_ms=2000)
    host.start(_python(flood), {})
    assert _wait_until(lambda: any("longer than" in line for line in logs), 1.5)
    assert len(host._buffer) <= cp.MAX_LINE
    assert _wait_until(lambda: events)
    assert events[0] == cp.Break(1, 1761725400005)
    assert not any("not JSON" in line for line in logs)  # its end went too
    host.stop(wait=True)


def test_a_hello_of_an_unknown_kind_or_a_text_protocol_stops_it_for_good():
    for hello, why in (
        ('{"type": "hello", "protocol": 1, "kind": "rfid"}', "a rfid connector"),
        ('{"type": "hello", "protocol": "1", "kind": "beam"}', "protocol '1'"),
    ):
        host, _, _, _ = _host()
        ended: list[int] = []
        host.stopped.connect(lambda e=ended: e.append(1))
        host.start(_python(f"print({hello!r}, flush=True)\n{SLEEP}"), {})
        assert _wait_until(lambda h=host: h.state.startswith("failed"))
        assert why in host.state
        assert _wait_until(lambda e=ended: e)


def test_events_already_sent_count_when_the_connector_is_stopped():
    late = "\n".join(
        [
            "import json, sys, time",
            HELLO % (1, "beam"),
            "sys.stdin.readline()",
            "time.sleep(0.2)",
            "for seq in (1, 2, 3):",
            "    beam = {'type': 'beam', 'seq': seq}",
            "    print(json.dumps(beam), flush=True)",
            SLEEP,
        ]
    )
    host, events, states, _ = _host()
    host.start(_python(late), {})
    assert _wait_until(lambda: "running" in states)
    _wait_until(lambda: False, timeout=0.05)  # the start command goes out
    time.sleep(0.6)  # the window was busy: the events wait in the pipe
    host.stop(wait=True)
    assert [event.seq for event in events] == [1, 2, 3]


def test_a_hello_read_while_stopping_starts_nothing():
    host, _, states, _ = _host()
    host.start(_python("import json\n" + HELLO % (1, "beam") + "\n" + SLEEP), {})
    assert _wait_until(lambda: host._process.state().name == "Running", 5)
    time.sleep(0.5)  # its hello waits in the pipe: the window was busy
    host.stop(wait=True)
    assert "running" not in states
    assert host.state == "stopped"
    assert not host._ping_timer.isActive()


def _beams_then(*tail: str) -> str:
    """A beam connector that, once started, writes tail's lines in one go."""
    return "\n".join(
        [
            "import json, sys, time",
            HELLO % (1, "beam"),
            "sys.stdin.readline()",
            *tail,
            SLEEP,
        ]
    )


def test_lines_sent_with_a_fatal_error_all_count():
    events_and_error = (
        "out = [{'type': 'beam', 'seq': 1}, {'type': 'error', 'message': 'lost',"
        " 'fatal': True}, {'type': 'beam', 'seq': 2}]"
    )
    code = _beams_then(
        events_and_error,
        "sys.stdout.write(''.join(json.dumps(x) + '\\n' for x in out))",
        "sys.stdout.flush()",
    )
    host, events, _, logs = _host()
    host.start(_python(code), {})
    assert _wait_until(lambda: any("gave up: lost" in line for line in logs))
    assert [type(e).__name__ for e in events] == ["Break", "Error", "Break"]
    host.stop(wait=True)


def test_reads_waiting_when_the_pongs_stop_still_count():
    code = _beams_then(
        "time.sleep(0.2)",
        "for seq in (1, 2):",
        "    print(json.dumps({'type': 'beam', 'seq': seq}), flush=True)",
    )
    host, events, states, logs = _host()
    host.start(_python(code), {})
    assert _wait_until(lambda: "running" in states)
    _wait_until(lambda: False, timeout=0.05)  # the start command goes out
    time.sleep(0.6)  # the window was busy: the events wait in the pipe
    host._last_pong = 0.0  # and the pong timeout has passed
    host._on_ping()
    assert [e.seq for e in events] == [1, 2]
    assert any("stopped answering" in line for line in logs)
    host.stop(wait=True)


def test_an_event_of_the_other_kind_is_logged_not_passed_on():
    code = _beams_then(
        "print(json.dumps({'type': 'read', 'chip': 'A1'}), flush=True)",
        "print(json.dumps({'type': 'beam', 'seq': 1}), flush=True)",
    )
    host, events, _, logs = _host()
    host.start(_python(code), {})
    assert _wait_until(lambda: events)
    assert events == [cp.Break(1, None)]
    assert any("a read on a beam source" in line for line in logs)
    host.stop(wait=True)


def test_a_connector_works_in_the_folder_the_data_is_in(tmp_path, monkeypatch):
    monkeypatch.setattr(ch, "base_dir", lambda: tmp_path)
    code = _beams_then(
        "import os",
        "beam = {'type': 'beam', 'seq': 1, 'device_time': os.getcwd()}",
        "print(json.dumps(beam), flush=True)",
    )
    host, events, _, _ = _host()
    host.start(_python(code), {})
    assert _wait_until(lambda: events)
    assert tmp_path.samefile(events[0].device_time)
    host.stop(wait=True)


def test_a_last_line_without_a_line_end_still_counts():
    code = "\n".join(
        [
            "import json, sys",
            HELLO % (1, "beam"),
            "sys.stdin.readline()",
            "sys.stdout.write(json.dumps({'type': 'beam', 'seq': 3}))",
            "sys.stdout.flush()",
        ]
    )
    host, events, _, logs = _host()
    host.start(_python(code), {})
    assert _wait_until(lambda: events)
    assert events[0] == cp.Break(3, None)
    assert _wait_until(lambda: any("exited" in line for line in logs))
    host.stop(wait=True)


def test_what_a_connector_reports_until_it_ends_after_stop_counts():
    code = _beams_then(
        "sys.stdin.readline()",  # the stop command
        "print(json.dumps({'type': 'beam', 'seq': 7}), flush=True)",
    )
    host, events, states, _ = _host()
    ended: list[int] = []
    host.stopped.connect(lambda: ended.append(1))
    host.start(_python(code), {})
    assert _wait_until(lambda: "running" in states)
    host.stop()
    assert _wait_until(lambda: ended)
    assert events == [cp.Break(7, None)]
    assert host.state == "stopped"
