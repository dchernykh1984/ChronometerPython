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


def test_the_label_flips_as_each_second_of_the_clock_starts(win):
    win._chk_summer_time.setChecked(False)
    ticks: list[tuple[float, str]] = []
    win._timer.timeout.connect(
        lambda: ticks.append((time.time(), win._lbl_timer.text()))
    )
    loop = QEventLoop()
    QTimer.singleShot(2100, loop.quit)
    loop.exec()
    assert len(ticks) >= 2
    for at, shown in ticks:
        assert at % 1 < 0.2, f"a tick at .{int(at % 1 * 1000):03d}"
        assert shown == format_time(int(at * 1000), accuracy=0)
