"""The beam source of spec 003: every board the judge picked, read at once.

The chronometer starts ``<chronometer> --connector beam-boards``; this answers on
standard input and output with the connector protocol, as usb_serial.py does, for
several boards: each picked board is a link of its own, through usb_serial.py's or
ble.py's connector, with its own bridge, so its own clock and counts. Every BREAK of
every board goes out as it comes, nothing merged (FR-004); each board's state and
errors go out with its name before them (FR-005). ``{"cmd": "blink", "board": <key>}``
blinks one board's LED (FR-003). Its settings, the pick as ``beam-scan`` finds them:

    {"boards": [{"link": "ble", "device": "<address>", "name": "beam-7c1c"},
                {"link": "usb", "port": "COM7", "kind": "beam-rp2040"}],
     "hold_off_ms": 1000}

``beam-blink`` is the same for one board, before timing: its LED blinked, and the end.
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import sys
import threading
import time
from collections.abc import Iterable
from typing import IO, Any

from app import connector_protocol as cp
from app.connectors.boards import Board, ble, esp32c3, rp2040
from app.connectors.boards.usb_serial import Connector, watch_parent

NAME = "beam-boards"
# A board on Bluetooth says its kind only in its HELLO: either kind's is taken.
ANY_RADIO = Board(
    name=NAME,
    label="Beam board (Bluetooth)",
    hello="",
    firmware=rp2040.FIRMWARE,
    transport="ble",
)
# A board on USB is of the kind its USB ids gave: the two kinds' control lines differ,
# and one's would reset the other's chip.
USB_KINDS = {spec.hello: spec for spec in (rp2040.BOARD, esp32c3.BOARD)}
FLASHES, FLASH_EVERY_S = 5, 0.4  # a blink: FLASH 1 to FLASH 5
BLINK_WAIT_S = 20.0  # a scan, a connection and a HELLO, with time to spare
NONE_PICKED = "no board picked: find the boards around and pick one"


def key_of(pick: dict[str, Any]) -> str:
    """A picked board as told apart from the others: its address or its port."""
    if pick.get("link") == "ble":
        return str(pick.get("device") or "")
    return str(pick.get("port") or pick.get("kind") or "")


class Many:
    """The chronometer on standard input and output, and a link for each board picked:
    one loop takes the chronometer's commands and each link's lines, in turn."""

    name = NAME

    def __init__(self, stdout: IO[str], serial: Any, bleak: Any) -> None:
        self.stdout, self.serial, self.bleak = stdout, serial, bleak
        self.inbox: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.links: dict[str, Connector] = {}  # by key_of
        self.names: dict[str, str] = {}  # the judge's name for each
        self.readers: dict[str, str] = {}  # by board id, the key of the link it is on
        self.loop: asyncio.AbstractEventLoop | None = None
        self.scan_lock: asyncio.Lock | None = None
        self.flashes: list[tuple[float, str, int]] = []  # (due, key, n)
        self.started = False
        self.unknown: set[str] = set()

    def send(self, message: dict[str, Any]) -> None:
        self.stdout.write(json.dumps(message) + "\n")
        self.stdout.flush()

    def commands(self, stdin: Iterable[bytes]) -> None:
        for raw in stdin:
            try:
                command = json.loads(raw)
            except ValueError:
                command = None
            if isinstance(command, dict):
                self.inbox.put(("command", command))
            else:  # the protocol: logged and ignored
                print(f"not a JSON object, ignored: {raw[:80]!r}", file=sys.stderr)
        self.inbox.put(("eof", None))

    def link_for(self, pick: dict[str, Any], named: str) -> Connector | None:
        """A picked board's connector, what it says said with its name before it;
        None for a board on USB of no kind known."""
        if pick.get("link") == "ble":
            if self.loop is None:  # one loop for every board on Bluetooth
                self.loop = asyncio.new_event_loop()
                threading.Thread(target=self.loop.run_forever, daemon=True).start()
                self.scan_lock = asyncio.Lock()
            link: Connector = ble.RadioConnector(
                self.stdout, self.bleak, ANY_RADIO, self.loop, self.scan_lock
            )
        elif (spec := USB_KINDS.get(str(pick.get("kind")))) is not None:
            link = Connector(self.stdout, self.serial, spec)
        else:
            return None
        said = link.send

        def send(message: dict[str, Any]) -> None:
            if message.get("type") == "status":
                message = {**message, "detail": f"{named}: {message['detail']}"}
            elif message.get("type") == "error":
                message = {**message, "message": f"{named}: {message['message']}"}
            said(message)

        link.send = send  # type: ignore[method-assign]
        return link

    def configure(self, settings: object) -> None:
        """The boards picked, each a link started; none picked is said."""
        settings = settings if isinstance(settings, dict) else {}
        picks = settings.get("boards")
        if not isinstance(picks, list):
            picks = []
        for pick in picks:
            key = key_of(pick) if isinstance(pick, dict) else ""
            if not key:  # typed by hand, say: said, not left out unseen
                self.send(
                    {
                        "type": "error",
                        "message": "a board picked with no address or port "
                        f"({pick!r}): find the boards again and pick it",
                    }
                )
                continue
            if key in self.links:
                continue  # picked twice: read once
            named = str(pick.get("name") or key)
            link = self.link_for(pick, named)
            if link is None:
                self.send(
                    {
                        "type": "error",
                        "message": f"{named}: a USB board of no kind known "
                        f"({pick.get('kind')!r}): find the boards again and pick it",
                    }
                )
                continue
            where = "device" if pick.get("link") == "ble" else "port"
            link.configure({**settings, where: pick.get(where)})  # and its hold-off
            link.started = True
            self.links[key], self.names[key] = link, named
        if not self.links:
            self.send(
                {"type": "status", "state": "disconnected", "detail": NONE_PICKED}
            )

    def blink(self, key: str, now: float) -> None:
        """The board's LED lit FLASHES times, or why not."""
        link = self.links.get(key)
        if link is None:
            self.send({"type": "error", "message": f"{key}: not a board read here"})
        elif link.link is None or not link.bridge.board:
            self.send(
                {
                    "type": "error",
                    "message": f"{self.names[key]}: not connected, so not blinked",
                }
            )
        else:
            self.flashes += [
                (now + n * FLASH_EVERY_S, key, n + 1) for n in range(FLASHES)
            ]

    def obey(self, command: dict[str, Any], now: float) -> bool:
        """One of the chronometer's commands; False for stop."""
        cmd = command.get("cmd")
        if cmd == "stop":
            return False
        if cmd == "ping":
            self.send({"type": "pong", "id": command.get("id")})
        elif cmd == "start":
            if not self.started:  # a second start changes nothing
                self.configure(command.get("settings"))
            self.started = True
        elif cmd == "blink":
            self.blink(str(command.get("board") or ""), now)
        elif repr(cmd) not in self.unknown:  # the protocol: logged once, ignored
            self.unknown.add(repr(cmd))
            print(f"unknown cmd {cmd!r}: ignored", file=sys.stderr)
        return True

    def tick(self, now: float) -> bool:
        """Every link's turn: its PINGs and opening, then what came on it; the
        flashes due. False once there is no more to do."""
        for link in self.links.values():
            link.tick(now)
            while True:
                try:
                    kind, item = link.inbox.get_nowait()
                except queue.Empty:
                    break
                link.handle(kind, item)
        self.drop_twins()
        due = [f for f in self.flashes if f[0] <= now]
        self.flashes = [f for f in self.flashes if f[0] > now]
        for _, key, n in due:
            board = self.links.get(key)  # not let go since, as a twin
            if board is not None and board.link is not None:  # nor lost
                board.write(f"FLASH {n}\n")
        return True

    def drop_twins(self) -> None:
        """One board picked on two links, its USB and its Bluetooth (the list cannot
        tell them one before its HELLO): read on the link that said HELLO first only,
        or each of its breaks would be two cutoffs. The other's are that one's."""
        for key, link in list(self.links.items()):
            board_id = link.bridge.board_id
            if not board_id or self.readers.setdefault(board_id, key) == key:
                continue
            del self.links[key]
            if link.link is not None:
                link.link.close()
            self.send(
                {
                    "type": "error",
                    "message": f"{self.names[key]}: the same board as "
                    f"{self.names[self.readers[board_id]]}, read on that link only",
                }
            )

    def close(self) -> None:
        # Every board's breaks still waiting for its clock first: a Bluetooth link takes
        # up to 2 s to let go, and the chronometer kills the connector 3 s after stop.
        for link in self.links.values():
            for event in link.bridge.release(float("inf")):
                link.send(event)
        for link in self.links.values():
            if link.link is not None:
                link.link.close()

    def run(self, stdin: Iterable[bytes]) -> int:
        self.send(
            {
                "type": "hello",
                "protocol": cp.PROTOCOL,
                "connector": self.name,
                "kind": "beam",
            }
        )
        threading.Thread(target=self.commands, args=(stdin,), daemon=True).start()
        while self.tick(time.monotonic()):
            try:
                kind, item = self.inbox.get(timeout=0.01)  # the links' turns between
            except queue.Empty:
                continue
            if kind == "eof" or not self.obey(item, time.monotonic()):
                break
        self.close()
        return 0


class Blink(Many):
    """``beam-blink``: the one board picked, its LED blinked once it says HELLO, and
    the end; or, not reached within BLINK_WAIT_S, said so."""

    name = "beam-blink"

    def __init__(self, stdout: IO[str], serial: Any, bleak: Any) -> None:
        super().__init__(stdout, serial, bleak)
        self.until: float | None = None
        self.asked = False

    def tick(self, now: float) -> bool:
        super().tick(now)
        if not self.started:
            return True
        if self.until is None:
            self.until = now + BLINK_WAIT_S
        for key, link in self.links.items():
            if not self.asked and link.link is not None and link.bridge.board:
                self.asked = True
                self.blink(key, now)
                # Till the last flash is lit: a link closed at once may drop it.
                self.until = now + (FLASHES + 1) * FLASH_EVERY_S
        if self.asked or not self.links:  # blinked, or nothing to blink: said why
            return self.asked and now <= self.until
        if now > self.until:
            self.send(
                {
                    "type": "error",
                    "message": f"{', '.join(self.names.values())}: not reached "
                    f"within {BLINK_WAIT_S:.0f} s: is it on, in range, and read by "
                    "no other program or phone?",
                }
            )
            return False
        return True


def run(kind: type[Many] = Many) -> int:
    """The process entry for ``--connector beam-boards`` (or ``beam-blink``)."""
    threading.Thread(target=watch_parent, args=(os.getppid(),), daemon=True).start()
    import bleak
    import serial

    # Unbuffered, as usb_serial.py reads it: a thread blocked in a buffered read
    # holds its lock, and the exit after "stop" would abort on it.
    stdin = open(sys.stdin.fileno(), "rb", buffering=0, closefd=False)
    return kind(sys.stdout, serial, bleak).run(stdin)
