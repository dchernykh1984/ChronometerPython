"""The beam board's connector, firmware/beam_rp2040/connector.py: the board's lines
as the chronometer's events, the board's clock moved onto the computer's, and the
loop between the two, with a board on a fake port standing in for the real one."""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
import types
from collections.abc import Iterator
from typing import Any

import pytest

from firmware.beam_rp2040 import connector as c

HELLO = "HELLO beam-rp2040 0.1 e6614103"


def _connected() -> c.Bridge:
    bridge = c.Bridge()
    bridge.from_board(HELLO, 0.0)
    return bridge


def test_a_board_line_is_its_word_and_the_rest():
    assert c.parse("break 12 812345\r") == ("BREAK", ["12", "812345"])
    assert c.parse("  ") == ("", [])


@pytest.mark.parametrize(
    "rest", [["1"], ["1", "2", "3"], ["1", "-2"], ["x", "2"], ["1.5", "2"]]
)
def test_a_break_or_pong_without_two_whole_numbers_carries_none(rest):
    assert c.pair(rest) is None


def test_the_board_clock_maps_onto_the_middle_of_a_round_trip():
    sync = c.ClockSync()
    assert sync.to_host_ms(2_000_000) is None
    sync.add(sent_ms=1_000_000.0, got_ms=1_000_004.0, board_us=2_000_000)
    assert sync.to_host_ms(2_000_000) == 1_000_002
    assert sync.to_host_ms(3_500_000) == 1_001_502


def test_a_round_trip_too_long_to_say_when_the_board_answered_is_left_out():
    sync = c.ClockSync()
    sync.add(0.0, c.LONGEST_TRIP_MS + 0.1, 0)
    assert sync.to_host_ms(0) is None
    sync.add(0.0, c.LONGEST_TRIP_MS, 0)
    assert sync.to_host_ms(0) == round(c.LONGEST_TRIP_MS / 2)


def test_the_offset_is_the_median_of_the_last_nine_round_trips():
    sync = c.ClockSync()
    for offset in [0.0] * c.SAMPLES + [500.0] * 5:
        sync.add(offset, offset, 0)
    assert sync.to_host_ms(0) == 500  # five of the last nine: the oldest have gone
    sync.add(9_000.0, 9_000.0, 0)  # one far off moves it no further
    assert sync.to_host_ms(0) == 500


def test_pings_are_numbered_and_the_long_unanswered_ones_dropped():
    bridge = c.Bridge()
    lines = [bridge.ping(float(n)) for n in range(1, 4 * c.SAMPLES + 2)]
    assert lines[:2] == ["PING 1", "PING 2"]
    assert sorted(bridge.pings) == list(range(2, 4 * c.SAMPLES + 2))
    assert bridge.pings[2] == 2.0


def test_a_board_that_answers_no_ping_for_six_seconds_is_silent():
    bridge = _connected()
    bridge.ping(0.0)
    assert not bridge.silent(c.SILENT_MS)
    assert bridge.silent(c.SILENT_MS + 1)
    bridge.ping(5_000.0)
    bridge.from_board("PONG 2 10", 5_003.0)  # a later one answered: the board is there
    assert not bridge.silent(10**12)


def test_nothing_counts_before_the_board_says_its_hello():
    """Lines left from before the HELLO asked for, or a board that runs another
    firmware, stamp no slot."""
    bridge = c.Bridge()
    assert bridge.from_board("BREAK 1 1000", 5.0) == []
    assert bridge.from_board("HELLO another-board 1", 5.0) == []
    assert bridge.from_board("BREAK 2 1000", 5.0) == []
    assert bridge.from_board(HELLO, 5.0) == [
        {"type": "status", "state": "connected", "detail": HELLO[6:]}
    ]
    assert len(bridge.from_board("BREAK 3 1000", 5.0)) == 1


def test_a_break_before_any_round_trip_has_the_time_its_line_came():
    assert _connected().from_board("BREAK 12 812345", 1_761_725_401_500.4) == [
        {
            "type": "beam",
            "seq": 12,
            "time_ms": 1_761_725_401_500,
            "device_time": "812345",
        }
    ]


def test_a_break_has_the_board_time_moved_onto_the_computer_clock():
    bridge = _connected()
    n = bridge.ping(1_000_000.0).split()[1]
    assert bridge.from_board(f"PONG {n} 2000000", 1_000_004.0) == []
    [event] = bridge.from_board("BREAK 3 3500000", 9_999_999.0)  # its line came late
    assert event["time_ms"] == 1_001_502


def test_a_pong_for_no_ping_or_answered_twice_is_left_out():
    bridge = _connected()
    bridge.from_board("PONG 5 2000000", 1.0)
    assert bridge.sync.offsets == []
    pong = f"PONG {bridge.ping(0.0).split()[1]} 0"
    bridge.from_board(pong, 2.0)
    bridge.from_board(pong, 4.0)
    assert bridge.sync.offsets == [1.0]


def test_a_board_error_is_said_and_its_other_lines_are_its_own_business():
    bridge = _connected()
    assert bridge.from_board("ERROR unknown: XYZ", 0.0) == [
        {"type": "error", "message": "board: unknown: XYZ"}
    ]
    for line in ["STATUS beam", "FLASH 1 5", "HOLDOFF 300", "", "BREAK x 1"]:
        assert bridge.from_board(line, 0.0) == []


@pytest.mark.parametrize("given", ["-5", "0", "60001", "1.5", "x"])
def test_a_hold_off_out_of_range_is_refused_at_start(given, capsys):
    """Refused where the chronometer's log shows it, before any board is opened."""
    with pytest.raises(SystemExit) as ended:
        c.main(["--hold-off-ms", given])
    assert ended.value.code == 2
    assert "--hold-off-ms" in capsys.readouterr().err


def test_a_hold_off_in_range_is_taken():
    assert (c.hold_off("1"), c.hold_off("60000")) == (1, 60_000)


def test_the_port_named_is_used_else_the_first_raspberry_pi_one(monkeypatch):
    assert c.board_port("COM7") == "COM7"
    ports = [
        types.SimpleNamespace(device="/dev/cu.usbmodem201", vid=c.RASPBERRY_PI_USB),
        types.SimpleNamespace(device="/dev/cu.Bluetooth-Incoming-Port", vid=None),
        types.SimpleNamespace(device="/dev/cu.usbmodem101", vid=c.RASPBERRY_PI_USB),
        types.SimpleNamespace(device="/dev/cu.usbserial-10", vid=0x0403),
    ]
    tools = types.ModuleType("serial.tools")
    tools.list_ports = types.SimpleNamespace(comports=lambda: ports)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "serial", types.ModuleType("serial"))
    monkeypatch.setitem(sys.modules, "serial.tools", tools)
    assert c.board_port("") == "/dev/cu.usbmodem101"
    del ports[0], ports[1]
    assert c.board_port("") is None


# -- the loop, with a board on a fake port ------------------------------------


class SerialError(Exception):
    """pyserial's SerialException, for the fake port."""


class Port:
    """A beam board running main.py on a serial port: it answers HELLO and PING as
    the firmware does, at board time ``answers_at``, and says what a test makes it
    say."""

    answers_at = 2_000_000
    answering = True  # False: main.py has stopped, the port is still open

    def __init__(
        self, device: str, timeout: float | None, exclusive: bool | None
    ) -> None:
        self.device, self.closed, self.exclusive = device, False, exclusive
        self.written: list[str] = []
        self.said: queue.Queue[bytes | Exception | None] = queue.Queue()

    def write(self, data: bytes) -> int:
        for line in data.decode().split("\n")[:-1]:
            self.written.append(line)
            if line == "HELLO":
                self.say(HELLO)
            elif line.startswith("PING ") and self.answering:
                self.say(f"PONG {line.split()[1]} {self.answers_at}")
        return len(data)

    def say(self, line: str) -> None:
        self.said.put(f"{line}\r\n".encode())

    def __iter__(self) -> Iterator[bytes]:
        while (item := self.said.get()) is not None:
            if isinstance(item, Exception):
                raise item
            yield item

    def close(self) -> None:
        self.closed = True
        self.said.put(None)


class Chronometer:
    """The chronometer's side: commands written to the connector, events read."""

    def __init__(self) -> None:
        self.commands: queue.Queue[bytes | None] = queue.Queue()
        self.events: queue.Queue[dict[str, Any]] = queue.Queue()

    def __iter__(self) -> Iterator[bytes]:  # the connector's standard input
        while (line := self.commands.get()) is not None:
            yield line

    def write(self, text: str) -> int:  # its standard output
        self.events.put(json.loads(text))
        return len(text)

    def flush(self) -> None:
        pass

    def tell(self, command: dict[str, Any] | None) -> None:
        line = None if command is None else (json.dumps(command) + "\n").encode()
        self.commands.put(line)

    def next(self) -> dict[str, Any]:
        return self.events.get(timeout=5)


def _run(connector: c.Connector, chronometer: Chronometer) -> list[int]:
    ended: list[int] = []
    threading.Thread(
        target=lambda: ended.append(connector.run(chronometer)), daemon=True
    ).start()
    assert chronometer.next() == {
        "type": "hello",
        "protocol": 1,
        "connector": "beam-rp2040",
        "kind": "beam",
    }
    return ended


def _until(condition: Any) -> None:
    deadline = time.monotonic() + 5
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.01)


@pytest.fixture
def ports() -> list[Port]:
    return []


@pytest.fixture
def serial(ports: list[Port]) -> types.SimpleNamespace:
    """pyserial as the connector uses it, every port it opens kept in ``ports``. As
    pyserial's, an exclusive open fails while another exclusive one holds the port."""

    def open_port(
        device: str, timeout: float | None = None, exclusive: bool | None = None
    ) -> Port:
        held = [p for p in ports if p.device == device and not p.closed]
        if exclusive and any(p.exclusive for p in held):
            raise SerialError(f"Could not exclusively lock port {device}")
        ports.append(Port(device, timeout, exclusive))
        return ports[-1]

    return types.SimpleNamespace(Serial=open_port, SerialException=SerialError)


def test_a_break_on_the_board_reaches_the_chronometer_on_its_clock(
    monkeypatch, ports, serial
):
    monkeypatch.setattr(c, "now_ms", lambda: 1_000_000.0)
    chronometer = Chronometer()
    connector = c.Connector(chronometer, serial, "/dev/cu.usbmodem101", 1000)
    ended = _run(connector, chronometer)
    chronometer.tell({"cmd": "start", "settings": {}})
    assert chronometer.next() == {
        "type": "status",
        "state": "connecting",
        "detail": "/dev/cu.usbmodem101",
    }
    assert chronometer.next()["state"] == "connected"
    [port] = ports
    assert port.written[:4] == ["", "HOLDOFF 1000", "HELLO", "PING 1"]
    port.say("BREAK 1 2500000")  # half a second after the board answered PING 1
    assert chronometer.next() == {
        "type": "beam",
        "seq": 1,
        "time_ms": 1_000_500,
        "device_time": "2500000",
    }
    chronometer.tell({"cmd": "ping", "id": 7})
    assert chronometer.next() == {"type": "pong", "id": 7}
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])
    assert port.closed


def test_a_board_lost_is_said_and_opened_again_with_its_clock_anew(
    monkeypatch, ports, serial
):
    monkeypatch.setattr(c, "REOPEN_AFTER_S", 0.01)
    monkeypatch.setattr(c, "now_ms", lambda: 1_000_000.0)
    chronometer = Chronometer()
    ended = _run(c.Connector(chronometer, serial, "COM7", 1000), chronometer)
    chronometer.tell({"cmd": "start", "settings": {}})
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    monkeypatch.setattr(Port, "answers_at", 1_000)  # the board starts again
    ports[0].said.put(SerialError("device disconnected"))
    assert chronometer.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": "device disconnected",
    }
    assert ports[0].closed
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    assert ports[1].written[3] == "PING 2"  # a number once used is not used again
    ports[1].say("BREAK 1 501000")  # the old board's round trips count no more
    assert chronometer.next()["time_ms"] == 1_000_500
    chronometer.tell(None)  # the chronometer gone: its standard input ends
    _until(lambda: ended == [0])
    assert ports[1].closed


def test_a_board_that_stops_answering_is_said_disconnected_until_it_answers(
    monkeypatch, ports, serial
):
    clock = [1_000_000.0]
    monkeypatch.setattr(c, "now_ms", lambda: clock[0])
    monkeypatch.setattr(c, "PING_EVERY_S", 0.02)
    chronometer = Chronometer()
    ended = _run(c.Connector(chronometer, serial, "COM7", 1000), chronometer)
    chronometer.tell({"cmd": "start", "settings": {}})
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    ports[0].answering = False
    sent = len(ports[0].written)
    _until(lambda: len(ports[0].written) > sent)  # a PING the board left unanswered
    clock[0] += c.SILENT_MS + 1
    assert chronometer.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": c.SILENT,
    }
    ports[0].answering = True
    assert chronometer.next() == {
        "type": "status",
        "state": "connected",
        "detail": HELLO[6:],
    }
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])


def test_a_second_program_on_the_board_is_refused_not_given_half_its_lines(serial):
    """Two chronometers, one per event, both on the first Raspberry Pi port."""
    first, second = Chronometer(), Chronometer()
    ended = _run(c.Connector(first, serial, "COM7", 1000), first)
    first.tell({"cmd": "start", "settings": {}})
    assert [first.next()["state"] for _ in range(2)] == ["connecting", "connected"]
    also_ended = _run(c.Connector(second, serial, "COM7", 1000), second)
    second.tell({"cmd": "start", "settings": {}})
    assert second.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": "Could not exclusively lock port COM7",
    }
    first.tell(None)
    second.tell(None)
    _until(lambda: ended == also_ended == [0])


def test_a_board_missing_is_said_once_not_at_every_retry(monkeypatch):
    monkeypatch.setattr(c, "REOPEN_AFTER_S", 0.0)
    tries: list[str] = []

    def missing(device: str, timeout: float | None = None, **_: object) -> Port:
        tries.append(device)
        raise SerialError(f"could not open port {device}")

    serial = types.SimpleNamespace(Serial=missing, SerialException=SerialError)
    chronometer = Chronometer()
    ended = _run(c.Connector(chronometer, serial, "COM7", 1000), chronometer)
    chronometer.tell({"cmd": "start", "settings": {}})
    _until(lambda: len(tries) >= 3)
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])
    said = list(chronometer.events.queue)
    assert said == [
        {
            "type": "status",
            "state": "disconnected",
            "detail": "could not open port COM7",
        }
    ]
