"""The boards picked, read at once, found and blinked (spec 003; app/connectors/boards/
many.py and scan.py): the fake board of test_beam_board.py on USB beside the fake one
of test_beam_ble.py on the radio."""

from __future__ import annotations

import asyncio
import io
import json
import subprocess
import sys
import threading
import types
from typing import IO, Any, cast

import pytest

from app import sources_config as sc
from app.connectors import runtime
from app.connectors.boards import ble, rp2040
from app.connectors.boards import many as m
from app.connectors.boards import protocol as p
from app.connectors.boards import scan as s
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


def test_at_stop_every_board_s_waiting_breaks_go_before_any_link_is_let_go(
    serial, bleak
):
    said: list[str] = []

    class Slow:
        """A link that takes its time to let go, as Bluetooth's does."""

        def __init__(self, name: str) -> None:
            self.name = name

        def close(self) -> None:
            said.append(f"closed {self.name}")

    connector = m.Many(cast(IO[str], Chronometer()), serial, bleak)
    connector.configure({"boards": [USB, dict(USB, port="COM8", name="other")]})
    for key, link in connector.links.items():
        link.link = Slow(key)
        link.bridge.release = lambda _now, key=key: [{"type": "beam", "seq": 1}]  # type: ignore[method-assign]
        link.send = lambda event, key=key: said.append(f"break of {key}")  # type: ignore[method-assign]
    connector.close()
    assert said == ["break of COM7", "break of COM8", "closed COM7", "closed COM8"]


def test_a_flash_due_for_a_board_let_go_since_is_not_written(serial, bleak):
    connector = m.Many(cast(IO[str], Chronometer()), serial, bleak)
    connector.flashes = [(0.0, "COM7", 1)]  # its board let go meanwhile, a twin say
    assert connector.tick(1.0)
    assert connector.flashes == []


def test_no_board_picked_or_one_of_no_kind_known_is_said(serial, bleak):
    chronometer = Chronometer()
    connector = m.Many(cast(IO[str], chronometer), serial, bleak)
    nano = {"link": "usb", "port": "COM9", "kind": "beam-nano"}
    by_name = {"link": "ble", "name": "beam-7c1c"}  # typed by hand: no address
    connector.configure({"boards": [nano, "COM3", by_name]})
    assert chronometer.next()["message"] == (
        "COM9: a USB board of no kind known ('beam-nano'): find the boards again "
        "and pick it"
    )
    assert chronometer.next()["message"] == (
        "a board picked with no address or port ('COM3'): find the boards again and "
        "pick it"
    )
    assert chronometer.next()["message"].startswith(
        "a board picked with no address or port ({'link': 'ble', 'name': 'beam-7c1c'})"
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


def test_the_chronometer_runs_the_boards_their_search_and_blink(monkeypatch):
    ran: list[Any] = []
    monkeypatch.setattr(m, "run", ran.append)
    monkeypatch.setattr(s, "run", lambda: ran.append("search"))
    for name in ("beam-boards", "beam-blink", "beam-scan"):
        runtime.run(name)
    assert ran == [m.Many, m.Blink, "search"]


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


# -- the search ---------------------------------------------------------------------


class Heard(Advert):
    def __init__(self, name: str | None, uuids: list[str], rssi: int) -> None:
        super().__init__(name, uuids)
        self.rssi = rssi


def _radio(seen: dict[str, tuple[Device, Heard]] | Exception) -> Any:
    async def discover(timeout: float, return_adv: bool) -> dict[str, tuple]:
        assert (timeout, return_adv) == (ble.SCAN_S, True)
        if isinstance(seen, Exception):
            raise seen
        return seen

    return types.SimpleNamespace(BleakScanner=types.SimpleNamespace(discover=discover))


def _port(device: str, vid: int | None, pid: int | None) -> types.SimpleNamespace:
    return types.SimpleNamespace(device=device, vid=vid, pid=pid)


def test_the_boards_on_usb_are_found_by_their_ports_ids():
    found = s.on_usb(
        [
            _port("COM9", 0x303A, 0x1001),
            _port("COM3", 0x2E8A, 0x0005),
            _port("COM4", 0x2E8A, 0x000C),  # a Raspberry Pi Debug Probe
            _port("COM1", None, None),
        ]
    )
    assert found == [
        {"link": "usb", "name": "beam-rp2040", "port": "COM3", "kind": "beam-rp2040"},
        {
            "link": "usb",
            "name": "beam-esp32c3",
            "port": "COM9",
            "kind": "beam-esp32c3",
        },
    ]


def test_the_boards_on_bluetooth_are_found_the_nearest_first():
    seen = {
        "AA": (Device("beam-7c1c", "AA"), Heard("beam-7c1c", [], -80)),
        "BB": (Device(None, "BB"), Heard(None, [ble.SERVICE], -50)),  # a BT05's own
        "CC": (Device("Headphones", "CC"), Heard("Headphones", [], -40)),
    }
    assert asyncio.run(s.on_radio(_radio(seen))) == [
        {"link": "ble", "name": "BB", "device": "BB", "rssi": -50},
        {"link": "ble", "name": "beam-7c1c", "device": "AA", "rssi": -80},
    ]


def test_a_search_says_the_boards_found_usb_first():
    out = io.StringIO()
    usb = types.SimpleNamespace(comports=lambda: [_port("COM3", 0x2E8A, 0x0005)])
    seen = {"AA": (Device("beam-7c1c", "AA"), Heard("beam-7c1c", [], -61))}
    assert s.scan(out, usb, _radio(seen)) == 0
    lines = [json.loads(line) for line in out.getvalue().splitlines()]
    assert (lines[0]["type"], lines[0]["connector"]) == ("hello", "beam-scan")
    boards, errors = s.found_in(out.getvalue().encode())
    assert [one["link"] for one in boards] == ["usb", "ble"] and errors == []


def test_a_search_says_what_it_could_not_look_on_and_finds_the_rest():
    def broken() -> list[Any]:
        raise OSError("no ports today")

    out = io.StringIO()
    off = OSError("Bluetooth device is turned off")
    assert s.scan(out, types.SimpleNamespace(comports=broken), _radio(off)) == 0
    boards, errors = s.found_in(out.getvalue().encode())
    assert boards == []
    assert errors == [
        "USB: no ports today",
        "Bluetooth: Bluetooth device is turned off",
    ]


def test_a_search_s_output_is_read_whatever_else_it_holds():
    output = b"\n".join(
        [
            b"not json",
            b"[1, 2]",
            b'{"type": "found", "boards": "none"}',
            b'{"type": "found", "boards": [{"link": "ble"}, "junk"]}',
            b'{"type": "status", "state": "connected"}',
        ]
    )
    assert s.found_in(output) == ([{"link": "ble"}], [])


def test_the_list_has_the_boards_found_then_those_picked_and_not_found():
    usb = {"link": "usb", "name": "beam-rp2040", "port": "COM3", "kind": "beam-rp2040"}
    near = {"link": "ble", "name": "beam-7c1c", "device": "AA", "rssi": -61}
    gone = {"link": "ble", "name": "beam-b6b0", "device": "BB"}
    assert s.pick_of(near) == {"link": "ble", "name": "beam-7c1c", "device": "AA"}
    rows = s.listed([usb, near], [s.pick_of(near), gone])
    assert rows == [(usb, False, True), (near, True, True), (gone, True, False)]
    assert [s.label(board, here) for board, _, here in rows] == [
        "beam-rp2040 (USB, COM3)",
        "beam-7c1c (Bluetooth, -61 dBm)",
        "beam-b6b0 (Bluetooth, not found by the last search)",
    ]
    assert s.label(gone, False, read=True) == "beam-b6b0 (Bluetooth, read now)"
    first = {"link": "usb", "kind": "beam-rp2040"}  # carried over with no port
    assert s.label(first, False) == (
        "beam-rp2040 (USB, the first port of its kind, not found by the last search)"
    )


# -- a board chosen before spec 003 ------------------------------------------------


@pytest.mark.parametrize(
    ("saved", "boards", "hold_off"),
    [
        (
            "beam_connector=beam-esp32c3-ble\nsettings.beam-esp32c3-ble="
            '{"device":"beam-b6b0","hold_off_ms":800}\n',
            [{"link": "ble", "device": "beam-b6b0", "name": "beam-b6b0"}],
            800,
        ),
        (  # no port: the first with the board's USB ids, as before
            "beam_connector=beam-rp2040\n",
            [{"link": "usb", "port": "", "kind": "beam-rp2040", "name": "beam-rp2040"}],
            1000,
        ),
        ("beam_connector=beam-rp2040-ble\n", [], 1000),  # none named: none picked
        (  # picked in Beam boards already: kept
            'beam_connector=beam-esp32c3\nsettings.beam-boards={"boards":[],'
            '"hold_off_ms":5}\n',
            [],
            5,
        ),
    ],
)
def test_a_single_board_device_chosen_before_is_that_board_in_beam_boards(
    tmp_path, saved, boards, hold_off
):
    path = tmp_path / "sources.txt"
    path.write_text(saved)
    cfg = sc.load_sources(str(path))
    assert cfg["beam_connector"] == "beam-boards"
    assert sc.connector_settings(cfg, "beam-boards") == {
        "boards": boards,
        "hold_off_ms": hold_off,
    }
