"""A beam board on a USB serial port, run as a built-in connector.

The chronometer starts ``<chronometer> --connector <board>``; this answers on standard
input and output with the connector protocol, and reads the board's lines on its port:
the one the "port" setting names, else the first one with the board's USB ids. The
board's lines become events by protocol.py.
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
from collections.abc import Callable, Iterable
from typing import IO, Any

from app import connector_protocol as cp
from app.connectors.boards import Board, protocol
from app.connectors.boards.protocol import Bridge

REOPEN_AFTER_S = 2.0
HOLD_OFF_MS = 1000  # after a break, edges this soon are the same rider's
LONGEST_HOLD_OFF_MS = 60_000


def now_ms() -> float:
    """Unix time in milliseconds: the chronometer's clock."""
    return time.time() * 1000


def board_port(chosen: str, spec: Board) -> str | None:
    """The port named, else the first serial port with the board's USB ids."""
    if chosen:
        return chosen
    from serial.tools import list_ports

    ours = (spec.vendor, spec.product)
    found = [p.device for p in list_ports.comports() if (p.vid, p.pid) == ours]
    return sorted(found)[0] if found else None


def hold_off(value: object) -> int | None:
    """A hold-off setting in whole milliseconds, 1 to 60000, else None. The board
    would take 0, every edge of a chattering sensor then a break, or a typo's hours,
    every break after the first then lost."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if not float(value).is_integer() or not 1 <= value <= LONGEST_HOLD_OFF_MS:
        return None
    return int(value)


class Connector:
    """The chronometer on standard input and output, the board on its serial port:
    one loop takes what either says, in turn, from one inbox."""

    def __init__(self, stdout: IO[str], serial: Any, spec: Board) -> None:
        self.stdout, self.serial, self.spec = stdout, serial, spec  # serial: pyserial
        self.port, self.hold_off_ms = "", HOLD_OFF_MS
        self.inbox: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.bridge = Bridge(spec)
        self.started = False
        self.link: Any = None
        self.next_ping = self.reopen = self.next_hello = 0.0
        self.status: tuple[str, str] | None = None  # the last said
        self.unknown: set[str] = set()  # commands not known, each said once

    def send(self, message: dict[str, Any]) -> None:
        if message["type"] == "status":
            said = (message["state"], message["detail"])
            if said == self.status:
                return  # a board still missing is said once, not at every retry
            self.status = said
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
            else:  # the protocol: logged and ignored, the log the chronometer's
                print(f"not a JSON object, ignored: {raw[:80]!r}", file=sys.stderr)
        self.inbox.put(("eof", None))

    def listen(self, link: Any) -> None:
        why = "the board's port closed"
        try:
            for raw in link:
                if not raw.endswith(b"\n"):
                    continue  # cut short as the port ended: a BREAK of half its digits
                line = raw.decode("ascii", "replace").strip()
                self.inbox.put(("board", (line, now_ms())))  # timed as it came
        except Exception as error:  # whatever ends the reading ends the link
            why = str(error) or type(error).__name__
        self.inbox.put(("lost", (link, why)))  # once, naming its port: a new one stays

    def write(self, text: str) -> None:
        try:
            self.link.write(text.encode())
        except OSError, self.serial.SerialException:
            pass  # the listening thread says the port is gone

    def open_board(self, now: float) -> None:
        port = board_port(self.port, self.spec)
        link = None
        try:
            if port is None:
                raise OSError(f"no {self.spec.label} found on USB")
            # Exclusive: two programs on one port would each get half its lines. A
            # write gives up after 1 s: a board that reads no more must not hang this.
            link = self.serial.Serial(
                port, timeout=None, exclusive=True, write_timeout=1
            )
            if not self.spec.lines:  # DTR first: RTS off with DTR on is the bootloader
                link.dtr = False
                link.rts = False
        except (OSError, ValueError, self.serial.SerialException) as error:
            if link is not None:  # open, but not as it is to be: let go, try again
                link.close()
            self.reopen = now + REOPEN_AFTER_S
            self.send({"type": "status", "state": "disconnected", "detail": str(error)})
            return
        self.link = link
        threading.Thread(target=self.listen, args=(self.link,), daemon=True).start()
        self.opened(port, now)

    def opened(self, where: str, now: float) -> None:
        """A link to the board is up: asked who it is, its clock read anew."""
        # The board may have started again: its clock with it, so no old round
        # trip counts, and a ping number once used is not used again; the counts
        # taken stay, to ask for what it counted while no link was up.
        self.bridge = Bridge(
            self.spec, next_ping=self.bridge.next_ping, counts=self.bridge.counts
        )
        self.send({"type": "status", "state": "connecting", "detail": where})
        self.write(f"\nHOLDOFF {self.hold_off_ms}\nHELLO\nSTATUS\n")
        self.next_ping, self.next_hello = now, now + protocol.HELLO_EVERY_S

    def tick(self, now: float) -> None:
        if self.started and self.link is None and now >= self.reopen:
            self.open_board(now)
        if self.link is None:
            return
        if now >= self.next_ping:
            self.write(self.bridge.ping(now_ms()) + "\n")
            self.next_ping = now + self.bridge.ping_every_s
        for event in self.bridge.release(now_ms()):
            self.send(event)
        if now >= self.next_hello:  # its count: a break whose line was lost shows
            self.write("HELLO\n")
            self.next_hello = now + protocol.HELLO_EVERY_S
        while self.bridge.outbox:  # RESEND: breaks counted while no link was up
            self.write(self.bridge.outbox.pop(0) + "\n")
        # A board whose main.py has stopped keeps its port open: only PING tells.
        if self.bridge.silent(now_ms()):
            self.send(
                {"type": "status", "state": "disconnected", "detail": protocol.SILENT}
            )
        elif self.bridge.board:
            # A laser knocked off its sensor, or a loose wire: the beam sees nothing.
            detail = self.bridge.board
            if why := self.bridge.unseeing(now_ms()):
                detail += f": {why}"
            self.send({"type": "status", "state": "connected", "detail": detail})

    def configure(self, settings: object) -> None:
        """The settings the chronometer starts it with: its port, its hold-off."""
        settings = settings if isinstance(settings, dict) else {}
        self.port = str(settings.get("port") or "")
        given = settings.get("hold_off_ms", HOLD_OFF_MS)
        ms = hold_off(given)
        if ms is None:
            self.send(
                {
                    "type": "error",
                    "message": f"hold_off_ms {given!r} is not 1 to "
                    f"{LONGEST_HOLD_OFF_MS}: {HOLD_OFF_MS} it is",
                }
            )
        self.hold_off_ms = HOLD_OFF_MS if ms is None else ms

    def obey(self, command: dict[str, Any]) -> bool:
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
        elif repr(cmd) not in self.unknown:  # the protocol: logged once, ignored
            self.unknown.add(repr(cmd))
            print(f"unknown cmd {cmd!r}: ignored", file=sys.stderr)
        return True

    def handle(self, kind: str, item: Any) -> bool:
        """Act on one inbox item; False once the chronometer has said stop."""
        if kind == "eof":
            return False
        if kind == "command":
            return self.obey(item)
        if kind == "board":
            for event in self.bridge.from_board(*item):
                self.send(event)
        elif kind == "lost" and item[0] is self.link:
            self.link.close()
            self.link = None
            self.reopen = time.monotonic() + REOPEN_AFTER_S
            self.send({"type": "status", "state": "disconnected", "detail": item[1]})
        return True

    def run(self, stdin: Iterable[bytes]) -> int:
        self.send(
            {
                "type": "hello",
                "protocol": cp.PROTOCOL,
                "connector": self.spec.name,
                "kind": "beam",
            }
        )
        threading.Thread(target=self.commands, args=(stdin,), daemon=True).start()
        while True:
            self.tick(time.monotonic())
            try:
                kind, item = self.inbox.get(timeout=0.2)
            except queue.Empty:
                continue
            if not self.handle(kind, item):
                for event in self.bridge.release(float("inf")):
                    self.send(event)  # a break still waiting for the clock: not lost
                if self.link is not None:
                    self.link.close()
                return 0


def watch_parent(
    parent: int,
    getppid: Callable[[], int] = os.getppid,
    end: Callable[[int], object] = os._exit,
    every_s: float = 1.0,
) -> None:
    """End this connector once the program that started it is gone. A onefile build
    runs it under a bootloader of its own: killed, that would leave this running and
    keep the board's port locked against the next start, however hung it is."""
    while getppid() == parent:
        time.sleep(every_s)
    end(1)


def run(spec: Board) -> int:
    """The process entry for ``--connector <board>``; returns the exit code."""
    threading.Thread(target=watch_parent, args=(os.getppid(),), daemon=True).start()
    import serial

    # Unbuffered, as the other built-in connectors read it: a thread blocked in a
    # buffered read holds its lock, and the exit after "stop" would abort on it.
    stdin = open(sys.stdin.fileno(), "rb", buffering=0, closefd=False)
    return Connector(sys.stdout, serial, spec).run(stdin)
