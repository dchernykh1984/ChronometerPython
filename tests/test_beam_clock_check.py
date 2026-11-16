"""The clock check run on every beam board flashed (beam/tools/clock_check.py): the
spec's hypotheses against trips made up with a known crystal and known ways, and the
check run end to end on the fake board of the connectors' tests."""

from __future__ import annotations

import sys
import types
from collections.abc import Callable

import pytest

from app.connectors.boards import protocol as p
from app.connectors.boards import rp2040
from beam.tools import clock_check as c
from tests.test_beam_ble import Client, Radio, Scanner, _board_in_range
from tests.test_beam_board import HELLO, Port, SerialError, _port

Ways = Callable[[int], float]
NOW_MS = 1e12  # this computer's clock at the first PING
BOOTED_US = 5_000_000  # the board's at the same moment
BOARD_WAIT_US = 10_000  # between a PING come and its PONG gone
BOARD_ID = HELLO.split()[3]  # the fake board's, as its HELLO says it


def _trips(
    ppm: float,
    there: Ways,
    back: Ways,
    every_ms: float,
    count: int,
    radio: bool = False,
) -> c.Link:
    """A board ``ppm`` fast, PINGed every ``every_ms``: the k-th PING ``there(k)`` ms on
    its way, its PONG ``back(k)``."""
    rate = 1 + ppm * 1e-6
    link = c.Link(radio)
    for k in range(count):
        sent = NOW_MS + every_ms * k
        got_us = round((sent + there(k) - NOW_MS) * rate * 1000) + BOOTED_US
        sent_us = got_us + BOARD_WAIT_US
        got = NOW_MS + (sent_us - BOOTED_US) / 1000 / rate + back(k)
        link.trips.append((sent, got, got_us, sent_us))
    return link


def _cycle(*ms: float) -> Ways:
    return lambda k: ms[k % len(ms)]


CABLE = _trips(20, _cycle(0.5), _cycle(0.5), 2000, 150)  # 5 minutes, a 20 ppm crystal
RADIO_BACK = _cycle(25, 8, 40, 12)


def test_a_board_within_every_hypothesis_says_so():
    radio = _trips(20, _cycle(8, 30, 15, 45), RADIO_BACK, 1000, 300, radio=True)
    said = c.report("beam-rp2040 0.4 e6614103", CABLE, radio)
    assert said[:4] == [
        "board: beam-rp2040 0.4 e6614103",
        "USB: 150 answers, a round trip 1.00 ms (median)",
        "  the mapping off by at most half of it: 0.50 ms (within 1 ms)",
        "  its move from one answer to the next, 95% under: 0.04 ms (within 0.5 ms),"
        " the most 0.04 ms",
    ]
    # A hair under 20: the first answers, before 9 are kept, lag the clock less.
    assert (
        said[4]
        == "  the board's crystal ahead of this clock: 19.91 ppm (within 30 ppm)"
    )
    assert said[5] == "Bluetooth: 300 answers, a round trip 46.50 ms (median)"
    assert "(within 2 ms)" in said[8]
    assert said[-1] == "result: every check within"


def test_a_radio_slower_one_way_than_the_other_is_outside():
    """The shortest way there 13 ms, back 8: the mapping 2.5 ms off the cable's."""
    radio = _trips(20, _cycle(13, 30, 15, 45), RADIO_BACK, 1000, 300, radio=True)
    said = c.report("beam-rp2040 0.4 e6614103", CABLE, radio)
    assert said[8].startswith(
        "  Bluetooth's mapping from the cable's, 90% of the time: 2."
    )
    assert said[8].endswith("(OUTSIDE 2 ms)")
    assert said[9].startswith("    -2.")
    assert said[-1] == "result: 1 OUTSIDE: look at this board before it times a race"


def test_too_few_answers_map_no_clock():
    cable = _trips(20, _cycle(0.5), _cycle(0.5), 2000, 2)
    assert c.report("b", cable, None)[1] == "USB: 2 answers, too few to map the clock"


def test_only_a_pong_for_a_ping_sent_is_a_trip():
    link = c.Link(radio=False)
    assert link.ping(100.0) == "PING 1\n"
    assert link.ping(200.0) == "PING 2\n"
    for line in ("PONG 3 5 6", "PONG 1 5", "HELLO beam-rp2040", "PONG 2 7 8"):
        link.heard(line, 300.0)
    link.heard("PONG 2 9 9", 400.0)  # answered twice: the first is the one
    assert link.trips == [(200.0, 300.0, 7, 8)]


@pytest.fixture
def board(monkeypatch: pytest.MonkeyPatch) -> list[types.SimpleNamespace]:
    """The fake board of the connectors' tests, on USB at COM7 and in Bluetooth range
    as beam- and the last 4 digits of its id; its ports, for a test to change."""
    ports = [_port("COM7", rp2040.BOARD.vendor, rp2040.BOARD.product)]
    tools = types.ModuleType("serial.tools")
    tools.list_ports = types.SimpleNamespace(comports=lambda: ports)  # type: ignore[attr-defined]
    serial = types.ModuleType("serial")
    serial.Serial, serial.SerialException = Port, SerialError  # type: ignore[attr-defined]
    bleak = types.ModuleType("bleak")
    bleak.BleakScanner, bleak.BleakClient = Scanner, Client  # type: ignore[attr-defined]
    for name, module in (("serial", serial), ("serial.tools", tools), ("bleak", bleak)):
        monkeypatch.setitem(sys.modules, name, module)
    for kept in ("in_range", "clients", "kept"):
        monkeypatch.setattr(Radio, kept, [])
    monkeypatch.setattr(Port, "kept", [])
    monkeypatch.setattr(p, "PING_EVERY_S", 0.02)
    monkeypatch.setattr(p, "RADIO_PING_EVERY_S", 0.01)
    _board_in_range("beam-" + BOARD_ID[-4:])
    return ports


def test_the_board_is_checked_over_its_cable_and_its_radio_at_once(board):
    said = c.measure(sys.modules["serial"], sys.modules["bleak"], "", "", 0.01)
    hello = f"beam-rp2040 {rp2040.FIRMWARE} {BOARD_ID}"
    assert said[0] == f"board: {hello}, USB COM7, Bluetooth beam-4103"
    assert said[1].startswith("USB: ") and "answers" in said[1]
    assert any(line.startswith("Bluetooth: ") for line in said)
    assert said[-1].startswith("result: ")
    assert Radio.clients[0].connected is False  # let go of, for the next reader


def test_the_cable_alone_is_checked_when_asked(board, capsys):
    assert c.main(["--ble", "-", "--minutes", "0.005"]) == 0
    said = capsys.readouterr().out
    assert said.startswith("board: beam-rp2040") and "Bluetooth" not in said
    assert not Radio.clients


def test_no_board_on_usb_or_one_held_by_another_program_is_said(board, monkeypatch):
    serial = sys.modules["serial"]
    with pytest.raises(SystemExit, match="no beam board on USB COM9"):
        c.measure(serial, None, "COM9", "-", 0.01)

    def busy(*_args: object, **_kwargs: object) -> None:
        raise OSError("[Errno 16] Resource busy")

    monkeypatch.setattr(serial, "Serial", busy)
    with pytest.raises(SystemExit, match=r"COM7: \[Errno 16\] Resource busy"):
        c.measure(serial, None, "", "-", 0.01)
