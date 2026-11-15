"""The beam board contract as a reading program keeps to it, whatever the transport.

specs/001-event-sources/contracts/beam-board-protocol.md: a board's lines as events of
the connector protocol, its microseconds moved onto this computer's clock by PING round
trips, half a trip each way. Nothing here touches a port: usb_serial.py does that.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from app.connectors.boards import Board

LONGEST_TRIP_MS = 20.0  # a round trip longer than this says nothing about the clock
SAMPLES = 9  # round trips kept, their median the offset
STEP_MS = 50.0  # an offset this far from the median: this computer's clock stepped
PING_EVERY_S = 2.0
SILENT_MS = 3 * PING_EVERY_S * 1000  # a PING unanswered this long: the board stopped
SILENT = "the board answers no PING: is main.py running on it?"
BLOCKED_MS = 2000.0  # longer than any rider takes to cross the beam
BLOCKED = "the beam is blocked: no break can be seen until the light is back"
UNSTEADY = "the light flickers on the sensor: no break can be seen; aim it again"
HELD_MS = 3000.0  # a break waits this long for the board's clock, then takes its line's
HELD_MAX = 64


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
        offset = (sent_ms + got_ms) / 2 - board_us / 1000
        # Round trips this short agree within half of one; one that does not saw the
        # computer's clock set anew, and the offsets before it no longer hold.
        if self.offsets and abs(offset - statistics.median(self.offsets)) > STEP_MS:
            self.offsets.clear()
        self.offsets.append(offset)
        del self.offsets[:-SAMPLES]

    def to_host_ms(self, board_us: int) -> int | None:
        if not self.offsets:
            return None
        return round(board_us / 1000 + statistics.median(self.offsets))


@dataclass
class Bridge:
    """One board, from its HELLO on: what it says, as events for the chronometer."""

    spec: Board  # what the board is to say of itself
    sync: ClockSync = field(default_factory=ClockSync)
    pings: dict[int, float] = field(default_factory=dict)  # sent at, by number
    next_ping: int = 1
    board: str = ""  # what its HELLO said: no line counts before it
    held: list[tuple[int, int, str, float]] = field(default_factory=list)  # BREAKs
    dark: str | None = None  # STATUS blocked or unsteady: no break can be seen
    seqs: dict[str, int] = field(default_factory=dict)  # last BREAK, by board id
    board_id: str = ""
    dark_since: float = 0.0

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

    def unseeing(self, now_ms: float) -> str | None:
        """Why no break can be seen, once it has lasted longer than a rider takes."""
        if self.dark is None or now_ms - self.dark_since <= BLOCKED_MS:
            return None
        return BLOCKED if self.dark == "blocked" else UNSTEADY

    def answered(self, n: int, board_us: int, got_ms: float) -> None:
        """PONG n: a round trip for the clock, and the board is there."""
        sent = self.pings.pop(n, None)
        for lost in [k for k in self.pings if k < n]:
            del self.pings[lost]  # a later one answered: the board is there
        if sent is not None:
            self.sync.add(sent, got_ms, board_us)

    def hello(self, rest: list[str]) -> list[dict[str, Any]]:
        """HELLO: from now on the board counts, and runs the firmware it is to."""
        self.board = " ".join(rest)
        self.board_id = rest[2] if len(rest) > 2 else ""
        said = [{"type": "status", "state": "connected", "detail": self.board}]
        runs = rest[1] if len(rest) > 1 else "?"
        if runs != self.spec.firmware:
            said.append(
                {
                    "type": "error",
                    "message": f"the board runs firmware {runs}, the chronometer "
                    f"reads {self.spec.firmware}: flash the board again "
                    "(firmware/ in the repository)",
                }
            )
        return said

    def missing(self, seq: int) -> list[dict[str, Any]]:
        """Breaks the board counted that never came: its link was down meanwhile,
        though not its power. A count begun again is the board started again."""
        last, self.seqs[self.board_id] = self.seqs.get(self.board_id, 0), seq
        if not 0 < last < seq - 1:
            return []
        span = f"{last + 1}" if last + 2 == seq else f"{last + 1} to {seq - 1}"
        return [
            {
                "type": "error",
                "message": f"the board's break(s) {span} did not arrive: its link "
                "was down as they came; check that finish by other means",
            }
        ]

    def beam(self, seq: int, board_us: int, text: str, got_ms: float) -> list[Any]:
        at = self.sync.to_host_ms(board_us)
        beam = {
            "type": "beam",
            "seq": seq,
            "time_ms": round(got_ms) if at is None else at,
            "device_time": text,
        }
        return [beam, *self.missing(seq)]

    def release(self, now_ms: float | None = None) -> list[dict[str, Any]]:
        """Breaks that waited for the board's HELLO and its clock: timed by the
        board's clock once it is read. Given up on HELD_MS after the first came,
        they take the time their lines came, and that is said."""
        if not self.held or not self.board:
            return []
        read = bool(self.sync.offsets)
        if not read and (now_ms is None or now_ms - self.held[0][3] <= HELD_MS):
            return []
        held, self.held = self.held, []
        events = [event for one in held for event in self.beam(*one)]
        if not read:
            events.append(
                {
                    "type": "error",
                    "message": "the board's clock could not be read: "
                    f"{len(held)} break(s) timed by when their lines came",
                }
            )
        return events

    def from_board(self, line: str, got_ms: float) -> list[dict[str, Any]]:
        """Events for the chronometer from one board line, received at ``got_ms``."""
        word, rest = parse(line)
        if word == "HELLO" and rest[:1] == [self.spec.hello]:
            return self.hello(rest)
        numbers = pair(rest)
        if word == "BREAK" and numbers is not None:
            if self.board and self.sync.offsets:
                return self.beam(*numbers, rest[1], got_ms)
            # Before the HELLO, or the clock read: a rider all the same, so it
            # waits, and one from a board that never says HELLO never counts.
            if len(self.held) < HELD_MAX:
                self.held.append((*numbers, rest[1], got_ms))
            return []
        if not self.board:
            return []  # left from before the HELLO asked for, or another firmware's
        if word == "PONG" and numbers is not None:
            self.answered(*numbers, got_ms)
            return self.release()
        if word == "STATUS":
            dark = rest[0] if rest in (["blocked"], ["unsteady"]) else None
            if dark != self.dark:  # said again when asked: since the first
                self.dark, self.dark_since = dark, got_ms
            return []
        if word == "ERROR":
            return [{"type": "error", "message": f"board: {' '.join(rest)}"}]
        return []  # FLASH, HOLDOFF: the board's own business
