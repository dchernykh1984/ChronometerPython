"""Chip reads in the window: raw file first, crossings by pass, never a dialog."""

from __future__ import annotations

import json

import pytest

from app import main_window as mw
from app.connector_protocol import Read
from app.models import format_time, parse_time

T0 = 1_761_725_400_000


@pytest.fixture
def chips_on(win, tmp_path):
    """A start protocol binding A and B to bib 15 and C to bib 22."""
    start = tmp_path / "start.txt"
    start.write_text(
        "15#Rider#M40#3#1#1990#T#C##0 00:00:00.000#r1#A,B#\n"
        "22#Other#M40#3#1#1991#T#C##0 00:00:00.000#r2#C#\n",
        encoding="utf-8",
    )
    win._edit_start_protocol.setText(str(start))
    win._on_start_protocol_path()
    return tmp_path


def _results(tmp_path) -> list[str]:
    path = tmp_path / "results.txt"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_reads_of_one_pass_make_one_crossing_at_the_first_read(win, chips_on):
    for chip, offset in (("A", 0), ("B", 300), ("a", 2000), ("A", 9000)):
        win._on_source_event(Read(chip, T0 + offset, "dev", "1", -58.5, "r1"))
    assert _results(chips_on) == [
        f"15#{format_time(T0)}#nextLap#",
        f"15#{format_time(T0 + 9000)}#nextLap#",
    ]
    raw = (chips_on / "results.chip_reads.txt").read_text(encoding="utf-8").splitlines()
    assert raw[0] == f"A#{format_time(T0)}#dev#1#-58.5#r1#"
    assert len(raw) == 4
    assert win._crossings.count() == 2


def test_finish_mode_gives_chip_crossings_the_finish_action(win, chips_on):
    win._chk_finish.setChecked(True)
    win._on_source_event(Read("C", T0))
    assert _results(chips_on) == [f"22#{format_time(T0)}#finish#"]


def test_a_read_without_a_usable_id_is_logged_and_dropped(win, chips_on):
    win._on_source_event(Read("--", T0))
    assert not (chips_on / "results.chip_reads.txt").exists()
    assert "without a usable id" in win._log.item(win._log.count() - 1).text()


def test_the_chip_state_is_saved_next_to_the_results_file(win, chips_on):
    win._on_source_event(Read("A", T0))
    state = json.loads(
        (chips_on / "results.chip_state.json").read_text(encoding="utf-8")
    )
    assert state["processed_lines"] == 1
    assert list(state["passes"]) == ["15"]


def test_a_crossing_waits_while_the_results_file_cannot_be_written(
    win, chips_on, monkeypatch
):
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: pytest.fail("dialog"))
    blocker = chips_on / "blocker"
    blocker.write_text("x", encoding="utf-8")
    win._edit_results_file.setText(str(blocker / "results.txt"))
    win._on_source_event(Read("A", T0))
    assert win._chip_timing.unwritten == [f"15#{format_time(T0)}#nextLap#"]
    assert "1 chip crossing(s) wait" in win._lbl_unwritten.text()
    assert win._unwritten_timer.isActive()
    blocker.unlink()
    blocker.mkdir()
    win._retry_unwritten()
    assert (blocker / "results.txt").read_text(encoding="utf-8") == (
        f"15#{format_time(T0)}#nextLap#\n"
    )
    assert win._lbl_unwritten.text() == ""
    assert not win._unwritten_timer.isActive()


def test_reads_a_crash_left_unprocessed_are_replayed(win, chips_on):
    win._on_source_event(Read("A", T0))
    # The raw file got two more reads, and the program died before handling them.
    with (chips_on / "results.chip_reads.txt").open("a", encoding="utf-8") as f:
        f.write(f"A#{format_time(T0 + 1000)}#####\n")
        f.write(f"C#{format_time(T0 + 2000)}#####\n")
    win._chip_timing = None
    win._timing()
    assert _results(chips_on) == [
        f"15#{format_time(T0)}#nextLap#",
        f"22#{format_time(T0 + 2000)}#nextLap#",
    ]


def test_a_changed_dead_time_applies_to_reads_from_then_on(win, chips_on):
    win._on_source_event(Read("A", T0))
    win._spin_dead_time.setValue(1)
    assert win._sources["dead_time_s"] == "1"
    win._on_source_event(Read("A", T0 + 3000))
    assert len(_results(chips_on)) == 2


def test_a_burst_of_reads_is_handled_in_order(win, chips_on):
    # 10,000 reads: three riders, a pass every 10 s, many reads per pass.
    for i in range(10_000):
        chip = "ABC"[i % 3]
        win._on_source_event(Read(chip, T0 + (i // 300) * 10_000 + i))
    raw = (chips_on / "results.chip_reads.txt").read_text(encoding="utf-8").splitlines()
    assert len(raw) == 10_000
    lines = _results(chips_on)
    assert len(lines) == 2 * 34  # bibs 15 and 22, one crossing per 10 s pass
    times = [parse_time(line.split("#")[1]) for line in lines]
    assert times == sorted(times)


def test_an_unknown_chip_is_listed_and_timed_once_the_map_binds_it(win, chips_on):
    win._on_source_event(Read("D", T0))
    win._on_source_event(Read("D", T0 + 20_000))
    assert win._list_unknown.count() == 1
    assert win._list_unknown.item(0).text().startswith("D: 2 read(s)")
    assert _results(chips_on) == []
    with (chips_on / "start.txt").open("a", encoding="utf-8") as f:
        f.write("31#Late#M40#3#1#1992#T#C##0 00:00:00.000#r3#D#\n")
    win._reload_chip_map()
    assert _results(chips_on) == [
        f"31#{format_time(T0)}#nextLap#",
        f"31#{format_time(T0 + 20_000)}#nextLap#",
    ]
    assert win._list_unknown.count() == 0


def test_the_chip_report_is_written_next_to_the_results_file(
    win, chips_on, monkeypatch
):
    told = []
    monkeypatch.setattr(mw.QMessageBox, "information", lambda *a: told.append(a[2]))
    for chip, offset in (("A", 0), ("B", 300), ("a", 2000), ("A", 9000)):
        win._on_source_event(Read(chip, T0 + offset))
    win._on_chip_report()
    report = (chips_on / "results.chip_report.txt").read_text(encoding="utf-8")
    assert "bib 15: chip A read in 2 of 2 crossings, 3 reads\n" in report
    assert "bib 15: chip B read in 1 of 2 crossings, 1 read\n" in report
    assert "bib 22: chip C\n" in report
    assert told and "results.chip_report.txt" in told[0]


def test_the_chip_report_needs_a_results_file(win, monkeypatch):
    warned = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warned.append(a[2]))
    win._edit_results_file.setText("")
    win._on_chip_report()
    assert warned == ["Choose the results file first."]


def test_a_chip_report_that_cannot_be_written_says_so(win, chips_on, monkeypatch):
    warned = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warned.append(a[2]))
    (chips_on / "results.chip_report.txt").mkdir()  # a folder where the file goes
    win._on_chip_report()
    assert warned and warned[0].startswith("Not written:")
