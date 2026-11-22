"""The device's own clock against world time (spec 003, FR-007 to FR-015).

NTP is asked of several servers, a few times each, and each one's shortest round trip
taken; a server that is not synchronised, or that disagrees with the others by more
than its round trip allows, is not. The clock is a monotonic one that goes on while the
computer sleeps, plus the offset so measured, its rate followed from one measurement to
the next, so it keeps world time while the internet is gone; with no measurement, the
system's time as it is.
It never runs backwards for a correction under a second, and it never sets the system's
clock. A laptop has no GNSS: the phone's app adds it.
"""

from __future__ import annotations

import os
import socket
import statistics
import struct
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field

SERVERS = (
    "time.google.com",
    "time.cloudflare.com",
    "pool.ntp.org",
    "time.apple.com",
    "time.windows.com",
)
QUERIES = 4  # asked of each server in a round: its shortest round trip is kept
WAIT_S = 1.0  # an answer later than this is none
EVERY_S = 64.0  # a round
AGREE_MS = 1.0  # servers' own times agree within this, over what their trips allow
DRIFT_PPM = 50.0  # how fast an offset goes stale while its rate is not known
RATE_PPM = 5.0  # and while it is: the rate moves with the temperature
RATE_SPAN_S = 600.0  # measurements this far apart give the rate
KEPT_S = 7200.0  # measurements kept for the rate
EASE = 0.1  # a correction that sets the clock back runs it at 0.9 of its speed
AT_ONCE_MS = 1000.0  # a correction over this is taken at once, and said
NTP_EPOCH_S = 2_208_988_800  # from 1900 to 1970
ERA_S = 2**32  # NTP's seconds wrap in 2036


@dataclass(frozen=True)
class Answer:
    """One NTP exchange: world time less this clock's, and the round trip less the
    server's own time, both in milliseconds."""

    server: str
    offset_ms: float
    trip_ms: float


def request(cookie: int) -> bytes:
    """An SNTP version 4 client request, its transmit time a cookie the answer echoes:
    this clock's time is never sent, as the device's clock is no NTP clock."""
    return struct.pack("!B3x36xQ", 0x23, cookie)  # LI 0, version 4, mode 3: a client


def ntp_ms(stamp: int) -> float:
    """An NTP timestamp as Unix milliseconds; seconds below 2**31 are past 2036."""
    seconds = stamp >> 32
    if seconds < 2**31:
        seconds += ERA_S
    return (seconds - NTP_EPOCH_S) * 1000 + (stamp & 0xFFFFFFFF) * 1000 / 2**32


def answer(
    server: str, data: bytes, cookie: int, sent_ms: float, got_ms: float
) -> Answer | None:
    """A server's reply to the request of ``cookie``, sent and got on this clock; None
    for one not to be taken: not a server's, not this request's, or not synchronised
    (stratum 0 or 16 and over, or the leap alarm)."""
    if len(data) < 48:
        return None
    leap, mode, stratum = data[0] >> 6, data[0] & 7, data[1]
    origin, received, sent = struct.unpack("!QQQ", data[24:48])
    if mode != 4 or leap == 3 or not 1 <= stratum <= 15 or origin != cookie:
        return None
    t2, t3 = ntp_ms(received), ntp_ms(sent)
    trip = (got_ms - sent_ms) - (t3 - t2)
    if trip < 0:
        return None
    return Answer(server, ((t2 - sent_ms) + (t3 - got_ms)) / 2, trip)


def ask(
    server: str,
    clock_ms: Callable[[], float],
    opener: Callable[..., socket.socket] = socket.socket,
    tries: int = QUERIES,
) -> list[Answer]:
    """The answers ``server`` gives to ``tries`` requests; none when it is not found or
    does not answer in time."""
    try:
        family, kind, _, _, address = socket.getaddrinfo(
            server, 123, type=socket.SOCK_DGRAM
        )[0]
    except OSError, IndexError:
        return []
    answers = []
    try:
        with opener(family, kind) as sock:
            sock.settimeout(WAIT_S)
            for _ in range(tries):
                cookie = int.from_bytes(os.urandom(8), "big")
                sent = clock_ms()
                try:
                    sock.sendto(request(cookie), address)
                    data = sock.recvfrom(512)[0]
                except TimeoutError:  # silent once: not asked again this round
                    break
                except OSError:  # refused, say: the next try
                    continue
                got = clock_ms()
                if (one := answer(server, data, cookie, sent, got)) is not None:
                    answers.append(one)
    except OSError:  # no socket at all: no network
        return answers
    return answers


def combine(best: list[Answer]) -> tuple[float, float] | None:
    """The offset and how far it may be off, from each server's best answer: one
    further from the others' median than its half round trip allows disagrees, and is
    dropped. None with no answer at all."""
    if not best:
        return None
    middle = statistics.median(one.offset_ms for one in best)
    kept = [
        one for one in best if abs(one.offset_ms - middle) <= one.trip_ms / 2 + AGREE_MS
    ]
    kept = kept or best
    offset = statistics.median(one.offset_ms for one in kept)
    return offset, min(one.trip_ms for one in kept) / 2


def measure(
    clock_ms: Callable[[], float],
    servers: tuple[str, ...] = SERVERS,
    asker: Callable[[str, Callable[[], float]], list[Answer]] = ask,
) -> tuple[float, float] | None:
    """A round: every server asked, each one's shortest round trip kept, combined."""
    best = []
    for server in servers:
        if answers := asker(server, clock_ms):
            best.append(min(answers, key=lambda one: one.trip_ms))
    return combine(best)


# The clock the device clock runs on: one no one sets, that goes on while the computer
# sleeps. Python's monotonic one stops then on macOS (mach_absolute_time) and on Linux,
# and a laptop closed between two heats, the internet gone, would wake its sleep behind
# world time; on Windows it is QueryPerformanceCounter's, which goes on.
_ASLEEP_TOO = {"darwin": "CLOCK_MONOTONIC_RAW", "linux": "CLOCK_BOOTTIME"}
_CLOCK_ID: int | None = getattr(time, _ASLEEP_TOO.get(sys.platform, ""), None)


def _monotonic() -> float:
    if _CLOCK_ID is None:
        return time.monotonic()
    return time.clock_gettime(_CLOCK_ID)


def _system() -> float:
    return time.time()


@dataclass
class DeviceClock:
    """World time as well as this device knows it: the monotonic clock plus the offset
    measured, or the system's time while none is. It never runs backwards: a correction
    that would set it back is eased in, but for one of over a second (a system clock
    set wrong by hand), taken at once and said."""

    mono: Callable[[], float] = _monotonic  # read at each call, as tests set them
    system: Callable[[], float] = _system
    source: str = "system"  # "system", "internet", "gnss"
    error_ms: float | None = None  # at the last measurement; None: not checked
    offset_ms: float | None = None  # world less monotonic, as applied now
    target_ms: float = 0.0  # as measured, the applied one easing to it
    rate: float = 0.0  # the offset's change per monotonic ms, once known
    measured_at: float = 0.0  # monotonic s
    points: list[tuple[float, float]] = field(default_factory=list)  # (mono s, offset)
    eased_at: float = 0.0
    last_ms: float = 0.0

    def __post_init__(self) -> None:
        self.eased_at = self.mono()

    def take(self, offset_ms: float, error_ms: float, source: str) -> str | None:
        """A measurement, ``offset_ms`` world less monotonic; what to tell the judge."""
        at = self.mono()
        said = None
        if source != self.source:
            said = f"clock: {SOURCES[source]}"
        current = self.offset_ms
        if current is None:
            current = self.system() * 1000 - at * 1000
        change = offset_ms - current
        if abs(change) > AT_ONCE_MS:
            said = (
                f"clock corrected by {change / 1000:+.3f} s ({SOURCES[source]}): "
                "the cutoffs before it were on the old clock"
            )
        if self.offset_ms is None or change >= 0 or abs(change) > AT_ONCE_MS:
            self.offset_ms = offset_ms
            self.last_ms = 0.0  # a clock set right by over a second may go back
        self.points = [p for p in self.points if at - p[0] <= KEPT_S]
        self.points.append((at, offset_ms))
        span = at - self.points[0][0]
        if source == self.source and span >= RATE_SPAN_S and len(self.points) >= 3:
            fit = statistics.linear_regression(
                [p[0] * 1000 for p in self.points], [p[1] for p in self.points]
            )
            self.rate = fit.slope
        elif source != self.source:
            self.points, self.rate = [(at, offset_ms)], 0.0
        self.target_ms, self.error_ms = offset_ms, error_ms
        self.source, self.measured_at = source, at
        return said

    def now_ms(self) -> float:
        mono = self.mono()
        if (
            self.offset_ms is None
        ):  # not measured: the system's time, as the system sets it
            self.eased_at = mono
            return self.system() * 1000
        target = self.target_ms + self.rate * (mono - self.measured_at) * 1000
        if target < self.offset_ms:  # back: run slower until it is in
            step = EASE * (mono - self.eased_at) * 1000
            self.offset_ms = max(target, self.offset_ms - step)
        else:
            self.offset_ms = target
        self.eased_at = mono
        self.last_ms = max(mono * 1000 + self.offset_ms, self.last_ms)
        return self.last_ms

    def from_system(self, system_ms: float) -> float:
        """A time on the system's clock, a connector's event's, on this one."""
        return system_ms + self.now_ms() - self.system() * 1000

    def uncertainty_ms(self) -> float | None:
        """How far the clock may be off now; None while it is not checked."""
        if self.error_ms is None:
            return None
        drift = RATE_PPM if self.rate else DRIFT_PPM
        return self.error_ms + drift * (self.mono() - self.measured_at) * 1e-3

    def described(self) -> str:
        """The clock's line for the judge."""
        off = self.uncertainty_ms()
        if off is None:
            return "Clock: the system's, not checked"
        return f"Clock: {SOURCES[self.source]}, within {off:.0f} ms"


SOURCES = {"system": "the system's", "internet": "the internet", "gnss": "GNSS"}
