"""The device's clock against world time (app/device_time.py): NTP's answers read and
weighed, and a clock that follows them without ever running backwards."""

from __future__ import annotations

import itertools
import socket
import struct
import sys
import time
from typing import Any

import pytest

from app import device_time as dt

WORLD_MS = 1_800_000_000_000.0  # world time at monotonic 0 in these tests


def _stamp(unix_ms: float) -> int:
    seconds, ms = divmod(unix_ms, 1000)
    return (int(seconds) + dt.NTP_EPOCH_S) % 2**32 << 32 | int(ms / 1000 * 2**32)


def _reply(
    cookie: int,
    received_ms: float,
    sent_ms: float,
    *,
    stratum: int = 2,
    leap: int = 0,
    mode: int = 4,
) -> bytes:
    first = leap << 6 | 4 << 3 | mode
    head = struct.pack("!BBxx", first, stratum) + bytes(20)
    return head + struct.pack("!QQQ", cookie, _stamp(received_ms), _stamp(sent_ms))


class Clock:
    """A monotonic clock and a system one, moved by hand."""

    def __init__(self, system_ahead_ms: float = 0.0) -> None:
        self.s = 100.0
        self.system_ahead_ms = system_ahead_ms

    def mono(self) -> float:
        return self.s

    def system(self) -> float:
        return (WORLD_MS + self.s * 1000 + self.system_ahead_ms) / 1000


def test_a_request_is_a_client_s_with_a_cookie_for_its_time():
    data = dt.request(0x0102030405060708)
    assert len(data) == 48 and data[0] == 0x23
    assert data[40:] == bytes(range(1, 9))


def test_an_ntp_time_reads_as_unix_milliseconds_past_2036_too():
    assert dt.ntp_ms(_stamp(WORLD_MS + 250)) == pytest.approx(WORLD_MS + 250, abs=1e-3)
    assert dt.ntp_ms(_stamp(2_200_000_000_000)) == pytest.approx(2_200_000_000_000)


def test_an_answer_gives_the_offset_and_the_trip_less_the_server_s_time():
    # sent at 1000 on this clock, got at 1030; the server got it at world 2010 and
    # answered at 2012: 28 ms of trip, the offset 1000 + (10 - 18) / 2.
    data = _reply(7, WORLD_MS + 2010, WORLD_MS + 2012)
    one = dt.answer("s", data, 7, 1000.0, 1030.0)
    assert one is not None
    assert one.trip_ms == pytest.approx(28.0, abs=1e-3)
    assert one.offset_ms == pytest.approx(WORLD_MS + 996.0, abs=1e-3)


@pytest.mark.parametrize(
    "data",
    [
        _reply(7, WORLD_MS, WORLD_MS)[:47],  # cut short
        _reply(7, WORLD_MS, WORLD_MS, mode=3),  # a client's, not a server's
        _reply(7, WORLD_MS, WORLD_MS, leap=3),  # the alarm: not synchronised
        _reply(7, WORLD_MS, WORLD_MS, stratum=0),  # a kiss of death
        _reply(7, WORLD_MS, WORLD_MS, stratum=16),  # not synchronised
        _reply(8, WORLD_MS, WORLD_MS),  # another request's
        _reply(7, WORLD_MS, WORLD_MS + 500),  # the server's time longer than the trip
    ],
)
def test_an_answer_not_to_be_taken_is_none(data):
    assert dt.answer("s", data, 7, 0.0, 30.0) is None


class Sock:
    """A UDP socket whose server answers as ``answers`` says, in turn."""

    def __init__(self, answers: list[Any]) -> None:
        self.answers = answers
        self.cookie = 0

    def __enter__(self) -> Sock:
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def settimeout(self, _: float) -> None:
        pass

    def sendto(self, data: bytes, _: object) -> None:
        self.cookie = struct.unpack("!Q", data[40:])[0]

    def recvfrom(self, _: int) -> tuple[bytes, object]:
        reply = self.answers.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply(self.cookie), None


def test_a_server_is_asked_a_few_times_and_not_again_once_silent(monkeypatch):
    """A refused try is tried again; a silent one ends the server's turn: five silent
    servers then take 5 s, not 20."""
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(2, 2, 0, "", ("1.2.3.4", 123))]
    )
    ok = lambda c: _reply(c, WORLD_MS + 5, WORLD_MS + 5)  # noqa: E731
    replies: list[Any] = [ok, ConnectionRefusedError("refused"), ok, TimeoutError()]
    ticks = iter(float(t) for t in range(0, 100, 10))
    got = dt.ask("s", lambda: next(ticks), lambda *_: Sock(replies), tries=5)
    assert [round(one.trip_ms) for one in got] == [10, 10]
    assert replies == []  # nothing asked after the silence


def test_a_server_not_found_or_no_network_answers_nothing(monkeypatch):
    def nowhere(*_: object, **__: object) -> list[Any]:
        raise socket.gaierror("not found")

    monkeypatch.setattr(socket, "getaddrinfo", nowhere)
    assert dt.ask("s", lambda: 0.0) == []
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **k: [(2, 2, 0, "", ("1.2.3.4", 123))]
    )

    def no_socket(*_: object) -> socket.socket:
        raise OSError("network is unreachable")

    assert dt.ask("s", lambda: 0.0, no_socket) == []


def test_the_offset_is_the_servers_median_one_that_disagrees_dropped():
    best = [
        dt.Answer("a", 100.0, 20.0),
        dt.Answer("b", 103.0, 10.0),
        dt.Answer("c", 101.0, 30.0),
        dt.Answer("d", 400.0, 8.0),  # 300 ms off with a trip of 8: not to be trusted
    ]
    assert dt.combine(best) == (101.0, 5.0)
    assert dt.combine([]) is None


def test_a_round_keeps_each_server_s_shortest_trip():
    answers = {
        "a": [dt.Answer("a", 110.0, 40.0), dt.Answer("a", 100.0, 10.0)],
        "b": [],
        "c": [dt.Answer("c", 102.0, 12.0)],
    }
    found = dt.measure(lambda: 0.0, ("a", "b", "c"), lambda s, _: answers[s])
    assert found == (101.0, 5.0)


def test_the_clock_runs_on_one_that_goes_on_while_the_computer_sleeps(monkeypatch):
    """Python's monotonic clock stops asleep on macOS and Linux: a laptop closed
    between two heats would wake behind world time by its sleep."""
    asleep_too = {"darwin": "CLOCK_MONOTONIC_RAW", "linux": "CLOCK_BOOTTIME"}
    assert dt._CLOCK_ID == getattr(time, asleep_too.get(sys.platform, ""), None)
    monkeypatch.setattr(dt, "_CLOCK_ID", 77)
    monkeypatch.setattr(time, "clock_gettime", lambda clock: {77: 42.5}[clock])
    assert dt._monotonic() == 42.5
    monkeypatch.setattr(dt, "_CLOCK_ID", None)  # Windows: the monotonic one goes on
    monkeypatch.setattr(time, "monotonic", lambda: 7.25)
    assert dt._monotonic() == 7.25


def test_unmeasured_the_clock_is_the_system_s_and_says_so():
    clock = Clock(system_ahead_ms=37.0)
    device = dt.DeviceClock(clock.mono, clock.system)
    assert device.now_ms() == pytest.approx(WORLD_MS + 100_037.0)
    assert device.described() == "Clock: the system's, not checked"
    assert device.uncertainty_ms() is None


def test_the_first_measurement_and_a_later_one_forward_are_taken_at_once():
    clock = Clock(system_ahead_ms=37.0)
    device = dt.DeviceClock(clock.mono, clock.system)
    assert device.take(WORLD_MS, 4.0, "internet") == "clock: the internet"
    assert device.now_ms() == pytest.approx(WORLD_MS + 100_000.0)  # 37 ms back: at once
    assert device.take(WORLD_MS + 3.0, 4.0, "internet") is None
    assert device.now_ms() == pytest.approx(WORLD_MS + 100_003.0)
    assert device.described() == "Clock: the internet, within 4 ms"


def test_a_correction_back_is_eased_in_and_the_clock_never_runs_backwards():
    clock = Clock()
    device = dt.DeviceClock(clock.mono, clock.system)
    device.take(WORLD_MS + 50.0, 4.0, "internet")
    before = device.now_ms()
    device.take(WORLD_MS, 4.0, "internet")  # 50 ms back
    readings = []
    for _ in range(60):  # 6 s, 0.1 s apart
        clock.s += 0.1
        readings.append(device.now_ms())
    assert readings[0] > before
    assert all(b >= a for a, b in itertools.pairwise(readings))
    assert readings[-1] == pytest.approx(WORLD_MS + clock.s * 1000)  # in by now
    assert readings[0] == pytest.approx(WORLD_MS + 50.0 + 100_100.0 - 10.0)


def test_a_correction_of_over_a_second_is_taken_at_once_and_said():
    clock = Clock()
    device = dt.DeviceClock(clock.mono, clock.system)
    device.take(WORLD_MS + 5_000.0, 4.0, "internet")
    device.now_ms()
    said = device.take(WORLD_MS, 4.0, "internet")
    assert said is not None and said.startswith("clock corrected by -5.000 s")
    assert device.now_ms() == pytest.approx(WORLD_MS + 100_000.0)


def test_the_offset_s_rate_is_followed_once_measurements_span_ten_minutes():
    clock = Clock()
    device = dt.DeviceClock(clock.mono, clock.system)
    for _ in range(12):  # 64 s apart, the clock 20 ppm slow against world time
        device.take(WORLD_MS + 20e-6 * clock.s * 1000, 3.0, "internet")
        clock.s += 64.0
    assert device.rate == pytest.approx(20e-6, rel=1e-6)
    clock.s += 3600.0  # an hour with no internet: still the rate's
    assert device.now_ms() == pytest.approx(
        WORLD_MS + clock.s * 1000 * (1 + 20e-6), abs=1e-3
    )
    # 3 ms at the last measurement, 5 ppm of the hour and 64 s since: 21 ms.
    assert device.uncertainty_ms() == pytest.approx(3.0 + 5e-3 * (3600 + 64), rel=1e-6)


def test_without_its_rate_the_offset_goes_stale_at_50_ppm():
    clock = Clock()
    device = dt.DeviceClock(clock.mono, clock.system)
    device.take(WORLD_MS, 3.0, "internet")
    clock.s += 100.0
    assert device.uncertainty_ms() == pytest.approx(3.0 + 50e-3 * 100)


def test_a_connector_s_event_on_the_system_clock_is_moved_onto_this_one():
    clock = Clock(system_ahead_ms=37.0)
    device = dt.DeviceClock(clock.mono, clock.system)
    device.take(WORLD_MS, 4.0, "internet")
    system_ms = clock.system() * 1000 - 250.0  # an event 250 ms ago, on the system's
    assert device.from_system(system_ms) == pytest.approx(
        WORLD_MS + clock.s * 1000 - 250.0
    )


def test_a_change_of_source_starts_its_rate_anew():
    clock = Clock()
    device = dt.DeviceClock(clock.mono, clock.system)
    for _ in range(12):
        device.take(WORLD_MS + 20e-6 * clock.s * 1000, 3.0, "internet")
        clock.s += 64.0
    assert device.take(WORLD_MS + 20e-6 * clock.s * 1000, 1.0, "gnss") == "clock: GNSS"
    assert device.rate == 0.0 and device.points == [(clock.s, device.target_ms)]
