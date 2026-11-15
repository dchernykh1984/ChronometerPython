"""The beam board contract as a reading program keeps to it, whatever the transport.

specs/001-event-sources/contracts/beam-board-protocol.md: a board's lines as events of
the connector protocol, its microseconds moved onto this computer's clock by PING round
trips. Over USB a trip is short and even, and its middle is the board's moment; over
Bluetooth it waits for the radio, so the shortest trip each way is taken instead.
Nothing here touches a port or a radio: usb_serial.py and ble.py do that.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from app.connectors.boards import Board

LONGEST_TRIP_MS = 20.0  # a USB round trip longer than this says nothing about the clock
SAMPLES = 9  # USB round trips kept, their median the offset
STEP_MS = 50.0  # an offset this far from the median: this computer's clock stepped
RADIO_SAMPLES = 16  # Bluetooth round trips kept: the shortest way each way of these
RADIO_READY = 4  # Bluetooth round trips before the board's clock counts as read
RADIO_STEP_MS = 100.0  # beyond a radio trip's own spread: the clock stepped
PING_EVERY_S = 2.0
RADIO_PING_EVERY_S = 1.0  # more trips over Bluetooth: more chances of a short one
SILENT_MS = 6000.0  # a PING unanswered this long: the board stopped
SILENT = "the board answers no PING: is main.py running on it?"
BLOCKED_MS = 2000.0  # longer than any rider takes to cross the beam
BLOCKED = "the beam is blocked: no break can be seen until the light is back"
UNSTEADY = "the light flickers on the sensor: no break can be seen; aim it again"
HELD_MS = 3000.0  # a break waits this long for the board's clock, then takes its line's
RADIO_HELD_MS = 10_000.0  # over Bluetooth the clock takes RADIO_READY answers first
HELD_MAX = 64
RESENT_WITHIN_MS = 10_000.0  # a break asked for again and not come by then: said


def parse(line: str) -> tuple[str, list[str]]:
    """A board line as its word and the rest: ``("BREAK", ["12", "812345"])``."""
    words = line.split()
    return (words[0].upper(), words[1:]) if words else ("", [])


def numbers(rest: list[str], count: int) -> list[int] | None:
    """The ``count`` whole numbers a BREAK or a PONG carries, else None."""
    if len(rest) != count or not all(word.isdigit() for word in rest):
        return None
    return [int(word) for word in rest]


def trip(
    sent_ms: float, got_ms: float, got_us: int, sent_us: int
) -> tuple[float, float]:
    """A PING's way there and its PONG's way back, each the arriving clock less the
    leaving one: their difference is twice the offset, their sum the round trip with
    the board's own wait left out."""
    return got_us / 1000 - sent_ms, got_ms - sent_us / 1000


@dataclass
class ClockSync:
    """Over USB: the board's microseconds onto this computer's milliseconds, from
    round trips short enough that half of one each way is near the truth."""

    offsets: list[float] = field(default_factory=list)

    @property
    def read(self) -> bool:
        return bool(self.offsets)

    def add(self, sent_ms: float, got_ms: float, got_us: int, sent_us: int) -> None:
        there, back = trip(sent_ms, got_ms, got_us, sent_us)
        if there + back > LONGEST_TRIP_MS:
            return
        offset = (back - there) / 2
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
class RadioSync:
    """Over Bluetooth: a message waits for the radio's next connection event, up to
    tens of milliseconds, and a trip's two ways seldom wait alike. The shortest way
    there and the shortest way back of the last trips are each near the radio's bare
    delay, so half their difference is the offset; the board's random wait before a
    PONG gives the way back its short ones too."""

    trips: list[tuple[float, float]] = field(default_factory=list)

    @property
    def read(self) -> bool:
        return len(self.trips) >= RADIO_READY

    @property
    def offset(self) -> float:
        return (min(b for _, b in self.trips) - min(t for t, _ in self.trips)) / 2

    def add(self, sent_ms: float, got_ms: float, got_us: int, sent_us: int) -> None:
        there, back = trip(sent_ms, got_ms, got_us, sent_us)
        if self.read and abs((back - there) / 2 - self.offset) > RADIO_STEP_MS:
            self.trips.clear()  # the computer's clock set anew
        self.trips.append((there, back))
        del self.trips[:-RADIO_SAMPLES]

    def to_host_ms(self, board_us: int) -> int | None:
        if not self.read:
            return None
        return round(board_us / 1000 + self.offset)


@dataclass
class Counts:
    """One board's breaks by count, kept across its link going and coming back:
    each taken once, those missed asked for again."""

    last: int = 0  # the highest count taken, or the one the first HELLO gave
    taken: dict[int, int] = field(default_factory=dict)  # seq: t_us, since its start
    wanted: dict[int, float] = field(default_factory=dict)  # seq: asked for at, ms
    said: set[int] = field(default_factory=set)  # wanted ones said as never come

    def restart(self) -> None:
        """The board started again: its counts begin anew."""
        self.last, self.taken, self.wanted, self.said = 0, {}, {}, set()


@dataclass
class Bridge:
    """One board, from its HELLO on: what it says, as events for the chronometer,
    and the lines it is to be sent beside the PINGs (``outbox``)."""

    spec: Board  # what the board is to say of itself
    sync: ClockSync | RadioSync = field(default_factory=ClockSync)
    pings: dict[int, float] = field(default_factory=dict)  # sent at, by number
    next_ping: int = 1
    board: str = ""  # what its HELLO said: no line counts before it
    held: list[tuple[int, int, str, float]] = field(default_factory=list)  # BREAKs
    dark: str | None = None  # STATUS blocked or unsteady: no break can be seen
    counts: dict[str, Counts] = field(default_factory=dict)  # by board id
    board_id: str = ""
    dark_since: float = 0.0
    outbox: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.spec.transport == "ble" and isinstance(self.sync, ClockSync):
            self.sync = RadioSync()

    @property
    def radio(self) -> bool:
        return self.spec.transport == "ble"

    @property
    def ping_every_s(self) -> float:
        return RADIO_PING_EVERY_S if self.radio else PING_EVERY_S

    def ping(self, sent_ms: float) -> str:
        """The next PING line for the board, its sending time kept."""
        n, self.next_ping = self.next_ping, self.next_ping + 1
        self.pings[n] = sent_ms
        for unanswered in [k for k in self.pings if k <= n - 4 * RADIO_SAMPLES]:
            del self.pings[unanswered]
        return f"PING {n}"

    def silent(self, now_ms: float) -> bool:
        """A PING unanswered for SILENT_MS: the board has stopped, its link up."""
        return any(now_ms - sent > SILENT_MS for sent in self.pings.values())

    def unseeing(self, now_ms: float) -> str | None:
        """Why no break can be seen, once it has lasted longer than a rider takes."""
        if self.dark is None or now_ms - self.dark_since <= BLOCKED_MS:
            return None
        return BLOCKED if self.dark == "blocked" else UNSTEADY

    def answered(self, n: int, got_us: int, sent_us: int, got_ms: float) -> None:
        """PONG n: a round trip for the clock, and the board is there."""
        sent = self.pings.pop(n, None)
        for lost in [k for k in self.pings if k < n]:
            del self.pings[lost]  # a later one answered: the board is there
        if sent is not None:
            self.sync.add(sent, got_ms, got_us, sent_us)

    def hello(self, rest: list[str], got_ms: float) -> list[dict[str, Any]]:
        """HELLO: from now on the board counts, and runs the firmware it is to; what
        it counted while no link was up is asked for again."""
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
                    "(beam/firmware/ in the repository)",
                }
            )
        if len(rest) > 3 and rest[3].isdigit():
            self.catch_up(int(rest[3]), got_ms)
        return said

    def catch_up(self, seq: int, got_ms: float) -> None:
        """The count the board's HELLO gave against the counts taken from it."""
        counts = self.counts.get(self.board_id)
        if counts is None:
            # The first HELLO: breaks before it were not this program's, but those
            # already come on this link, waiting for it, are.
            first = min([seq + 1, *(one[0] for one in self.held)])
            self.counts[self.board_id] = Counts(last=first - 1)
        elif seq > counts.last:
            self.resend(counts, counts.last + 1, seq, got_ms)  # missed while down
        elif seq < counts.last:
            counts.restart()  # it started again, and counted while no link was up
            if seq:
                self.resend(counts, 1, seq, got_ms)

    def resend(self, counts: Counts, first: int, last: int, now_ms: float) -> None:
        for seq in range(first, last + 1):
            counts.wanted.setdefault(seq, now_ms)
        self.outbox.append(f"RESEND {first}")

    def take(self, seq: int, board_us: int, got_ms: float) -> bool:
        """Whether a BREAK is a break this program has not had; a gap before it is
        asked for again."""
        counts = self.counts.get(self.board_id)
        if counts is None:  # no count from a HELLO (another firmware's): from this one
            counts = self.counts[self.board_id] = Counts(last=seq - 1)
        if seq in counts.taken:
            if counts.taken[seq] == board_us:
                return False  # said again: had already
            counts.restart()  # the same count, another time: it started again
        elif seq < counts.last and seq not in counts.wanted:
            counts.restart()  # a lower count, not asked for: it started again
        if seq > counts.last + 1:
            self.resend(counts, counts.last + 1, seq - 1, got_ms)
        counts.taken[seq] = board_us
        counts.wanted.pop(seq, None)
        counts.last = max(counts.last, seq)
        return True

    def overdue(self, now_ms: float) -> list[dict[str, Any]]:
        """Breaks asked for again that have not come within RESENT_WITHIN_MS: they
        never came, the link down as they did. Said once; taken still, if late."""
        events = []
        for counts in self.counts.values():
            late = sorted(
                seq
                for seq, asked in counts.wanted.items()
                if now_ms - asked > RESENT_WITHIN_MS and seq not in counts.said
            )
            if not late:
                continue
            counts.said.update(late)
            span = f"{late[0]}" if len(late) == 1 else f"{late[0]} to {late[-1]}"
            events.append(
                {
                    "type": "error",
                    "message": f"the board's break(s) {span} did not arrive: its link "
                    "was down as they came; check that finish by other means",
                }
            )
        return events

    def beam(self, seq: int, board_us: int, text: str, got_ms: float) -> list[Any]:
        if not self.take(seq, board_us, got_ms):
            return []
        at = self.sync.to_host_ms(board_us)
        return [
            {
                "type": "beam",
                "seq": seq,
                "time_ms": round(got_ms) if at is None else at,
                "device_time": text,
            }
        ]

    def release(self, now_ms: float | None = None) -> list[dict[str, Any]]:
        """Breaks that waited for the board's HELLO and its clock: timed by the
        board's clock once it is read. Given up on after the first came, they take
        the time their lines came, and that is said. And breaks asked for again
        that never came."""
        events = [] if now_ms is None else self.overdue(now_ms)
        if not self.held or not self.board:
            return events
        wait = RADIO_HELD_MS if self.radio else HELD_MS
        read = self.sync.read
        if not read and (now_ms is None or now_ms - self.held[0][3] <= wait):
            return events
        held, self.held = self.held, []
        events += [event for one in held for event in self.beam(*one)]
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
            return self.hello(rest, got_ms)
        if word == "BREAK" and (pair := numbers(rest, 2)) is not None:
            if self.board and self.sync.read:
                return self.beam(pair[0], pair[1], rest[1], got_ms)
            # Before the HELLO, or the clock read: a rider all the same, so it
            # waits, and one from a board that never says HELLO never counts.
            if len(self.held) < HELD_MAX:
                self.held.append((pair[0], pair[1], rest[1], got_ms))
            return []
        if not self.board:
            return []  # left from before the HELLO asked for, or another firmware's
        if word == "PONG" and (pong := numbers(rest, 3)) is not None:
            self.answered(pong[0], pong[1], pong[2], got_ms)
            return self.release()
        if word == "STATUS":
            dark = rest[0] if rest in (["blocked"], ["unsteady"]) else None
            if dark != self.dark:  # said again when asked: since the first
                self.dark, self.dark_since = dark, got_ms
            return []
        if word == "ERROR":
            return [{"type": "error", "message": f"board: {' '.join(rest)}"}]
        return []  # FLASH, HOLDOFF: the board's own business
