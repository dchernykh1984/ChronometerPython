"""A beam at the start: its breaks stamp group starts instead of rider cutoffs.

The first break after a group is chosen is its start, put in the group's time field
for the judge to see and Save; the breaks of its riders after it are no start, until
Save group. Every break is in the beam file all the same.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from app import sources_config as sources
from app.connector_protocol import Break
from app.models import format_time

T0 = 1_761_725_400_123


def _said(win) -> list[str]:
    return [win._log.item(i).text() for i in range(win._log.count())]


def _group_starts(win, group: str = "M40") -> None:
    win._combo_source.setCurrentIndex(win._combo_source.findData("beam"))
    win._combo_beam_records.setCurrentIndex(win._combo_beam_records.findData("groups"))
    win._combo_group.addItem(group)
    win._combo_group.setCurrentText(group)


def test_a_beam_records_rider_cutoffs_until_told_otherwise_and_the_choice_is_kept(
    win, monkeypatch
):
    saved: list[dict[str, str]] = []
    monkeypatch.setattr(
        "app.main_window.save_sources", lambda cfg, *a: saved.append(dict(cfg)) or True
    )
    assert sources.DEFAULTS["beam_records"] == "riders"
    assert win._beam_records() == "riders"
    _group_starts(win)
    assert saved[-1]["beam_records"] == "groups"


def test_the_first_break_after_a_group_is_chosen_is_its_start(win, tmp_path):
    _group_starts(win)
    win._on_source_event(Break(1, T0))
    assert win._edit_group_time.text() == format_time(T0)
    assert all(not e.text() for e in win._time_edits)  # no rider's crossing
    assert (
        _said(win)[-1]
        == f"group M40 started by the beam at {format_time(T0)}: Save group"
    )
    beam = (tmp_path / "results.beam_breaks.txt").read_text(encoding="utf-8")
    assert beam == f"1#{format_time(T0)}##\n"


def test_its_riders_breaks_are_no_start_until_save_group(win, tmp_path):
    _group_starts(win)
    win._on_source_event(Break(1, T0))
    win._on_source_event(Break(2, T0 + 1_500))  # the group's riders, crossing after
    assert win._edit_group_time.text() == format_time(T0)
    win._on_save_group()
    groups = (tmp_path / "groups.txt").read_text(encoding="utf-8")
    assert groups == f"M40#{format_time(T0)}#\n"
    _group_starts(win, "W30")
    win._on_source_event(Break(3, T0 + 60_000))  # the next group's first rider
    assert win._edit_group_time.text() == format_time(T0 + 60_000)
    beam = (tmp_path / "results.beam_breaks.txt").read_text(encoding="utf-8")
    assert len(beam.splitlines()) == 3  # every break kept


def test_the_judges_own_start_is_not_replaced_by_a_break(win):
    """Start pressed by hand, or the time typed: the judge's, until Save group."""
    _group_starts(win)
    win._on_start_group()
    by_hand = win._edit_group_time.text()
    win._on_source_event(Break(1, T0))
    assert win._edit_group_time.text() == by_hand
    win._on_save_group()
    _group_starts(win, "W30")
    win._edit_group_time.clear()
    QTest.keyClicks(win._edit_group_time, "1 12:00:00.000")
    win._on_source_event(Break(2, T0 + 60_000))
    assert win._edit_group_time.text() == "1 12:00:00.000"


def test_choosing_group_starts_again_makes_the_beam_wait_for_a_start_anew(win):
    _group_starts(win)
    win._on_source_event(Break(1, T0))  # taken: the next waits for Save group
    riders = win._combo_beam_records.findData("riders")
    win._combo_beam_records.setCurrentIndex(riders)
    win._combo_beam_records.setCurrentIndex(win._combo_beam_records.findData("groups"))
    win._on_source_event(Break(2, T0 + 9_000))
    assert win._edit_group_time.text() == format_time(T0 + 9_000)


def test_a_break_long_after_a_start_not_saved_is_said_once_as_likely_a_group(win):
    """Save group forgotten: the next group's start is no start, as chosen, but the
    judge is told, once, a minute on; riders of the group crossing just after are not
    said at all."""
    _group_starts(win)
    win._on_source_event(Break(1, T0))
    count = win._log.count()
    win._on_source_event(Break(2, T0 + 20_000))  # the group's riders
    assert win._log.count() == count  # nothing said for them
    win._on_source_event(Break(3, T0 + 90_000))  # the next group, Save forgotten
    assert "is not saved yet; Save group" in _said(win)[-1]
    win._on_source_event(Break(4, T0 + 95_000))
    assert win._log.count() == count + 1  # said once
    assert win._edit_group_time.text() == format_time(T0)  # the start kept


def _clock_at(win, ms: int) -> None:
    """The window's clock reads ``ms`` now; a break keeps its own time."""
    win._device_clock.system = lambda: ms / 1000


def _press_start(win) -> None:
    win._btn_start_group.click()


def _type_a_start(win) -> None:
    win._edit_group_time.clear()
    QTest.keyClicks(win._edit_group_time, "1 12:00:00.000")


@pytest.mark.parametrize("by_hand", [_press_start, _type_a_start])
def test_a_riders_break_just_after_a_start_given_by_hand_is_not_said(win, by_hand):
    """The minute counts from the judge's own start too, not from a beam start that
    never came."""
    _group_starts(win)
    _clock_at(win, T0)
    by_hand(win)
    count = win._log.count()
    win._on_source_event(Break(1, T0 + 3_000))  # the group's first rider
    assert win._log.count() == count  # nothing said for it
    win._on_source_event(Break(2, T0 + 90_000))  # the next group, Save forgotten
    assert "is not saved yet; Save group" in _said(win)[-1]


@pytest.mark.parametrize("by_hand", [_press_start, _type_a_start])
def test_a_group_said_once_leaves_the_next_started_by_hand_to_be_said(win, by_hand):
    """A group said once leaves the next one, started by hand, to be said again."""
    win._start_upload = Mock()  # Save group uploads; the network is not tested here
    _group_starts(win)
    win._on_source_event(Break(1, T0))  # the beam's start
    win._on_source_event(Break(2, T0 + 90_000))  # Save group forgotten: said
    assert "is not saved yet; Save group" in _said(win)[-1]
    win._on_save_group()
    _group_starts(win, "W30")
    _clock_at(win, T0 + 120_000)
    by_hand(win)
    count = win._log.count()
    win._on_source_event(Break(3, T0 + 123_000))  # its first rider
    assert win._log.count() == count
    win._on_source_event(Break(4, T0 + 200_000))  # Save group forgotten again
    assert "is not saved yet; Save group" in _said(win)[-1]
    assert win._log.count() == count + 1


def test_a_field_emptied_by_hand_starts_no_minute(win):
    """An emptied field holds no start: the next group's break, its start missed, is
    named at once with its time, the minute counted from the last start."""
    win._start_upload = Mock()  # Save group uploads; the network is not tested here
    _group_starts(win)
    win._on_source_event(Break(1, T0))  # M40 started by the beam
    win._on_save_group()
    _group_starts(win, "W30")
    _clock_at(win, T0 + 170_000)
    win._edit_group_time.selectAll()
    QTest.keyClick(win._edit_group_time, Qt.Key.Key_Backspace)
    assert win._edit_group_time.text() == ""
    win._on_source_event(Break(2, T0 + 180_000))  # W30's start, 10 s on
    assert _said(win)[-1].startswith(
        f"beam break {format_time(T0 + 180_000)} is no start: the start in the group's"
    )


def test_a_field_emptied_key_by_key_takes_its_typing_back(win):
    """Every Backspace but the last leaves text, a start typed; the last one empties the
    field and puts the minute back as it was before the typing."""
    win._start_upload = Mock()  # Save group uploads; the network is not tested here
    _group_starts(win)
    win._on_source_event(Break(1, T0))  # M40 started by the beam
    win._on_save_group()
    _group_starts(win, "W30")
    _clock_at(win, T0 + 170_000)
    win._edit_group_time.end(False)
    for _ in win._edit_group_time.text():
        QTest.keyClick(win._edit_group_time, Qt.Key.Key_Backspace)
    assert win._edit_group_time.text() == ""
    win._on_source_event(Break(2, T0 + 180_000))  # W30's start, 10 s on
    assert _said(win)[-1].startswith(
        f"beam break {format_time(T0 + 180_000)} is no start: the start in the group's"
    )


def _typed(win, at_ms: int) -> None:
    _clock_at(win, at_ms)
    win._edit_group_time.clear()
    QTest.keyClicks(win._edit_group_time, "1 12:00:00.000")


def _emptied(win) -> None:
    win._edit_group_time.selectAll()
    QTest.keyClick(win._edit_group_time, Qt.Key.Key_Backspace)


def _saved_then_emptied(win) -> int:
    """M40's time typed and saved; W30's field emptied 10 s on."""
    _group_starts(win)
    _typed(win, T0)
    win._on_save_group()
    _group_starts(win, "W30")
    _clock_at(win, T0 + 10_000)
    _emptied(win)
    return T0 + 20_000


def _started_then_emptied(win) -> int:
    """A time typed, then Start 5 s on, then the field emptied."""
    _group_starts(win)
    _typed(win, T0)
    _clock_at(win, T0 + 5_000)
    win._btn_start_group.click()
    _clock_at(win, T0 + 8_000)
    _emptied(win)
    return T0 + 12_000


def _beam_started_then_emptied(win) -> int:
    """A time typed while the beam records riders; then Group starts, the beam starting
    M40 5 s on, and the field emptied."""
    win._combo_source.setCurrentIndex(win._combo_source.findData("beam"))
    win._combo_group.addItem("M40")
    win._combo_group.setCurrentText("M40")
    _typed(win, T0)
    win._combo_beam_records.setCurrentIndex(win._combo_beam_records.findData("groups"))
    win._on_source_event(Break(1, T0 + 5_000))
    _emptied(win)
    return T0 + 15_000


@pytest.mark.parametrize(
    "newer_start",
    [_saved_then_emptied, _started_then_emptied, _beam_started_then_emptied],
)
def test_a_field_emptied_after_a_newer_start_takes_back_no_more_than_its_own_typing(
    win, newer_start
):
    """Save group, Start and a beam start forget the minute a typing before them
    remembered: emptied after them, the field leaves the newer start's minute."""
    win._start_upload = Mock()  # Save group uploads; the network is not tested here
    inside_its_minute = newer_start(win)
    count = win._log.count()
    win._on_source_event(Break(9, inside_its_minute))
    assert win._log.count() == count


def test_a_break_with_no_group_chosen_starts_none_and_says_so(win):
    win._combo_beam_records.setCurrentIndex(win._combo_beam_records.findData("groups"))
    win._combo_group.setCurrentText("")
    before = win._edit_group_time.text()
    win._on_source_event(Break(1, T0))
    assert win._edit_group_time.text() == before
    assert "starts no group: choose the group first" in _said(win)[-1]


def test_what_a_break_records_cannot_change_while_the_beam_runs(win):
    win._combo_source.setCurrentIndex(win._combo_source.findData("beam"))
    assert win._combo_beam_records.isEnabled()
    win._lock_source_choice(True)  # as a started source does
    assert not win._combo_beam_records.isEnabled()
    win._lock_source_choice(False)
    assert win._combo_beam_records.isEnabled()
    win._combo_source.setCurrentIndex(win._combo_source.findData("hand"))
    assert not win._combo_beam_records.isEnabled()  # by hand there is no beam


def test_a_hand_edited_sources_file_with_an_unknown_choice_records_riders(tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text("source=beam\nbeam_records=laps\n", encoding="utf-8")
    assert sources.load_sources(str(path))["beam_records"] == "riders"
