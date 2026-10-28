"""Built-in connectors: the registry, the test sources and the process loop."""

from __future__ import annotations

import io
import itertools
import json
import queue
import subprocess
import sys

from app import connectors
from app.connectors import dummy_beam, dummy_chips, runtime


def test_the_registry_lists_test_connectors_custom_and_stubs():
    chips = {c.name: c for c in connectors.connectors_for("chips")}
    assert {"dummy-chips", "custom", "llrp", "raceresult", "r2000"} <= set(chips)
    assert "dummy-beam" not in chips
    assert chips["dummy-chips"].test and chips["dummy-chips"].available
    assert not chips["llrp"].available
    beam = {c.name for c in connectors.connectors_for("beam")}
    assert {"dummy-beam", "custom", "beam-usb", "beam-ble"} <= beam
    assert connectors.find("beam-ble").kind == "beam"
    assert connectors.find("nothing") is None
    assert connectors.builtin("dummy-beam")[0] == "beam"
    assert connectors.builtin("llrp") is None


def test_test_chips_pass_riders_in_turn_with_a_few_reads_each():
    riders = [["A1", "A2"], ["B1"]]
    reads = list(
        itertools.islice(
            dummy_chips.events({"riders": riders, "period_s": 3, "seed": 1}), 60
        )
    )
    passes, current = [], None
    for pause, event in reads:
        assert event["type"] == "read" and event["reader"] == "dummy"
        if pause == 3:
            current = []
            passes.append(current)
        else:
            assert 0 < pause < 1
        current.append(event["chip"])
    assert all(2 <= len(p) <= 4 for p in passes[:-1])
    assert set(passes[0]) <= {"A1", "A2"} and set(passes[1]) == {"B1"}
    assert set(passes[9]) == {dummy_chips.UNKNOWN_CHIP}


def test_test_chips_without_a_map_read_only_an_unknown_chip():
    chips = {e["chip"] for _, e in itertools.islice(dummy_chips.events({}), 20)}
    assert chips == {dummy_chips.UNKNOWN_CHIP}


def test_test_beam_counts_its_breaks():
    breaks = list(itertools.islice(dummy_beam.events({"min_s": 1, "max_s": 2}), 5))
    assert [e["seq"] for _, e in breaks] == [1, 2, 3, 4, 5]
    assert all(1 <= pause <= 2 for pause, _ in breaks)


def _serve(commands, source, q=None):
    out = io.BytesIO()
    q = q or queue.Queue()
    for command in commands:
        q.put(command)
    code = runtime.serve("test", "chips", source, q, out)
    return code, [json.loads(line) for line in out.getvalue().splitlines()]


def test_the_loop_says_hello_emits_events_and_answers_pings():
    q: queue.Queue = queue.Queue()

    def source(settings):
        assert settings == {"x": 1}
        yield 0.0, {"type": "read", "chip": "A1"}
        yield 0.0, {"type": "read", "chip": "B1", "time_ms": 5}
        # The chronometer pings and then goes away, once the events are out.
        q.put({"cmd": "ping", "id": 9})
        q.put(None)

    code, lines = _serve([{"cmd": "start", "settings": {"x": 1}}], source, q)
    assert code == 0
    assert lines[0] == {
        "type": "hello",
        "protocol": 1,
        "connector": "test",
        "kind": "chips",
    }
    assert lines[1]["chip"] == "A1" and isinstance(lines[1]["time_ms"], int)
    assert lines[2]["time_ms"] == 5  # a time the device gave is kept
    assert lines[3] == {"type": "pong", "id": 9}


def test_a_stop_is_not_held_up_by_events_that_never_pause():
    def source(settings):
        while True:
            yield 0.0, {"type": "beam", "seq": 1}

    code, lines = _serve([{"cmd": "start"}, {"cmd": "stop"}], source)
    assert code == 0
    assert [line["type"] for line in lines] == ["hello"]


def test_stop_ends_the_loop_and_a_second_start_is_ignored():
    started = []

    def source(settings):
        started.append(settings)
        return iter(())

    code, lines = _serve(
        [{"cmd": "start"}, {"cmd": "start"}, {"cmd": "stop"}, {"cmd": "ping", "id": 1}],
        source,
    )
    assert code == 0
    assert len(started) == 1
    assert [line["type"] for line in lines] == ["hello"]


def test_commands_are_read_until_the_input_ends():
    q: queue.Queue = queue.Queue()
    runtime.read_commands(io.BytesIO(b'{"cmd":"ping","id":1}\nnoise\n[1]\n'), q)
    assert q.get_nowait() == {"cmd": "ping", "id": 1}
    assert q.get_nowait() is None


def test_an_unknown_connector_name_fails():
    assert runtime.run("nothing") == 2


def test_the_chronometer_runs_a_test_beam_as_a_process_of_its_own():
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main", "--connector", "dummy-beam"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert process.stdin and process.stdout
    hello = json.loads(process.stdout.readline())
    assert hello["kind"] == "beam" and hello["protocol"] == 1
    process.stdin.write(b'{"cmd":"start","settings":{"min_s":0.05,"max_s":0.05}}\n')
    process.stdin.flush()
    assert json.loads(process.stdout.readline())["type"] == "beam"
    process.stdin.write(b'{"cmd":"stop"}\n')
    process.stdin.close()
    assert process.wait(timeout=10) == 0


def test_replay_plays_a_reads_file_at_its_own_pace(tmp_path):
    from app.connectors import replay

    reads = tmp_path / "results.chip_reads.txt"
    reads.write_text(
        "A#1 10:0:0.000#dev1#1#-58.5#r1#\n"
        "B#1 10:0:0.300##2##r1#\n"
        "not a read\n"
        "A#1 10:0:2.000##1#-60#r1#\n"
        "A#1 10:0:9.000#####\n",
        encoding="utf-8",
    )
    played = list(replay.events({"path": str(reads)}))
    assert [round(p, 3) for p, _ in played] == [0, 0.3, 1.7, 7.0]
    assert played[0][1] == {
        "type": "read",
        "chip": "A",
        "device_time": "dev1",
        "antenna": "1",
        "rssi": -58.5,
        "reader": "r1",
    }
    assert played[3][1] == {"type": "read", "chip": "A"}
    fast = [p for p, _ in replay.events({"path": str(reads), "speed": 10})]
    assert [round(p, 3) for p in fast] == [0, 0.03, 0.17, 0.7]


def test_replay_of_a_missing_file_plays_nothing(tmp_path):
    from app.connectors import replay

    assert list(replay.events({"path": str(tmp_path / "none.txt")})) == []
    assert connectors.find("replay").test


def test_a_connector_told_to_stop_exits_cleanly_while_its_input_stays_open():
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main", "--connector", "dummy-beam"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert process.stdin and process.stdout
    process.stdout.readline()  # hello
    process.stdin.write(b'{"cmd":"stop"}\n')
    process.stdin.flush()
    try:
        assert process.wait(timeout=10) == 0  # not an abort at interpreter shutdown
    finally:
        process.stdin.close()
