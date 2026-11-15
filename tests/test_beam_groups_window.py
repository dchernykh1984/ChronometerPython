"""A beam at the start: its breaks stamp group starts instead of rider cutoffs.

The first break after a group is chosen is its start, put in the group's time field
for the judge to see and Save; the breaks of its riders after it are no start, until
Save group. Every break is in the beam file all the same.
"""

from __future__ import annotations

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
