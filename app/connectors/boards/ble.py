"""A beam board on Bluetooth Low Energy, run as a built-in connector.

The chronometer starts ``<chronometer> --connector <board>-ble``; this answers on
standard input and output with the connector protocol, as usb_serial.py does, and
reads the board over Bluetooth: the HM-10's serial service (0xFFE0 and its
characteristic 0xFFE1), which the RP2040's BT05 has and the ESP32-C3 offers. Only the
board the "device" setting names, by its advertised name or its address, is read;
with none named, the boards in range are said and none is read. bleak runs on an
asyncio loop of a thread of its own; the board's characters become lines in the same
inbox as the chronometer's commands, each line timed when its first piece came.
"""

from __future__ import annotations

import asyncio
import os
import queue
import sys
import threading
import time
from typing import IO, Any

from app.connectors.boards import Board, usb_serial
from app.connectors.boards.usb_serial import (
    LINE_MAX,
    Connector,
    now_ms,
    watch_parent,
)

SERVICE = "0000ffe0-0000-1000-8000-00805f9b34fb"  # the HM-10's serial service
CHARACTERISTIC = "0000ffe1-0000-1000-8000-00805f9b34fb"
CHUNK = 20  # a write's bytes at the default ATT MTU
SCAN_S = 5.0  # how long a scan looks for the board
CLOSE_S = 2.0  # how long a disconnect may take before the connector goes on
LOST = "the board's Bluetooth link was lost: out of range, or switched off"


def described(error: BaseException) -> str:
    return str(error) or type(error).__name__


def is_board(device: Any, advert: Any) -> bool:
    """A beam board in range: named so, or offering the serial service (a BT05 that
    kept its own name)."""
    name = advert.local_name or device.name or ""
    return name.startswith("beam-") or SERVICE in (advert.service_uuids or [])


class RadioLink:
    """A board connected over Bluetooth: bleak's client, and the board's characters
    joined into lines, each timed when its first piece came."""

    def __init__(
        self, loop: asyncio.AbstractEventLoop, inbox: queue.Queue, name: str
    ) -> None:
        self.loop, self.inbox, self.name = loop, inbox, name
        self.client: Any = None
        self.line = ""
        self.first_ms = 0.0
        self.lock = asyncio.Lock()  # one write's pieces never mixed with another's
        self.response = False  # writes answered: a BT05 may take no other kind

    def heard(self, _sender: Any, data: bytearray) -> None:
        """A notification: some of the board's characters."""
        came = now_ms()
        for char in data.decode("ascii", "replace"):
            if char in "\r\n":
                if self.line:
                    self.inbox.put(("board", (self.line, self.first_ms)))
                self.line = ""
            elif len(self.line) < LINE_MAX:
                if not self.line:
                    self.first_ms = came
                self.line += char

    def write(self, data: bytes) -> None:
        asyncio.run_coroutine_threadsafe(self.send(data), self.loop)

    async def send(self, data: bytes) -> None:
        async with self.lock:
            for at in range(0, len(data), CHUNK):
                try:
                    await self.client.write_gatt_char(
                        CHARACTERISTIC, data[at : at + CHUNK], response=self.response
                    )
                except Exception:
                    return

    def close(self) -> None:
        """Disconnected, so that the board advertises again for the next reader."""
        if self.client is None:
            return
        done = asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
        try:
            done.result(timeout=CLOSE_S)
        except Exception:
            done.cancel()


class RadioConnector(Connector):
    """The connector of usb_serial.py, its link Bluetooth: opened on its own loop, as
    finding and connecting a board takes seconds the chronometer must not wait."""

    def __init__(
        self,
        stdout: IO[str],
        bleak: Any,
        spec: Board,
        loop: asyncio.AbstractEventLoop | None = None,
        scan_lock: asyncio.Lock | None = None,
    ) -> None:
        super().__init__(stdout, None, spec)
        self.bleak = bleak
        self.device = ""
        self.pending = False  # a board being found and connected
        # Several boards read at once share one loop, and find and connect their
        # boards one after the other: two scans at once may each find nothing.
        if loop is None:
            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_forever, daemon=True).start()
        self.loop = loop
        self.scan_lock = scan_lock or asyncio.Lock()

    def configure(self, settings: object) -> None:
        super().configure(settings)
        settings = settings if isinstance(settings, dict) else {}
        self.device = str(settings.get("device") or "").strip()

    def write(self, text: str) -> None:
        if self.link is not None:
            self.link.write(text.encode())

    def open_board(self, now: float) -> None:
        if not self.pending:
            self.pending = True
            asyncio.run_coroutine_threadsafe(self.connect(), self.loop)

    async def connect(self) -> None:
        try:
            link = await self.found()
        except Exception as error:
            self.inbox.put(("failed", described(error)))
        else:
            self.inbox.put(("opened", link))

    async def found(self) -> RadioLink:
        """The board named, connected and its notifications on."""
        if not self.device:
            raise LookupError(await self.in_range())
        wanted = self.device.lower()

        def named(device: Any, advert: Any) -> bool:
            names = {advert.local_name or "", device.name or "", device.address}
            return wanted in {name.lower() for name in names}

        scanner = self.bleak.BleakScanner
        async with self.scan_lock:  # a connection made while another scans may fail
            device = await scanner.find_device_by_filter(named, timeout=SCAN_S)
            if device is None:
                raise LookupError(
                    f"no {self.spec.label} named {self.device!r} in range"
                )
            link = RadioLink(self.loop, self.inbox, device.name or self.device)
            link.client = self.bleak.BleakClient(
                device,
                disconnected_callback=lambda _: self.inbox.put(("lost", (link, LOST))),
            )
            await link.client.connect()
        try:
            await link.client.start_notify(CHARACTERISTIC, link.heard)
            # A write without response to a characteristic that offers none is
            # dropped on the way, and the board never hears a command: the
            # prototype's BT05.
            serial = link.client.services.get_characteristic(CHARACTERISTIC)
            link.response = "write-without-response" not in serial.properties
        except Exception:
            # Connected, but no serial service read: another device of the name, say.
            # Let go of it, or it stays held, and the board itself could not connect.
            await link.client.disconnect()
            raise
        return link

    async def in_range(self) -> str:
        """No board named: the boards in range, for the judge to name one."""
        seen = await self.bleak.BleakScanner.discover(timeout=SCAN_S, return_adv=True)
        boards = sorted(
            f"{advert.local_name or device.name} ({device.address})"
            for device, advert in seen.values()
            if is_board(device, advert)
        )
        if not boards:
            return "no Bluetooth beam board in range"
        return (
            'name the board in Settings, as {"device": "beam-1a2b"}; in range: '
            + ", ".join(boards)
        )

    def handle(self, kind: str, item: Any) -> bool:
        if kind == "opened":
            self.pending = False
            self.link = item
            self.opened(f"{item.name} (Bluetooth)", time.monotonic())
            return True
        if kind == "failed":
            self.pending = False
            self.reopen = time.monotonic() + usb_serial.REOPEN_AFTER_S
            self.send({"type": "status", "state": "disconnected", "detail": item})
            return True
        return super().handle(kind, item)


def run(spec: Board) -> int:
    """The process entry for ``--connector <board>-ble``; returns the exit code."""
    threading.Thread(target=watch_parent, args=(os.getppid(),), daemon=True).start()
    import bleak

    # Unbuffered, as usb_serial.py reads it: a thread blocked in a buffered read
    # holds its lock, and the exit after "stop" would abort on it.
    stdin = open(sys.stdin.fileno(), "rb", buffering=0, closefd=False)
    return RadioConnector(sys.stdout, bleak, spec).run(stdin)
