"""Chip reads in the window: raw file first, crossings by pass, never a dialog."""

from __future__ import annotations

import json
import time

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
    assert win._chip_state_timer.isActive()  # within a second
    win._save_chip_state()  # the timer's tick
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
    win._save_chip_state()  # within its second
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
    assert win._unknown_timer.isActive()
    win._show_unknown()  # what the timer does half a second later
    assert win._list_unknown.count() == 1
    assert win._list_unknown.item(0).text().startswith("D: 2 reads")
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


def test_waiting_crossings_stay_out_of_another_results_file(win, chips_on, monkeypatch):
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: pytest.fail("dialog"))
    blocker = chips_on / "blocker"
    blocker.write_text("x", encoding="utf-8")
    first = blocker / "results.txt"
    win._edit_results_file.setText(str(first))
    win._on_source_event(Read("A", T0))
    win._edit_results_file.setText(str(chips_on / "other.txt"))
    win._retry_unwritten()  # the timer's tick, or a reload of the start protocol
    win._reload_chip_map()
    assert not (chips_on / "other.txt").exists()
    blocker.unlink()
    blocker.mkdir()
    win._edit_results_file.setText(str(first))
    win._retry_unwritten()
    assert first.read_text(encoding="utf-8") == f"15#{format_time(T0)}#nextLap#\n"


def test_a_lost_chip_state_writes_no_crossing_twice(win, chips_on):
    for offset in (0, 9000):
        win._on_source_event(Read("A", T0 + offset))
    win._save_chip_state()
    (chips_on / "results.chip_state.json").unlink()
    win._chip_timing = None  # as at a start after the state was lost
    win._timing()
    written = [
        f"15#{format_time(T0)}#nextLap#",
        f"15#{format_time(T0 + 9000)}#nextLap#",
    ]
    assert _results(chips_on) == written
    log = [win._log.item(i).text() for i in range(win._log.count())]
    assert any(line.startswith("chip state lost:") for line in log)
    win._on_source_event(Read("B", T0 + 10_000))  # still the 9 s pass
    assert _results(chips_on) == written


def test_a_burst_of_unknown_reads_refreshes_the_list_once(win, chips_on):
    for i in range(300):
        win._on_source_event(Read("D", T0 + i))
    assert win._list_unknown.count() == 0  # not rebuilt read by read
    assert win._unknown_timer.isActive()
    win._show_unknown()
    assert win._list_unknown.item(0).text().startswith("D: 300 reads")


def test_a_read_with_no_results_file_is_logged_not_timed(win, chips_on):
    win._edit_results_file.setText("")
    win._on_source_event(Read("A", T0))
    last = win._log.item(win._log.count() - 1).text()
    assert last == f"chip read A {format_time(T0)} not timed: no results file"
    assert win._chip_timing is None or not win._chip_timing.unwritten


def test_a_crossing_written_on_a_retry_is_saved_within_a_second(
    win, chips_on, monkeypatch
):
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: pytest.fail("dialog"))
    blocker = chips_on / "blocker"
    blocker.write_text("x", encoding="utf-8")
    win._edit_results_file.setText(str(blocker / "results.txt"))
    win._on_source_event(Read("A", T0))
    blocker.unlink()
    blocker.mkdir()
    win._retry_unwritten()  # the 1 s timer's tick, with no read after it
    assert win._chip_state_timer.isActive()
    win._save_chip_state()
    state = json.loads((blocker / "results.chip_state.json").read_text("utf-8"))
    assert state["unwritten"] == []


def test_a_chip_state_left_from_another_race_is_not_used(win, chips_on):
    stale = {
        "version": 2,
        "processed_lines": 500,
        "passes": {"15": [[0, 0]]},
        "pending": {},
        "unwritten": ["15#1 10:0:0.000#nextLap#"],
    }
    (chips_on / "results.chip_state.json").write_text(json.dumps(stale), "utf-8")
    win._chip_timing = None  # a start, with only the state left of the last race
    win._timing()
    assert _results(chips_on) == []
    log = [win._log.item(i).text() for i in range(win._log.count())]
    assert any(line.startswith("chip state belongs to another") for line in log)
    win._on_source_event(Read("A", T0))
    assert _results(chips_on) == [f"15#{format_time(T0)}#nextLap#"]


def test_a_crossing_written_just_before_a_crash_is_not_written_again(win, chips_on):
    win._on_source_event(Read("A", T0))
    win._save_chip_state()  # within its second
    # The next read was kept and its crossing written, and the program died before
    # it saved the chip state.
    with (chips_on / "results.chip_reads.txt").open("a", encoding="utf-8") as f:
        f.write(f"A#{format_time(T0 + 9000)}#####\n")
    with (chips_on / "results.txt").open("a", encoding="utf-8") as f:
        f.write(f"15#{format_time(T0 + 9000)}#finish#\n")  # the mode changed since
    win._chip_timing = None
    win._timing()
    assert _results(chips_on) == [
        f"15#{format_time(T0)}#nextLap#",
        f"15#{format_time(T0 + 9000)}#finish#",
    ]


def test_a_waiting_crossing_already_in_the_results_file_is_dropped(win, chips_on):
    line = f"15#{format_time(T0)}#nextLap#"
    saved = {"version": 2, "processed_lines": 0, "passes": {}, "pending": {}}
    state = chips_on / "results.chip_state.json"
    state.write_text(json.dumps({**saved, "unwritten": [line]}), "utf-8")
    (chips_on / "results.txt").write_text(line + "\n", "utf-8")  # then the crash
    win._chip_timing = None
    win._timing()
    assert _results(chips_on) == [line]
    assert json.loads(state.read_text("utf-8"))["unwritten"] == []


def test_a_chip_state_that_could_not_be_saved_is_saved_later(
    win, chips_on, monkeypatch
):
    win._on_source_event(Read("A", T0))
    real, fail = mw.save_chip_state, [True]
    monkeypatch.setattr(mw, "save_chip_state", lambda *a: not fail[0] and real(*a))
    win._chip_state_dirty = True  # a change waiting for the save timer
    win._save_chip_state()  # its tick, while the disk refuses
    assert win._chip_state_dirty
    assert win._chip_state_timer.isActive()
    fail[0] = False
    win._save_chip_state()
    assert not win._chip_state_dirty


def test_steady_reads_do_not_put_off_the_state_save(win, chips_on):
    win._on_source_event(Read("D", T0))
    time.sleep(0.3)
    win._on_source_event(Read("D", T0 + 300))
    assert win._chip_state_timer.remainingTime() < 900


def test_waiting_crossings_are_counted_on_the_source_state_line(
    win, chips_on, monkeypatch
):
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: pytest.fail("dialog"))
    blocker = chips_on / "blocker"
    blocker.write_text("x", encoding="utf-8")
    win._edit_results_file.setText(str(blocker / "results.txt"))
    win._on_source_state("running")
    win._on_source_event(Read("A", T0))
    assert win._lbl_source_state.text() == "running; 1 chip crossing(s) waiting"
    win._edit_results_file.setText(str(chips_on / "other.txt"))
    win._retry_unwritten()  # the timer's tick after the switch
    assert win._lbl_source_state.text() == "running"
    assert win._lbl_unwritten.text() == ""
    assert win._unwritten_timer.isActive()  # for when that file is back


def test_a_burst_of_crossings_saves_the_state_once(win, chips_on, monkeypatch):
    saved = []
    real = mw.save_chip_state
    monkeypatch.setattr(mw, "save_chip_state", lambda *a: saved.append(1) or real(*a))
    for offset in range(0, 60_000, 6000):  # ten passes, ten crossings
        win._on_source_event(Read("A", T0 + offset))
    assert len(_results(chips_on)) == 10
    assert saved == []  # none on the window's thread meanwhile
    win._save_chip_state()  # the timer's one tick
    assert saved == [1]


def test_a_state_left_unsaved_on_a_switch_says_how_it_comes_back(
    win, chips_on, monkeypatch
):
    win._on_source_event(Read("A", T0))  # results.txt's state, not saved yet
    real = mw.save_chip_state
    monkeypatch.setattr(
        mw,
        "save_chip_state",
        lambda path, timing: "other" in path and real(path, timing),
    )
    win._edit_results_file.setText(str(chips_on / "other.txt"))
    win._on_source_event(Read("C", T0 + 1000))  # the state moves to other.txt
    log = [win._log.item(i).text() for i in range(win._log.count())]
    assert any("results.txt not saved; its latest reads come back" in x for x in log)
    assert not any(x.startswith("chip state not saved; trying again") for x in log)


def test_a_read_cut_by_a_crash_never_takes_the_next_one_with_it(win, chips_on):
    win._on_source_event(Read("A", T0))
    win._save_chip_state()
    raw = chips_on / "results.chip_reads.txt"
    with raw.open("a", encoding="utf-8") as f:
        f.write("B#20390 1")  # the crash came halfway through this read
    win._chip_timing = None  # the start after the crash
    win._timing()
    win._on_source_event(Read("C", T0 + 1000))
    lines = raw.read_text(encoding="utf-8").splitlines()
    assert lines[-1].startswith("C#")
    assert win._chip_timing.processed_lines == len(lines)
