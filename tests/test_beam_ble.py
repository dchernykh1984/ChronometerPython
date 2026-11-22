"""The beam boards on Bluetooth as the chronometer reads them (app/connectors/boards/
ble.py): a fake bleak with a fake board on the radio, answering as the firmware does,
its characters in notifications of 20 bytes, the radio's waits left out."""

from __future__ import annotations

import asyncio
import threading
import types
from collections.abc import Callable
from typing import IO, Any, ClassVar, cast

import pytest

from app.connectors import runtime
from app.connectors.boards import ble, esp32c3, rp2040
from app.connectors.boards import protocol as p
from app.connectors.boards import usb_serial as u
from tests.test_beam_board import Chronometer, _until

ID = "50543165e6614103"


class Device:
    def __init__(self, name: str | None, address: str) -> None:
        self.name, self.address = name, address


class Advert:
    def __init__(self, name: str | None, uuids: list[str] | None = None) -> None:
        self.local_name, self.service_uuids = name, uuids or []


class Radio:
    """The air around the computer: the boards in range, the one connected."""

    in_range: ClassVar[list[tuple[Device, Advert]]] = []
    off: ClassVar[str] = ""  # the system's Bluetooth off: why, as bleak says it
    clients: ClassVar[list[Client]] = []
    kept: ClassVar[list[str]] = []  # the BREAKs the board said, whatever the link
    answers_at = 2_000_000  # the board's clock when it answers, in microseconds
    # The writes 0xFFE1 takes: the ESP32-C3's both; the prototype's BT05 only "write".
    writes: ClassVar[list[str]] = ["write", "write-without-response"]


class Scanner:
    @staticmethod
    async def find_device_by_filter(
        test: Callable[[Device, Advert], bool], timeout: float
    ) -> Device | None:
        if Radio.off:
            raise OSError(Radio.off)
        return next((d for d, a in Radio.in_range if test(d, a)), None)

    @staticmethod
    async def discover(timeout: float, return_adv: bool) -> dict[str, tuple]:
        if Radio.off:
            raise OSError(Radio.off)
        return {d.address: (d, a) for d, a in Radio.in_range}


class Client:
    """A board connected over the radio: it answers as beamcore.py does."""

    def __init__(self, device: Device, disconnected_callback: Callable) -> None:
        self.device, self.gone = device, disconnected_callback
        self.notify: Callable[[Any, bytearray], None] | None = None
        self.written: list[bytes] = []
        self.responses: list[bool] = []  # each write's kind: answered, or not
        self.commands = ""
        self.connected = False
        serial = types.SimpleNamespace(properties=["read", *Radio.writes, "notify"])
        self.services = types.SimpleNamespace(get_characteristic=lambda _: serial)
        Radio.clients.append(self)

    async def connect(self) -> None:
        self.connected = True

    async def start_notify(self, char: str, callback: Callable) -> None:
        if self.device.name == "no-serial":
            raise OSError("Characteristic 0000ffe1-... was not found!")
        assert char == ble.CHARACTERISTIC
        self.notify = callback

    async def write_gatt_char(self, char: str, data: bytes, response: bool) -> None:
        assert char == ble.CHARACTERISTIC and len(data) <= 20
        self.responses.append(response)
        if not response and "write-without-response" not in Radio.writes:
            return  # dropped on the way, as macOS drops it: the board hears nothing
        self.written.append(data)
        self.commands += data.decode()
        while "\n" in self.commands:
            line, self.commands = self.commands.split("\n", 1)
            self.answer(line)

    def answer(self, line: str) -> None:
        words = line.split()
        if line == "HELLO":
            count = Radio.kept[-1].split()[1] if Radio.kept else "0"
            self.say(f"HELLO beam-esp32c3 {rp2040.FIRMWARE} {ID} {count}")
        elif words[:1] == ["PING"]:
            self.say(f"PONG {words[1]} {Radio.answers_at} {Radio.answers_at}")
        elif words[:1] == ["RESEND"]:
            for kept in Radio.kept:
                if int(kept.split()[1]) >= int(words[1]):
                    self.say(kept, keep=False)

    def say(self, line: str, *, keep: bool = True) -> None:
        """A line in pieces of 20 bytes, as the board's notifications come."""
        if keep and line.startswith("BREAK"):
            Radio.kept.append(line)
        if not self.connected or self.notify is None:
            return  # nobody to hear it: the board keeps it for RESEND
        data = f"{line}\r\n".encode()
        for at in range(0, len(data), 20):
            self.notify(None, bytearray(data[at : at + 20]))

    async def disconnect(self) -> None:
        self.connected = False

    def drop(self) -> None:
        """Out of range: the system says so through the callback."""
        self.connected = False
        self.gone(self)


@pytest.fixture
def bleak(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    monkeypatch.setattr(Radio, "in_range", [])
    monkeypatch.setattr(Radio, "off", "")
    monkeypatch.setattr(Radio, "clients", [])
    monkeypatch.setattr(Radio, "kept", [])
    monkeypatch.setattr(Radio, "writes", ["write", "write-without-response"])
    monkeypatch.setattr(u, "now_ms", lambda: 1_000_000.0)
    monkeypatch.setattr(ble, "now_ms", lambda: 1_000_000.0)
    monkeypatch.setattr(p, "RADIO_PING_EVERY_S", 0.01)
    monkeypatch.setattr(u, "REOPEN_AFTER_S", 0.01)
    return types.SimpleNamespace(BleakScanner=Scanner, BleakClient=Client)


def _run(
    bleak: types.SimpleNamespace, settings: dict[str, Any], board: Any = esp32c3.RADIO
) -> tuple[ble.RadioConnector, Chronometer, list[int]]:
    chronometer = Chronometer()
    connector = ble.RadioConnector(cast(IO[str], chronometer), bleak, board)
    ended: list[int] = []
    threading.Thread(
        target=lambda: ended.append(connector.run(chronometer)), daemon=True
    ).start()
    assert chronometer.next()["connector"] == board.name
    chronometer.tell({"cmd": "start", "settings": settings})
    return connector, chronometer, ended


def _board_in_range(name: str = "beam-4103", address: str = "AA:BB") -> Device:
    device = Device(name, address)
    Radio.in_range.append((device, Advert(name, [ble.SERVICE])))
    return device


def test_the_board_named_is_read_and_its_break_timed_by_its_clock(bleak):
    _board_in_range()
    Radio.in_range.append((Device("beam-9999", "CC:DD"), Advert("beam-9999")))
    connector, chronometer, ended = _run(bleak, {"device": "BEAM-4103"})
    assert chronometer.next() == {
        "type": "status",
        "state": "connecting",
        "detail": "beam-4103 (Bluetooth)",
    }
    assert chronometer.next()["detail"] == f"beam-esp32c3 {rp2040.FIRMWARE} {ID}"
    [client] = Radio.clients  # only the one named: never the other in range
    assert client.device.name == "beam-4103"
    _until(lambda: connector.bridge.sync.read)
    client.say("BREAK 1 2500000")
    assert chronometer.next() == {
        "type": "beam",
        "seq": 1,
        "time_ms": 1_000_500,
        "device_time": "2500000",
    }
    assert all(len(piece) <= ble.CHUNK for piece in client.written)
    assert not any(client.responses)  # it takes writes without response: no wait
    chronometer.tell({"cmd": "stop"})
    _until(lambda: ended == [0])
    assert not client.connected  # let go: it advertises again for the next reader


def test_a_board_taking_only_writes_with_response_hears_its_commands(
    bleak, monkeypatch
):
    """The prototype's BT05 offers 0xFFE1 no write without response: a command sent
    so is dropped on the way, and the board would never be heard."""
    monkeypatch.setattr(Radio, "writes", ["write"])
    _board_in_range("beam-7c1c")
    _, chronometer, ended = _run(bleak, {"device": "beam-7c1c"})
    assert chronometer.next()["state"] == "connecting"
    assert chronometer.next()["detail"] == f"beam-esp32c3 {rp2040.FIRMWARE} {ID}"
    [client] = Radio.clients
    assert client.responses and all(client.responses)
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_with_no_board_named_the_boards_in_range_are_said_and_none_read(bleak):
    _board_in_range("beam-4103", "AA:BB")
    Radio.in_range.append((Device("BT05", "EE:FF"), Advert("BT05", [ble.SERVICE])))
    Radio.in_range.append((Device("Headphones", "11:22"), Advert("Headphones")))
    _, chronometer, ended = _run(bleak, {})
    status = chronometer.next()
    assert status["state"] == "disconnected"
    assert status["detail"] == (
        'name the board in Settings, as {"device": "beam-1a2b"}; in range: '
        "BT05 (EE:FF), beam-4103 (AA:BB)"
    )
    assert Radio.clients == []
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_no_board_in_range_or_none_of_the_name_is_said(bleak):
    _, chronometer, ended = _run(bleak, {})
    assert chronometer.next()["detail"] == "no Bluetooth beam board in range"
    chronometer.tell(None)
    _until(lambda: ended == [0])
    _, chronometer, ended = _run(bleak, {"device": "beam-0000"})
    assert chronometer.next()["detail"] == (
        "no Beam board ESP32-C3 (Bluetooth) named 'beam-0000' in range"
    )
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_bluetooth_off_on_the_computer_is_said_and_tried_again(bleak):
    Radio.off = "Bluetooth device is turned off"
    _, chronometer, ended = _run(bleak, {"device": "beam-4103"})
    assert chronometer.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": "Bluetooth device is turned off",
    }
    _board_in_range()
    Radio.off = ""  # switched on
    assert chronometer.next()["state"] == "connecting"
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_a_break_seen_while_out_of_range_comes_once_the_board_is_back(bleak):
    """The board went on timing while the radio link was down: found again, it is
    asked for what it counted meanwhile, which comes with the board's own time."""
    _board_in_range()
    connector, chronometer, ended = _run(bleak, {"device": "beam-4103"})
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    _until(lambda: connector.bridge.sync.read)
    Radio.clients[0].say("BREAK 1 2500000")
    assert chronometer.next()["seq"] == 1
    Radio.clients[0].drop()
    assert chronometer.next() == {
        "type": "status",
        "state": "disconnected",
        "detail": ble.LOST,
    }
    Radio.clients[0].say("BREAK 2 2700000")  # nobody hears it, the board keeps it
    assert [chronometer.next()["state"] for _ in range(2)] == [
        "connecting",
        "connected",
    ]
    assert chronometer.next() == {
        "type": "beam",
        "seq": 2,
        "time_ms": 1_000_700,
        "device_time": "2700000",
    }
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_a_line_in_pieces_is_one_line_timed_when_its_first_piece_came(monkeypatch):
    lines: Any = __import__("queue").Queue()
    times = iter([10.0, 20.0, 30.0])
    monkeypatch.setattr(ble, "now_ms", lambda: next(times))
    link = ble.RadioLink(asyncio.new_event_loop(), lines, "beam-4103")
    link.heard(None, bytearray(b"PONG 1 1234567890 12"))
    link.heard(None, bytearray(b"34567890\r\nBREAK 2 "))
    link.heard(None, bytearray(b"99\r\n" + b"x" * 200))
    assert lines.get_nowait() == ("board", ("PONG 1 1234567890 1234567890", 10.0))
    assert lines.get_nowait() == ("board", ("BREAK 2 99", 20.0))
    assert lines.empty() and len(link.line) == ble.LINE_MAX


def test_a_write_cut_short_by_the_link_going_ends_quietly():
    class Failing:
        written = 0

        async def write_gatt_char(self, *args: Any, **kwargs: Any) -> None:
            self.written += 1
            raise OSError("not connected")

    link = ble.RadioLink(asyncio.new_event_loop(), __import__("queue").Queue(), "x")
    link.client = Failing()
    asyncio.run(link.send(b"x" * 50))
    assert link.client.written == 1  # the rest of the line not tried


def test_a_link_never_connected_closes_without_waiting():
    link = ble.RadioLink(asyncio.new_event_loop(), __import__("queue").Queue(), "x")
    link.close()  # no client: nothing to disconnect


def test_a_device_of_the_name_with_no_serial_service_is_let_go(bleak):
    _board_in_range("no-serial", "AA:BB")
    _, chronometer, ended = _run(bleak, {"device": "no-serial"})
    assert chronometer.next()["detail"].startswith("Characteristic 0000ffe1")
    assert Radio.clients and not any(c.connected for c in Radio.clients)
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_a_board_found_by_its_address_is_read_too(bleak):
    _board_in_range("BT05", "AA:BB:CC:DD:EE:FF")
    _, chronometer, ended = _run(bleak, {"device": "aa:bb:cc:dd:ee:ff"}, rp2040.RADIO)
    assert chronometer.next()["detail"] == "BT05 (Bluetooth)"
    chronometer.tell(None)
    _until(lambda: ended == [0])


def test_the_chronometer_runs_a_bluetooth_board_through_ble(monkeypatch):
    ran: list[Any] = []
    monkeypatch.setattr(ble, "run", ran.append)
    runtime.run("beam-esp32c3-ble")
    monkeypatch.setattr(u, "run", ran.append)
    runtime.run("beam-esp32c3")
    assert ran == [esp32c3.RADIO, esp32c3.BOARD]
