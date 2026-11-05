"""Qt-level tests for the clock label: it shows the second a stamp taken now gets.

A referee aims at the label. It was driven by a repeating coarse timer, which Qt
moves up to 5% a tick toward a round moment of its own clock: the label showed the
second before for most of each second, and every stamp looked a second late.
main_window is excluded from coverage, so these are what guard it.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QEventLoop, Qt, QTimer

from app.models import format_time


def test_a_stamp_gets_the_second_the_label_shows(win, monkeypatch):
    win._chk_summer_time.setChecked(False)
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000.002)  # a second starts
    win._on_timer_tick()
    assert win._lbl_timer.text() == format_time(1_700_000_000_002, accuracy=0)
    assert win._timer.timerType() == Qt.TimerType.PreciseTimer
    assert win._timer.interval() == 998  # the next tick as the next second starts
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000.999)
    win._on_finish(0)
    assert win._time_edits[0].text().startswith(win._lbl_timer.text() + ".999#")


def test_the_summer_hour_is_on_the_label_as_soon_as_it_is_checked(win, monkeypatch):
    win._chk_summer_time.setChecked(False)
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000.250)
    real = time.localtime
    monkeypatch.setattr(
        time, "localtime", lambda *at: time.struct_time((*real(*at)[:8], 1))
    )  # daylight saving on
    win._on_timer_tick()
    win._chk_summer_time.setChecked(True)  # stamps get the hour at once: the label too
    assert win._lbl_timer.text() == format_time(1_700_000_000_250, 0, dst=True)
    win._on_finish(0)
    assert win._time_edits[0].text().startswith(win._lbl_timer.text() + ".250#")


def test_on_the_event_loop_the_label_shows_the_second_of_the_clock(win):
    """What only the real event loop shows: the tick wired to the timer, firing and
    setting itself again. Looked at mid-second, as a referee does, so a tick held up
    on a busy machine, or one a hair early while the clock is slewed, is not what this
    looks at. A coarse timer drifts over more ticks than this runs: the first test's
    timer type and interval guard that."""
    win._chk_summer_time.setChecked(False)
    looked: list[tuple[float, str]] = []
    probe = QTimer()
    probe.setTimerType(Qt.TimerType.PreciseTimer)
    probe.timeout.connect(lambda: looked.append((time.time(), win._lbl_timer.text())))
    probe.start(25)
    loop = QEventLoop()
    QTimer.singleShot(1500, loop.quit)  # a second's start, whenever it begins
    loop.exec()
    probe.stop()
    mid = [(at, shown) for at, shown in looked if 0.3 <= at % 1 <= 0.95]
    assert len(mid) >= 5
    for at, shown in mid:
        assert shown == format_time(int(at * 1000), accuracy=0), f"at {at:.3f}"
