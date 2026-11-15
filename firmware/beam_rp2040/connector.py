# /// script
# requires-python = ">=3.14"
# dependencies = ["pyserial==3.5"]
# ///
"""The beam board as a connector, run by the chronometer as its custom command.

Source "beam", device "Custom command", and as the command (README.md):

    <uv> run --script <repo>/firmware/beam_rp2040/connector.py [--port P]

It speaks the connector protocol (specs/001-event-sources/contracts/) on its
standard input and output, and the board's lines (main.py) on the board's USB
serial port: the one --port names, else the first Raspberry Pi one found. A break
keeps the board's own time: its microseconds, moved onto this computer's clock by
PING round trips, half a trip each way. A custom command is started with no
settings, so its own come from the command line.
"""

from __future__ import annotations

import argparse
import json
import queue
import statistics
import sys
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import IO, Any

PROTOCOL = 1
NAME = "beam-rp2040"
RASPBERRY_PI_USB = 0x2E8A  # the USB vendor of the RP2040's MicroPython port
LONGEST_TRIP_MS = 20.0  # a round trip longer than this says nothing about the clock
SAMPLES = 9  # round trips kept, their median the offset
PING_EVERY_S = 2.0
REOPEN_AFTER_S = 2.0
SILENT_MS = 3 * PING_EVERY_S * 1000  # a PING unanswered this long: the board stopped
SILENT = "the board answers no PING: is main.py running on it?"


def now_ms() -> float:
    """Unix time in milliseconds: the chronometer's clock."""
    return time.time() * 1000


def parse(line: str) -> tuple[str, list[str]]:
    """A board line as its word and the rest: ``("BREAK", ["12", "812345"])``."""
    words = line.split()
    return (words[0].upper(), words[1:]) if words else ("", [])


def pair(rest: list[str]) -> tuple[int, int] | None:
    """The two whole numbers a BREAK or a PONG carries, else None."""
    if len(rest) != 2 or not all(word.isdigit() for word in rest):
        return None
    return int(rest[0]), int(rest[1])


@dataclass
class ClockSync:
    """The board's microseconds onto this computer's milliseconds, from round trips
    whose middle is taken as the moment the board answered."""

    offsets: list[float] = field(default_factory=list)

    def add(self, sent_ms: float, got_ms: float, board_us: int) -> None:
        if got_ms - sent_ms > LONGEST_TRIP_MS:
            return
        self.offsets.append((sent_ms + got_ms) / 2 - board_us / 1000)
        del self.offsets[:-SAMPLES]

    def to_host_ms(self, board_us: int) -> int | None:
        if not self.offsets:
            return None
        return round(board_us / 1000 + statistics.median(self.offsets))


@dataclass
class Bridge:
    """One board, from its HELLO on: what it says, as events for the chronometer."""

    sync: ClockSync = field(default_factory=ClockSync)
    pings: dict[int, float] = field(default_factory=dict)  # sent at, by number
    next_ping: int = 1
    board: str = ""  # what its HELLO said: nothing counts before it

    def ping(self, sent_ms: float) -> str:
        """The next PING line for the board, its sending time kept."""
        n, self.next_ping = self.next_ping, self.next_ping + 1
        self.pings[n] = sent_ms
        for unanswered in [k for k in self.pings if k <= n - 4 * SAMPLES]:
            del self.pings[unanswered]
        return f"PING {n}"

    def silent(self, now_ms: float) -> bool:
        """A PING unanswered for SILENT_MS: the board has stopped, its port open."""
        return any(now_ms - sent > SILENT_MS for sent in self.pings.values())

    def from_board(self, line: str, got_ms: float) -> list[dict[str, Any]]:
        """Events for the chronometer from one board line, received at ``got_ms``."""
        word, rest = parse(line)
        if word == "HELLO" and rest[:1] == [NAME]:
            self.board = " ".join(rest)
            return [{"type": "status", "state": "connected", "detail": self.board}]
        numbers = pair(rest)
        if not self.board:
            return []  # left from before the HELLO asked for, or another firmware's
        if word == "PONG" and numbers is not None:
            sent = self.pings.pop(numbers[0], None)
            for lost in [k for k in self.pings if k < numbers[0]]:
                del self.pings[lost]  # a later one answered: the board is there
            if sent is not None:
                self.sync.add(sent, got_ms, numbers[1])
            return []
        if word == "BREAK" and numbers is not None:
            at = self.sync.to_host_ms(numbers[1])
            return [
                {
                    "type": "beam",
                    "seq": numbers[0],
                    "time_ms": round(got_ms) if at is None else at,
                    "device_time": rest[1],
                }
            ]
        if word == "ERROR":
            return [{"type": "error", "message": f"board: {' '.join(rest)}"}]
        return []  # STATUS, FLASH, HOLDOFF: the board's own business


def board_port(chosen: str) -> str | None:
    """The port named, else the first Raspberry Pi serial port."""
    if chosen:
        return chosen
    from serial.tools import list_ports  # pyserial, only where a board is used

    found = [p.device for p in list_ports.comports() if p.vid == RASPBERRY_PI_USB]
    return sorted(found)[0] if found else None


class Connector:
    """The chronometer on standard input and output, the board on its serial port:
    one loop takes what either says, in turn, from one inbox."""

    def __init__(
        self, stdout: IO[str], serial: Any, port: str, hold_off_ms: int
    ) -> None:
        self.stdout, self.serial = stdout, serial  # serial: the pyserial module
        self.port, self.hold_off_ms = port, hold_off_ms
        self.inbox: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.bridge = Bridge()
        self.started = False
        self.link: Any = None
        self.next_ping = self.reopen = 0.0
        self.status: tuple[str, str] | None = None  # the last said

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
                continue
            if isinstance(command, dict):
                self.inbox.put(("command", command))
        self.inbox.put(("eof", None))

    def listen(self, link: Any) -> None:
        why = "the board's port closed"
        try:
            for raw in link:
                line = raw.decode("ascii", "replace").strip()
                self.inbox.put(("board", (line, now_ms())))  # timed as it came
        except (OSError, self.serial.SerialException) as error:
            why = str(error) or type(error).__name__
        self.inbox.put(("lost", (link, why)))  # once, naming its port: a new one stays

    def write(self, text: str) -> None:
        try:
            self.link.write(text.encode())
        except OSError, self.serial.SerialException:
            pass  # the listening thread says the port is gone

    def open_board(self, now: float) -> None:
        port = board_port(self.port)
        try:
            if port is None:
                raise OSError("no beam board found on USB")
            self.link = self.serial.Serial(port, timeout=None)
        except (OSError, ValueError, self.serial.SerialException) as error:
            self.reopen = now + REOPEN_AFTER_S
            self.send({"type": "status", "state": "disconnected", "detail": str(error)})
            return
        # The board may have started again: its clock with it, so no old round
        # trip counts, and a ping number once used is not used again.
        self.bridge = Bridge(next_ping=self.bridge.next_ping)
        threading.Thread(target=self.listen, args=(self.link,), daemon=True).start()
        self.send({"type": "status", "state": "connecting", "detail": port})
        self.write(f"\nHOLDOFF {self.hold_off_ms}\nHELLO\n")
        self.next_ping = now

    def tick(self, now: float) -> None:
        if self.started and self.link is None and now >= self.reopen:
            self.open_board(now)
        if self.link is None:
            return
        if now >= self.next_ping:
            self.write(self.bridge.ping(now_ms()) + "\n")
            self.next_ping = now + PING_EVERY_S
        # A board whose main.py has stopped keeps its port open: only PING tells.
        if self.bridge.silent(now_ms()):
            self.send({"type": "status", "state": "disconnected", "detail": SILENT})
        elif self.bridge.board:
            board = self.bridge.board
            self.send({"type": "status", "state": "connected", "detail": board})

    def handle(self, kind: str, item: Any) -> bool:
        """Act on one inbox item; False once the chronometer has said stop."""
        command = item.get("cmd") if kind == "command" else None
        if kind == "eof" or command == "stop":
            return False
        if command == "ping":
            self.send({"type": "pong", "id": item.get("id")})
        elif command == "start":
            self.started = True
        elif kind == "board":
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
            {"type": "hello", "protocol": PROTOCOL, "connector": NAME, "kind": "beam"}
        )
        threading.Thread(target=self.commands, args=(stdin,), daemon=True).start()
        while True:
            self.tick(time.monotonic())
            try:
                kind, item = self.inbox.get(timeout=0.2)
            except queue.Empty:
                continue
            if not self.handle(kind, item):
                if self.link is not None:
                    self.link.close()
                return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--port", default="", help="the board's port; default: the first Raspberry Pi"
    )
    parser.add_argument(
        "--hold-off-ms",
        type=int,
        default=1000,
        help="after a break, edges this soon are the same rider's (default 1000)",
    )
    args = parser.parse_args(argv)
    import serial  # pyserial, only where a board is used

    connector = Connector(sys.stdout, serial, args.port, args.hold_off_ms)
    return connector.run(sys.stdin.buffer)


if __name__ == "__main__":
    sys.exit(main())
