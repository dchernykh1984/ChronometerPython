"""The beam board's firmware, firmware/beam_rp2040/main.py, run on the computer.

MicroPython's modules are faked: its 30-bit microsecond ticks are a counter the
test moves on, the sensor's pin a level the test sets, and the pin's IRQ is called
on each rising edge, as the board's would be. The loop's steps are run one
millisecond at a time, as main.py's own loop runs them.
"""

from __future__ import annotations

import importlib
import sys
import time
import types
from collections.abc import Iterator
from typing import Any

import pytest

WRAP = 1 << 30  # MicroPython's ticks wrap here


class Ticks:
    """MicroPython's ticks: microseconds modulo 2**30, as the board counts them."""

    def __init__(self, start_us: int) -> None:
        self.us = start_us

    def ticks_us(self) -> int:
        return self.us % WRAP

    @staticmethod
    def ticks_diff(a: int, b: int) -> int:
        return (a - b + WRAP // 2) % WRAP - WRAP // 2

    def sleep_ms(self, ms: int) -> None:
        self.us += ms * 1000


class Pin:
    IN, PULL_UP, IRQ_RISING = 0, 1, 2

    def __init__(self, n: int, mode: int | None = None, pull: int | None = None):
        self.n, self.pull, self.level = n, pull, 0

    def value(self) -> int:
        return self.level

    def irq(self, **_: object) -> None:
        pass


class NeoPixel(list):
    def __init__(self, pin: Pin, n: int) -> None:
        super().__init__([(0, 0, 0)] * n)

    def write(self) -> None:
        pass


class Rig:
    """The board: its sensor's light, its clock, what it says."""

    def __init__(self, firmware: Any, ticks: Ticks, said: list[str]) -> None:
        self.firmware, self.ticks, self.said = firmware, ticks, said
        self.board = firmware.Board()

    def run(self, ms: int, *, blocked: bool | None = None) -> None:
        """The light blocked or not from now on, then ``ms`` of the board's loop."""
        if blocked is not None:
            self.light(blocked)
        for _ in range(ms):
            self.board.breaks()
            self.board.light()
            self.ticks.sleep_ms(1)

    def light(self, blocked: bool) -> None:
        pin = self.board.sensor
        if blocked and not pin.level:
            pin.level = 1
            self.firmware._edge(pin)  # DO rose: the IRQ, before the loop runs on
        pin.level = int(blocked)

    def chatter(self, edges: int) -> None:
        """The comparator in the half-light: the light lost and back, a ms apart."""
        for _ in range(edges):
            self.run(1, blocked=True)
            self.run(1, blocked=False)

    def breaks(self) -> list[int]:
        """The seq of each BREAK said."""
        return [int(line.split()[1]) for line in self.said if line.startswith("BREAK")]


@pytest.fixture
def rig(monkeypatch: pytest.MonkeyPatch) -> Iterator[Rig]:
    yield make_rig(monkeypatch, start_us=0)


def make_rig(monkeypatch: pytest.MonkeyPatch, start_us: int) -> Rig:
    ticks, said = Ticks(start_us), list[str]()
    for name in ("ticks_us", "ticks_diff", "sleep_ms"):
        monkeypatch.setattr(time, name, getattr(ticks, name), raising=False)
    machine = types.ModuleType("machine")
    vars(machine).update(Pin=Pin, unique_id=lambda: b"\x50\x54\x31\x65")
    micropython = types.ModuleType("micropython")
    vars(micropython).update(alloc_emergency_exception_buf=lambda n: None)
    neopixel = types.ModuleType("neopixel")
    vars(neopixel).update(NeoPixel=NeoPixel)
    for module in (machine, micropython, neopixel):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.delitem(sys.modules, "firmware.beam_rp2040.main", raising=False)
    firmware = importlib.import_module("firmware.beam_rp2040.main")
    monkeypatch.setattr(firmware, "print", said.append, raising=False)
    return Rig(firmware, ticks, said)


def test_a_break_is_said_with_the_time_its_edge_came(rig):
    rig.run(100, blocked=False)
    rig.ticks.us += 250  # the light goes mid-millisecond
    rig.run(5, blocked=True)
    assert [line for line in rig.said if line.startswith("BREAK")] == ["BREAK 1 100250"]


def test_a_bike_is_one_break_its_wheels_and_body_within_the_hold_off(rig):
    rig.run(100, blocked=False)
    for _wheel_or_body in range(3):
        rig.run(10, blocked=True)
        rig.run(200, blocked=False)
    assert rig.breaks() == [1]
    rig.run(1000, blocked=False)
    rig.run(10, blocked=True)  # the next rider
    assert rig.breaks() == [1, 2]


def test_the_light_coming_back_after_a_long_block_is_no_break(rig):
    """A rider stopped in the beam, or someone standing in it, for longer than the
    hold-off: the comparator chatters as the light comes back, and that is no rider."""
    rig.run(100, blocked=False)
    rig.run(1500, blocked=True)
    rig.chatter(5)
    rig.run(100, blocked=False)
    assert rig.breaks() == [1]
    rig.run(10, blocked=True)  # the next rider
    assert rig.breaks() == [1, 2]


def test_a_laser_first_aimed_at_the_sensor_is_no_break(rig):
    rig.run(500, blocked=True)  # the board started in the dark
    rig.chatter(5)  # the spot comes onto the sensor
    rig.run(100, blocked=False)
    assert rig.breaks() == []
    rig.run(10, blocked=True)  # then a rider
    assert rig.breaks() == [1]


def test_a_light_that_never_holds_is_said_unsteady_as_no_break_can_be_seen(rig):
    """The spot on the sensor's edge: the comparator flickers, the IRQ is never
    armed again, and the board says so instead of seeing nothing in silence."""
    rig.run(100, blocked=False)
    rig.chatter(600)  # 1.2 s of flicker
    assert rig.breaks() == [1]  # its first edge, the light lost after it held
    assert rig.said[-1] == "STATUS unsteady"
    rig.run(60, blocked=False)
    assert rig.said[-1] == "STATUS beam"


def test_the_clock_carries_on_over_the_ticks_wrapping(monkeypatch):
    """The board's ticks wrap every 18 minutes; its microseconds go on counting."""
    rig = make_rig(monkeypatch, start_us=WRAP - 600_000)
    rig.run(100, blocked=False)
    rig.run(10, blocked=True)
    rig.run(1500, blocked=False)  # the ticks wrap in here
    rig.run(10, blocked=True)
    times = [int(line.split()[2]) for line in rig.said if line.startswith("BREAK")]
    assert times == [100_000, 1_610_000]  # 100 + 10 + 1500 ms on


def test_the_board_answers_what_it_is_asked(rig):
    rig.run(60, blocked=False)  # held 50 ms: said for aiming
    for line in ("PING 7", "hello", "STATUS", "HOLDOFF 300", "HOLDOFF -1", "BEEP"):
        rig.board.answer(line)
    assert rig.said == [
        "STATUS beam",
        "PONG 7 60000",
        f"HELLO beam-rp2040 {rig.firmware.FIRMWARE} 50543165",
        "STATUS beam",
        "HOLDOFF 300",
        "ERROR unknown: HOLDOFF -1",
        "ERROR unknown: BEEP",
    ]
    assert rig.board.hold_off_us == 300_000


def test_a_loose_sensor_wire_reads_as_a_blocked_beam(rig):
    assert rig.board.sensor.pull == Pin.PULL_UP
