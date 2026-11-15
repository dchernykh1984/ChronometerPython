"""The beam board as the chronometer reads it itself (app/connectors/boards/): the
board's lines as the chronometer's events, the board's clock moved onto the computer's,
and the loop between the two, with a board on a fake port standing in for the real one.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.connectors.boards import protocol as p
from app.connectors.boards import rp2040
from app.connectors.boards import usb_serial as u

HELLO = f"HELLO beam-rp2040 {rp2040.FIRMWARE} e6614103"
# The port named: a real board on this computer is never looked for.
START = {"cmd": "start", "settings": {"port": "COM7"}}


def _connected() -> p.Bridge:
    bridge = p.Bridge(rp2040.BOARD)
    bridge.from_board(HELLO, 0.0)
    return bridge


def _read(bridge: p.Bridge) -> p.Bridge:
    """Its clock read: one round trip, the board's 2 s at the computer's 1000 s."""
    n = bridge.ping(1_000_000.0).split()[1]
    bridge.from_board(f"PONG {n} 2000000", 1_000_000.0)
    return bridge


def test_a_board_line_is_its_word_and_the_rest():
    assert p.parse("break 12 812345\r") == ("BREAK", ["12", "812345"])
    assert p.parse("  ") == ("", [])


@pytest.mark.parametrize(
    "rest", [["1"], ["1", "2", "3"], ["1", "-2"], ["x", "2"], ["1.5", "2"]]
)
def test_a_break_or_pong_without_two_whole_numbers_carries_none(rest):
    assert p.pair(rest) is None


def test_the_board_clock_maps_onto_the_middle_of_a_round_trip():
    sync = p.ClockSync()
    assert sync.to_host_ms(2_000_000) is None
    sync.add(sent_ms=1_000_000.0, got_ms=1_000_004.0, board_us=2_000_000)
    assert sync.to_host_ms(2_000_000) == 1_000_002
    assert sync.to_host_ms(3_500_000) == 1_001_502


def test_a_round_trip_too_long_to_say_when_the_board_answered_is_left_out():
    sync = p.ClockSync()
    sync.add(0.0, p.LONGEST_TRIP_MS + 0.1, 0)
    assert sync.to_host_ms(0) is None
    sync.add(0.0, p.LONGEST_TRIP_MS, 0)
    assert sync.to_host_ms(0) == round(p.LONGEST_TRIP_MS / 2)


def test_the_offset_is_the_median_of_the_last_nine_round_trips():
    sync = p.ClockSync()
    for offset in [0.0] * p.SAMPLES + [30.0] * 5:
        sync.add(offset, offset, 0)
    assert sync.to_host_ms(0) == 30  # five of the last nine: the oldest have gone
    sync.add(75.0, 75.0, 0)  # a stray one, short of a clock step, moves it no further
    assert sync.to_host_ms(0) == 30


def test_the_computer_clock_set_anew_moves_the_mapping_at_once():
    """NTP at the venue, or the judge setting the clock: a break just after must be
    on the new clock, not on the old one until the old round trips roll off."""
    sync = p.ClockSync()
    for n in range(p.SAMPLES):
        sync.add(float(n), float(n), n * 1000)  # offset 0
    sync.add(5_000.0, 5_000.0, 0)  # the clock set 5 s on
    assert sync.to_host_ms(1_000) == 5_001
    sync.add(5_000.0 + p.STEP_MS, 5_000.0 + p.STEP_MS, 0)  # not a step: kept
    assert sync.offsets == [5_000.0, 5_000.0 + p.STEP_MS]


def test_pings_are_numbered_and_the_long_unanswered_ones_dropped():
    bridge = p.Bridge(rp2040.BOARD)
    lines = [bridge.ping(float(n)) for n in range(1, 4 * p.SAMPLES + 2)]
    assert lines[:2] == ["PING 1", "PING 2"]
    assert sorted(bridge.pings) == list(range(2, 4 * p.SAMPLES + 2))
    assert bridge.pings[2] == 2.0


def test_a_board_that_answers_no_ping_for_six_seconds_is_silent():
    bridge = _connected()
    bridge.ping(0.0)
    assert not bridge.silent(p.SILENT_MS)
    assert bridge.silent(p.SILENT_MS + 1)
    bridge.ping(5_000.0)
    bridge.from_board("PONG 2 10", 5_003.0)  # a later one answered: the board is there
    assert not bridge.silent(10**12)


def test_a_beam_blocked_longer_than_a_rider_takes_is_blocked_until_it_is_back():
    bridge = _connected()
    bridge.from_board("STATUS blocked", 1_000.0)
    bridge.from_board("STATUS blocked", 1_500.0)  # said again when asked
    assert bridge.unseeing(1_000.0 + p.BLOCKED_MS) is None
    assert bridge.unseeing(1_000.0 + p.BLOCKED_MS + 1) == p.BLOCKED
    bridge.from_board("STATUS beam", 4_000.0)
    assert bridge.unseeing(10**12) is None


def test_a_light_that_flickers_on_the_sensor_is_said_as_no_break_can_be_seen():
    """The board arms its IRQ only once the light has held: one that flickers on
    the sensor's edge never does."""
    bridge = _connected()
    bridge.from_board("STATUS unsteady", 1_000.0)
    assert bridge.unseeing(1_000.0 + p.BLOCKED_MS + 1) == p.UNSTEADY
    bridge.from_board("STATUS blocked", 5_000.0)  # held dark: blocked, from now
    assert bridge.unseeing(5_000.0 + p.BLOCKED_MS + 1) == p.BLOCKED


def test_a_board_on_another_firmware_than_the_chronometer_reads_is_said():
    old = "HELLO beam-rp2040 0.1 e6614103"
    assert p.Bridge(rp2040.BOARD).from_board(old, 0.0) == [
        {"type": "status", "state": "connected", "detail": old[6:]},
        {
            "type": "error",
            "message": "the board runs firmware 0.1, the chronometer reads "
            f"{rp2040.FIRMWARE}: flash the board again (firmware/ in the repository)",
        },
    ]
    same = p.Bridge(rp2040.BOARD).from_board(HELLO, 0.0)
    assert len(same) == 1  # nothing to say


@pytest.mark.parametrize(
    ("line", "runs"),
    [
        ("HELLO beam-rp2040", "?"),
        (f"HELLO beam-rp2040 {rp2040.FIRMWARE}", rp2040.FIRMWARE),
    ],
    ids=["no version", "no board id"],
)
def test_a_hello_short_of_words_is_taken_without_falling_over(line, runs):
    bridge = p.Bridge(rp2040.BOARD)
    said = bridge.from_board(line, 0.0)
    assert said[0]["state"] == "connected"
    assert (bridge.board_id, len(said)) == ("", 1 if runs == rp2040.FIRMWARE else 2)
    assert len(_read(bridge).from_board("BREAK 1 1000", 0.0)) == 1  # and it counts


def test_the_connector_expects_the_firmware_beside_it():
    main = Path(__file__).parents[1] / "firmware" / "beam_rp2040" / "main.py"
    main = main.read_text(encoding="utf-8")
    assert f'\nFIRMWARE = "{rp2040.FIRMWARE}"\n' in main


def test_a_break_before_the_hello_waits_for_the_boards_clock_not_dropped():
    """The milliseconds between the port opening and the board's HELLO: a rider
    then is a rider all the same. The break waits till the board is known and its
    clock read, then is timed by it: right even for a line the system kept from
    before the port was opened."""
    bridge = p.Bridge(rp2040.BOARD)
    assert bridge.from_board("BREAK 1 2500000", 5.0) == []
    assert bridge.from_board("HELLO another-board 1", 5.0) == []
    assert bridge.from_board(HELLO, 6.0) == [
        {"type": "status", "state": "connected", "detail": HELLO[6:]}
    ]
    n = bridge.ping(1_000_000.0).split()[1]
    assert bridge.from_board(f"PONG {n} 2000000", 1_000_000.0) == [
        {"type": "beam", "seq": 1, "time_ms": 1_000_500, "device_time": "2500000"}
    ]


def test_a_board_that_never_says_hello_has_no_break_counted():
    bridge = p.Bridge(rp2040.BOARD)
    bridge.from_board("BREAK 1 1000", 0.0)
    assert bridge.release(10**12) == []


def test_a_break_given_up_on_for_the_boards_clock_takes_its_lines_time_said_so():
    """Every round trip too long to read the clock by: the break is stamped all the
    same, by when its line came, and the judge told."""
    bridge = _connected()
    came = 1_761_725_401_500.4
    assert bridge.from_board("BREAK 12 812345", came) == []
    assert bridge.release(came + p.HELD_MS) == []
    assert bridge.release(came + p.HELD_MS + 1) == [
        {
            "type": "beam",
            "seq": 12,
            "time_ms": 1_761_725_401_500,
            "device_time": "812345",
        },
        {
            "type": "error",
            "message": "the board's clock could not be read: 1 break(s) timed by "
            "when their lines came",
        },
    ]


def test_breaks_the_board_counted_that_never_came_are_said():
    bridge = _read(_connected())
    assert len(bridge.from_board("BREAK 4 1000", 0.0)) == 1  # the first seen: no gap
    assert len(bridge.from_board("BREAK 5 2000", 0.0)) == 1
    beam, error = bridge.from_board("BREAK 8 3000", 0.0)
    assert (beam["seq"], error["type"]) == (8, "error")
    assert error["message"].startswith("the board's break(s) 6 to 7 did not arrive")
    beam, error = bridge.from_board("BREAK 10 4000", 0.0)
    assert error["message"].startswith("the board's break(s) 9 did not arrive")
    assert len(bridge.from_board("BREAK 1 5000", 0.0)) == 1  # the board started again


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


def test_the_connector_ends_once_the_program_that_started_it_is_gone():
    parents = iter([41, 41, 1])  # its parent killed: the system takes it over
    ended: list[int] = []
    u.watch_parent(41, getppid=lambda: next(parents), end=ended.append, every_s=0)
    assert ended == [1]


@pytest.mark.parametrize("given", [-5, 0, 60001, 1.5, "1000", True, None])
def test_a_hold_off_setting_out_of_range_is_none(given):
    assert u.hold_off(given) is None


def test_a_hold_off_setting_in_range_is_taken():
    assert (u.hold_off(1), u.hold_off(60000), u.hold_off(1000.0)) == (1, 60_000, 1000)


def _port(device: str, vid: int | None, pid: int | None) -> types.SimpleNamespace:
    return types.SimpleNamespace(device=device, vid=vid, pid=pid)


def test_the_port_named_is_used_else_the_first_micropython_rp2040_one(monkeypatch):
    """Not just any Raspberry Pi device: its Debug Probe has a serial port too."""
    assert u.board_port("COM7", rp2040.BOARD) == "COM7"
    pi, micropython = rp2040.BOARD.vendor, rp2040.BOARD.product
    ports = [
        _port("/dev/cu.usbmodem201", pi, micropython),
        _port("/dev/cu.Bluetooth-Incoming-Port", None, None),
        _port("/dev/cu.usbmodem0001", pi, 0x000C),  # a Raspberry Pi Debug Probe
        _port("/dev/cu.usbmodem101", pi, micropython),
        _port("/dev/cu.usbserial-10", 0x0403, 0x6001),
    ]
    tools = types.ModuleType("serial.tools")
    tools.list_ports = types.SimpleNamespace(comports=lambda: ports)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "serial", types.ModuleType("serial"))
    monkeypatch.setitem(sys.modules, "serial.tools", tools)
    assert u.board_port("", rp2040.BOARD) == "/dev/cu.usbmodem101"
    del ports[3], ports[0]
    assert u.board_port("", rp2040.BOARD) is None


# -- the loop, with a board on a fake port ------------------------------------


class SerialError(Exception):
    """pyserial's SerialException, for the fake port."""


class Port:
    """A beam board running main.py on a serial port: it answers HELLO and PING as
    the firmware does, at board time ``answers_at``, and says what a test makes it
    say."""

    answers_at = 2_000_000
    answering = True  # False: main.py has stopped, the port is still open
    light = "beam"  # what it answers STATUS
    rider = False  # True: a rider breaks the beam just as the port opens

    reading = True  # False: the board reads its USB no more, a write never ends

    def __init__(
        self,
        device: str,
        timeout: float | None,
        exclusive: bool | None,
        write_timeout: float | None = None,
    ) -> None:
        self.device, self.closed, self.exclusive = device, False, exclusive
        self.write_timeout, self.stuck_writes = write_timeout, 0
        self.written: list[str] = []
        self.said: queue.Queue[bytes | Exception | None] = queue.Queue()

    def write(self, data: bytes) -> int:
        if not self.reading:
            self.stuck_writes += 1
            if self.write_timeout is None:
                threading.Event().wait()  # as pyserial's write with no timeout
            raise SerialError("Write timeout")
        for line in data.decode().split("\n")[:-1]:
            self.written.append(line)
            if line == "HELLO":
                if self.rider:
                    self.say("BREAK 1 1500000")  # said before it read the HELLO
                self.say(HELLO)
            elif line == "STATUS":
                self.say(f"STATUS {self.light}")
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


def _run(connector: u.Connector, chronometer: Chronometer) -> list[int]:
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
        device: str,
        timeout: float | None = None,
        exclusive: bool | None = None,
        write_timeout: float | None = None,
    ) -> Port:
        held = [p for p in ports if p.device == device and not p.closed]
        if exclusive and any(p.exclusive for p in held):
            raise SerialError(f"Could not exclusively lock port {device}")
        ports.append(Port(device, timeout, exclusive, write_timeout))
        return ports[-1]

    return types.SimpleNamespace(Serial=open_port, SerialException=SerialError)


def test_a_break_on_the_board_reaches_the_chronometer_on_its_clock(
    monkeypatch, ports, serial
):
    monkeypatch.setattr(u, "now_ms", lambda: 1_000_000.0)
    chronometer = Chronometer()
    connector = u.Connector(chronometer, serial, rp2040.BOARD)
    ended = _run(connector, chronometer)
    chronometer.tell({"cmd": "start", "settings": {"port": "/dev/cu.usbmodem101"}})
    assert chronometer.next() == {
        "type": "status",
        "state": "connecting",
        "detail": "/dev/cu.usbmodem101",
    }
    assert chronometer.next()["state"] == "connected"
    [port] = ports
    assert port.written[:5] == ["", "HOLDOFF 1000", "HELLO", "STATUS", "PING 1"]
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
    monkeypatch.setattr(u, "REOPEN_AFTER_S", 0.01)
    monkeypatch.setattr(u, "now_ms", lambda: 1_000_000.0)
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell(START)
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
    assert ports[1].written[4] == "PING 2"  # a number once used is not used again
    ports[1].say("BREAK 1 501000")  # the old board's round trips count no more
    assert chronometer.next()["time_ms"] == 1_000_500
    chronometer.tell(None)  # the chronometer gone: its standard input ends
    _until(lambda: ended == [0])
    assert ports[1].closed


def test_a_board_that_reads_no_more_does_not_hang_the_connector(
    monkeypatch, ports, serial
):
    """Its USB never read: a write that waited for it would never end, no pong
    would reach the chronometer, and it would be killed and started again on and on."""
    monkeypatch.setattr(p, "PING_EVERY_S", 0.02)
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell(START)
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    ports[0].reading = False
    _until(lambda: ports[0].stuck_writes > 0)
    chronometer.tell({"cmd": "ping", "id": 5})
    assert chronometer.next() == {"type": "pong", "id": 5}
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_a_board_that_stops_answering_is_said_disconnected_until_it_answers(
    monkeypatch, ports, serial
):
    clock = [1_000_000.0]
    monkeypatch.setattr(u, "now_ms", lambda: clock[0])
    monkeypatch.setattr(p, "PING_EVERY_S", 0.02)
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell(START)
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    ports[0].answering = False
    sent = len(ports[0].written)
    _until(lambda: len(ports[0].written) > sent)  # a PING the board left unanswered
    clock[0] += p.SILENT_MS + 1
    assert chronometer.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": p.SILENT,
    }
    ports[0].answering = True
    assert chronometer.next() == {
        "type": "status",
        "state": "connected",
        "detail": HELLO[6:],
    }
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])


def test_a_rider_as_the_port_opens_is_stamped_not_dropped(monkeypatch, ports, serial):
    monkeypatch.setattr(u, "now_ms", lambda: 1_000_000.0)
    monkeypatch.setattr(Port, "rider", True)
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell(START)
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    assert chronometer.next() == {  # half a second before the board answered PING 1
        "type": "beam",
        "seq": 1,
        "time_ms": 999_500,
        "device_time": "1500000",
    }
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_a_break_still_waiting_for_the_clock_at_stop_is_stamped(
    monkeypatch, ports, serial
):
    """The chronometer counts all a connector says until it has ended."""
    monkeypatch.setattr(Port, "rider", True)
    monkeypatch.setattr(Port, "answering", False)  # no round trip: no clock read
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell(START)
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])
    beam, error = list(chronometer.events.queue)
    assert (beam["type"], beam["seq"], error["type"]) == ("beam", 1, "error")


def test_a_break_lost_while_the_link_was_down_is_said(monkeypatch, ports, serial):
    """A USB link dropped and found again, the board's power never cut: it went on
    counting, and a break it saw meanwhile never came."""
    monkeypatch.setattr(u, "REOPEN_AFTER_S", 0.01)
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell(START)
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    ports[0].say("BREAK 1 2500000")
    assert chronometer.next()["type"] == "beam"
    ports[0].said.put(SerialError("device disconnected"))
    assert [chronometer.next()["state"] for _ in range(3)] == [
        "disconnected",
        "connecting",
        "connected",
    ]
    ports[1].say("BREAK 3 2600000")
    assert chronometer.next()["seq"] == 3
    assert chronometer.next() == {
        "type": "error",
        "message": "the board's break(s) 2 did not arrive: its link was down as "
        "they came; check that finish by other means",
    }
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_a_port_lost_before_is_not_the_one_open_now(ports, serial):
    """The lost port of an earlier link says so late: the link open now stays."""
    connector = u.Connector(Chronometer(), serial, rp2040.BOARD)
    connector.link = Port("COM7", None, True)
    assert connector.handle("lost", (Port("COM7", None, True), "closed long ago"))
    assert connector.link is not None and not connector.link.closed


def test_a_line_cut_short_as_the_port_ends_is_no_line(ports, serial):
    """The port's end can cut a line: BREAK 5 12345678 would be BREAK 5 12."""
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell(START)
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    ports[0].said.put(b"BREAK 5 12")
    ports[0].said.put(None)  # the port ends
    assert chronometer.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": "the board's port closed",
    }
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_a_reading_ended_by_any_error_is_said_and_the_port_opened_again(
    monkeypatch, ports, serial
):
    """Not only pyserial's errors: one from deeper down must not leave the link
    half dead, read by no one and never opened again."""
    monkeypatch.setattr(u, "REOPEN_AFTER_S", 0.01)
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell(START)
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    ports[0].said.put(RuntimeError("the driver fell over"))
    assert chronometer.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": "the driver fell over",
    }
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_a_beam_blocked_from_the_start_is_said_and_so_is_its_return(
    monkeypatch, ports, serial
):
    """The laser not yet aimed, or knocked off the sensor: no break can be seen."""
    clock = [1_000_000.0]
    monkeypatch.setattr(u, "now_ms", lambda: clock[0])
    monkeypatch.setattr(Port, "light", "blocked")
    chronometer = Chronometer()
    connector = u.Connector(chronometer, serial, rp2040.BOARD)
    ended = _run(connector, chronometer)
    chronometer.tell(START)
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    _until(lambda: connector.bridge.dark is not None)  # its STATUS taken
    clock[0] += p.BLOCKED_MS + 1
    assert chronometer.next() == {
        "type": "status",
        "state": "connected",
        "detail": f"{HELLO[6:]}: {p.BLOCKED}",
    }
    ports[0].say("STATUS beam")  # aimed again
    assert chronometer.next() == {
        "type": "status",
        "state": "connected",
        "detail": HELLO[6:],
    }
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])


def test_a_second_program_on_the_board_is_refused_not_given_half_its_lines(serial):
    """Two chronometers, one per event, both on the first MicroPython port."""
    first, second = Chronometer(), Chronometer()
    ended = _run(u.Connector(first, serial, rp2040.BOARD), first)
    first.tell(START)
    assert [first.next()["state"] for _ in range(2)] == ["connecting", "connected"]
    also_ended = _run(u.Connector(second, serial, rp2040.BOARD), second)
    second.tell(START)
    assert second.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": "Could not exclusively lock port COM7",
    }
    first.tell(None)
    second.tell(None)
    _until(lambda: ended == also_ended == [0])


def test_a_command_not_understood_is_logged_once_and_ignored(ports, serial, capfd):
    """As the protocol has it; the chronometer shows its error output in its log."""
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.commands.put(b"[1, 2]\n")
    chronometer.commands.put(b"not json\n")
    for _ in range(2):
        chronometer.tell({"cmd": "calibrate", "id": 3})
    chronometer.tell({"cmd": ["odd"]})
    chronometer.tell({"cmd": "ping", "id": 9})
    assert chronometer.next() == {"type": "pong", "id": 9}  # and it goes on
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])
    assert capfd.readouterr().err.splitlines() == [
        "not a JSON object, ignored: b'[1, 2]\\n'",
        "not a JSON object, ignored: b'not json\\n'",
        "unknown cmd 'calibrate': ignored",
        "unknown cmd ['odd']: ignored",
    ]


def test_a_board_missing_is_said_once_not_at_every_retry(monkeypatch):
    monkeypatch.setattr(u, "REOPEN_AFTER_S", 0.0)
    tries: list[str] = []

    def missing(device: str, timeout: float | None = None, **_: object) -> Port:
        tries.append(device)
        raise SerialError(f"could not open port {device}")

    serial = types.SimpleNamespace(Serial=missing, SerialException=SerialError)
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell(START)
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


def test_no_board_on_usb_is_said_once_by_its_name(monkeypatch, serial):
    monkeypatch.setattr(u, "REOPEN_AFTER_S", 0.0)
    monkeypatch.setattr(u, "board_port", lambda chosen, spec: None)
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell({"cmd": "start", "settings": {}})
    _until(lambda: not chronometer.events.empty())
    time.sleep(0.5)  # retries meanwhile, none said again
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])
    assert list(chronometer.events.queue) == [
        {
            "type": "status",
            "state": "disconnected",
            "detail": "no Beam board RP2040 (USB) found on USB",
        }
    ]


def test_a_hold_off_setting_out_of_range_is_said_and_the_default_kept(ports, serial):
    chronometer = Chronometer()
    ended = _run(u.Connector(chronometer, serial, rp2040.BOARD), chronometer)
    chronometer.tell({"cmd": "start", "settings": {"port": "COM7", "hold_off_ms": 0}})
    assert chronometer.next() == {
        "type": "error",
        "message": "hold_off_ms 0 is not 1 to 60000: 1000 it is",
    }
    assert chronometer.next()["state"] == "connecting"
    assert ports[0].written[1] == "HOLDOFF 1000"
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_a_break_the_clock_never_came_for_is_stamped_by_its_line_and_said(
    monkeypatch, ports, serial
):
    clock = [1_000_000.0]
    monkeypatch.setattr(u, "now_ms", lambda: clock[0])
    monkeypatch.setattr(Port, "rider", True)
    monkeypatch.setattr(Port, "answering", False)  # every round trip lost
    chronometer = Chronometer()
    connector = u.Connector(chronometer, serial, rp2040.BOARD)
    ended = _run(connector, chronometer)
    chronometer.tell(START)
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    _until(lambda: connector.bridge.held)  # its break, waiting for the clock
    clock[0] += p.HELD_MS + 1
    beam = chronometer.next()
    assert (beam["type"], beam["time_ms"]) == ("beam", 1_000_000)  # when it came
    assert chronometer.next()["message"].startswith("the board's clock could not")
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_the_chronometer_runs_the_board_as_a_process_of_its_own():
    """As the chronometer starts it: itself, with --connector, pyserial and all."""
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main", "--connector", "beam-rp2040"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert process.stdin and process.stdout
    hello = json.loads(process.stdout.readline())
    assert (hello["connector"], hello["kind"]) == ("beam-rp2040", "beam")
    start = {"cmd": "start", "settings": {"port": "/dev/no-such-board"}}
    process.stdin.write((json.dumps(start) + "\n").encode())
    process.stdin.flush()
    status = json.loads(process.stdout.readline())
    assert status["state"] == "disconnected"
    assert "no-such-board" in status["detail"]
    process.stdin.write(b'{"cmd":"stop"}\n')
    process.stdin.close()
    assert process.wait(timeout=10) == 0
