"""The boards picked, read at once and blinked (spec 003; app/connectors/boards/
many.py): the fake board of test_beam_board.py on USB beside the fake one of
test_beam_ble.py on the radio."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from typing import IO, Any, cast

from app.connectors import runtime
from app.connectors.boards import ble, rp2040
from app.connectors.boards import many as m
from app.connectors.boards import protocol as p
from tests import test_beam_ble as tb
from tests.test_beam_ble import ID, Advert, Device, Radio, _board_in_range
from tests.test_beam_ble import bleak as bleak
from tests.test_beam_board import Chronometer, _until
from tests.test_beam_board import ports as ports
from tests.test_beam_board import serial as serial

USB = {"link": "usb", "port": "COM7", "kind": "beam-rp2040", "name": "beam-rp2040"}
RADIO = {"link": "ble", "device": "AA:BB", "name": "beam-4103"}


def _start(
    kind: type[m.Many], chronometer: Chronometer, serial: Any, bleak: Any, picks: list
) -> tuple[m.Many, list[int]]:
    connector = kind(cast(IO[str], chronometer), serial, bleak)
    ended: list[int] = []
    threading.Thread(
        target=lambda: ended.append(connector.run(chronometer)), daemon=True
    ).start()
    assert chronometer.next()["connector"] == kind.name
    chronometer.tell({"cmd": "start", "settings": {"boards": picks}})
    return connector, ended


def _until_said(chronometer: Chronometer, wanted: Any) -> list[dict[str, Any]]:
    """What the connector says, up to and with what ``wanted`` looks for."""
    said: list[dict[str, Any]] = []
    while not said or not wanted(said[-1]):
        said.append(chronometer.next())
    return said


def _connected(named: str) -> Any:
    return lambda one: (
        one.get("state") == "connected" and one["detail"].startswith(f"{named}: beam-")
    )


def test_every_break_of_every_board_picked_is_a_cutoff_of_its_own(ports, serial, bleak):
    _board_in_range("beam-4103", "AA:BB")
    Radio.in_range.append((Device("beam-9999", "CC:DD"), Advert("beam-9999")))
    chronometer = Chronometer()
    connector, ended = _start(m.Many, chronometer, serial, bleak, [USB, RADIO])
    said = _until_said(chronometer, _connected("beam-rp2040"))
    said += _until_said(chronometer, _connected("beam-4103"))
    details = [one["detail"] for one in said if one["type"] == "status"]
    assert f"beam-rp2040: beam-rp2040 {rp2040.FIRMWARE} e6614103" in details
    assert f"beam-4103: beam-esp32c3 {rp2040.FIRMWARE} {ID}" in details
    [client] = Radio.clients  # the board picked, never the other in range
    assert client.device.address == "AA:BB"
    _until(lambda: all(one.bridge.sync.read for one in connector.links.values()))
    [port] = ports
    port.say("BREAK 1 2500000")
    client.say("BREAK 1 3500000")  # the same count, another board: a cutoff too
    beams = [chronometer.next(), chronometer.next()]
    assert sorted((one["seq"], one["time_ms"]) for one in beams) == [
        (1, 1_000_500),  # each on its own board's clock
        (1, 1_001_500),
    ]
    chronometer.tell({"cmd": "ping", "id": 3})
    assert _until_said(chronometer, lambda one: one["type"] == "pong")[-1]["id"] == 3
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])
    assert port.closed and not client.connected


def test_a_board_lost_does_not_stop_the_others_and_is_said_with_its_name(
    ports, serial, bleak
):
    _board_in_range("beam-4103", "AA:BB")
    chronometer = Chronometer()
    connector, ended = _start(m.Many, chronometer, serial, bleak, [USB, RADIO])
    _until_said(chronometer, _connected("beam-4103"))
    _until(lambda: all(one.bridge.sync.read for one in connector.links.values()))
    Radio.clients[0].drop()
    lost = _until_said(chronometer, lambda one: one.get("state") == "disconnected")
    assert lost[-1]["detail"] == f"beam-4103: {ble.LOST}"
    ports[0].say("BREAK 1 2500000")
    beam = _until_said(chronometer, lambda one: one["type"] == "beam")[-1]
    assert beam["time_ms"] == 1_000_500
    _until_said(chronometer, _connected("beam-4103"))  # back, and said so
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_one_board_picked_on_its_usb_and_its_bluetooth_is_read_once(
    ports, serial, bleak, monkeypatch
):
    """The list shows a board on a cable twice, by its port and by its name on the
    radio: both picked, its breaks would each be two cutoffs."""
    monkeypatch.setattr(tb, "ID", "e6614103")  # the board on the radio is the USB one
    _board_in_range("beam-4103", "AA:BB")
    chronometer = Chronometer()
    connector, ended = _start(m.Many, chronometer, serial, bleak, [USB, RADIO])
    said = _until_said(chronometer, lambda one: one["type"] == "error")
    twins = {"beam-rp2040", "beam-4103"}
    dropped = said[-1]["message"].split(":")[0]
    (kept,) = twins - {dropped}
    assert said[-1]["message"] == (
        f"{dropped}: the same board as {kept}, read on that link only"
    )
    assert len(connector.links) == 1
    if dropped == "beam-4103":
        _until(lambda: not Radio.clients[0].connected)
    else:
        assert ports[0].closed
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_blink_flashes_a_board_five_times_or_says_why_not(
    ports, serial, bleak, monkeypatch
):
    monkeypatch.setattr(m, "FLASH_EVERY_S", 0.01)
    away = {"link": "ble", "device": "EE:FF", "name": "beam-0000"}
    chronometer = Chronometer()
    _, ended = _start(m.Many, chronometer, serial, bleak, [USB, away])
    _until_said(chronometer, _connected("beam-rp2040"))
    chronometer.tell({"cmd": "blink", "board": "COM7"})
    flashes = [f"FLASH {n}" for n in range(1, 6)]
    _until(lambda: [one for one in ports[0].written if "FLASH" in one] == flashes)
    chronometer.tell({"cmd": "blink", "board": "EE:FF"})
    said = _until_said(chronometer, lambda one: one["type"] == "error")
    assert said[-1]["message"] == "beam-0000: not connected, so not blinked"
    chronometer.tell({"cmd": "blink", "board": "11:22"})
    said = _until_said(chronometer, lambda one: one["type"] == "error")
    assert said[-1]["message"] == "11:22: not a board read here"
    chronometer.tell({"cmd": "dance"})  # the protocol: ignored
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_no_board_picked_or_one_of_no_kind_known_is_said(serial, bleak):
    chronometer = Chronometer()
    connector = m.Many(cast(IO[str], chronometer), serial, bleak)
    nano = {"link": "usb", "port": "COM9", "kind": "beam-nano"}
    connector.configure({"boards": [nano, "COM3", {"link": "usb"}]})
    assert chronometer.next()["message"] == (
        "COM9: a USB board of no kind known ('beam-nano'): find the boards again "
        "and pick it"
    )
    assert chronometer.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": m.NONE_PICKED,
    }
    connector.configure("not settings")
    assert chronometer.next()["detail"] == m.NONE_PICKED
    connector.configure({"boards": [USB, dict(USB, name="again")]})
    assert list(connector.links) == ["COM7"]  # picked twice: read once
    assert connector.links["COM7"].spec is rp2040.BOARD


def test_blink_alone_reaches_the_board_blinks_it_and_ends(
    ports, serial, bleak, monkeypatch
):
    monkeypatch.setattr(m, "FLASH_EVERY_S", 0.01)
    chronometer = Chronometer()
    _, ended = _start(m.Blink, chronometer, serial, bleak, [USB])
    _until(lambda: ended == [0])
    [port] = ports
    assert [one for one in port.written if "FLASH" in one] == [
        f"FLASH {n}" for n in range(1, 6)
    ]
    assert port.closed


def test_blink_alone_says_a_board_not_reached_and_ends(serial, bleak, monkeypatch):
    monkeypatch.setattr(m, "BLINK_WAIT_S", 0.2)
    away = {"link": "ble", "device": "EE:FF", "name": "beam-0000"}
    chronometer = Chronometer()
    _, ended = _start(m.Blink, chronometer, serial, bleak, [away])
    said = _until_said(chronometer, lambda one: one["type"] == "error")
    assert said[-1]["message"].startswith("beam-0000: not reached within")
    _until(lambda: ended == [0])
    chronometer = Chronometer()
    _, ended = _start(m.Blink, chronometer, serial, bleak, [])
    assert chronometer.next()["detail"] == m.NONE_PICKED  # nothing to blink
    _until(lambda: ended == [0])


def test_a_board_picked_on_bluetooth_is_taken_for_either_kind_s_hello():
    bridge = p.Bridge(m.ANY_RADIO)
    assert bridge.from_board("HELLO beam-nano 0.4 abcd 0", 0.0) == []
    said = bridge.from_board(f"HELLO beam-esp32c3 {rp2040.FIRMWARE} abcd 0", 0.0)
    assert said[0]["detail"] == f"beam-esp32c3 {rp2040.FIRMWARE} abcd"
    assert bridge.radio  # its clock read as the radio's
    assert not p.Bridge(rp2040.BOARD).ours("beam-esp32c3")


def test_the_chronometer_runs_the_boards_and_their_blink(monkeypatch):
    ran: list[Any] = []
    monkeypatch.setattr(m, "run", ran.append)
    for name in ("beam-boards", "beam-blink"):
        runtime.run(name)
    assert ran == [m.Many, m.Blink]


def test_the_boards_run_as_a_process_of_their_own():
    """As the chronometer starts them: itself, with --connector, pyserial and all."""
    process = subprocess.Popen(
        [sys.executable, "-m", "app.main", "--connector", "beam-boards"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert process.stdin and process.stdout
    assert json.loads(process.stdout.readline())["connector"] == "beam-boards"
    pick = dict(USB, port="/dev/no-such-board", name="far")
    start = {"cmd": "start", "settings": {"boards": [pick]}}
    process.stdin.write((json.dumps(start) + "\n").encode())
    process.stdin.flush()
    status = json.loads(process.stdout.readline())
    assert status["state"] == "disconnected"
    assert status["detail"].startswith("far: ") and "no-such-board" in status["detail"]
    process.stdin.write(b'{"cmd":"stop"}\n')
    process.stdin.close()
    assert process.wait(timeout=10) == 0
