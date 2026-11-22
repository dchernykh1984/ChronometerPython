"""Qt-level tests of the device clock in the window (spec 003, FR-008, FR-009, FR-015):
an NTP round taken on the 1 s tick, every stamp on the corrected clock, the judge shown
where the time comes from. main_window is out of coverage: these guard it."""

from __future__ import annotations

import time

import pytest

from app import device_time
from app.models import format_time


def _measured(win, ahead_ms: float, error_ms: float = 4.0) -> None:
    """The window's clock measured world time ``ahead_ms`` ahead of the system's."""
    clock = win._device_clock
    offset = time.time() * 1000 - clock.mono() * 1000 + ahead_ms
    win._clock_results.put((offset, error_ms))
    win._on_timer_tick()


def test_a_round_that_came_back_is_taken_on_the_tick_and_shown(win):
    assert win._lbl_clock.text() == "Clock: the system's, not checked"
    _measured(win, 37.0, error_ms=4.0)
    assert win._lbl_clock.text() == "Clock: the internet, within 4 ms"
    lines = [win._log.item(i).text() for i in range(win._log.count())]
    assert any(line.endswith("clock: the internet") for line in lines)


def test_a_hand_stamp_is_on_the_corrected_clock(win):
    win._chk_summer_time.setChecked(False)
    _measured(win, 3_600_000.0)  # an hour ahead: taken at once, and said
    before = time.time() * 1000
    win._on_finish(0)
    after = time.time() * 1000
    stamp = win._time_edits[0].text().split("#")[0]
    seconds = {format_time(round(ms + 3_600_000.0))[:-4] for ms in (before, after)}
    assert stamp[:-4] in seconds  # the hour moved, to the second


def test_a_connector_s_event_is_moved_onto_the_corrected_clock(win):
    _measured(win, 250.0)
    system_ms = round(time.time() * 1000) - 1_000  # a break a second ago, the system's
    assert win._event_ms(system_ms) == pytest.approx(system_ms + 250.0, abs=2)
    assert win._event_ms(None) == pytest.approx(time.time() * 1000 + 250.0, abs=50)


def test_the_tick_starts_a_round_when_due_and_none_while_one_runs(win, monkeypatch):
    started = []
    monkeypatch.setattr(
        win, "_clock_round", lambda: started.append(win._clock_next_round)
    )

    class Inline:
        def __init__(self, target, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr("app.main_window.threading.Thread", Inline)
    win._clock_next_round, win._clock_busy = 0.0, False
    win._on_timer_tick()
    assert len(started) == 1 and win._clock_busy
    win._on_timer_tick()  # still busy: none more
    assert len(started) == 1
    win._clock_results.put(None)  # it came back with nothing: the internet is not there
    win._on_timer_tick()
    assert not win._clock_busy and len(started) == 1  # the next is 64 s away
    assert win._clock_next_round > time.monotonic() + device_time.EVERY_S - 5


def test_a_round_that_fails_leaves_the_clock_be(win, monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("no socket today")

    monkeypatch.setattr(device_time, "measure", broken)
    win._clock_round()
    assert win._clock_results.get_nowait() is None
