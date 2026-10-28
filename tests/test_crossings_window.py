"""The Crossings tab: the results file, corrected by hand with a backup each time."""

from __future__ import annotations

import pytest

from app import main_window as mw
from app import results_file as rf

LINES = ["15#1 10:0:0.000#nextLap#", "16#1 10:0:1.000#nextLap#"]


@pytest.fixture
def results(win, tmp_path, monkeypatch):
    """The window's results file with two crossings; backups go to tmp_path/temp."""
    monkeypatch.setattr(rf, "app_path", lambda *parts: tmp_path.joinpath(*parts))
    path = tmp_path / "results.txt"
    path.write_text("".join(line + "\n" for line in LINES), encoding="utf-8")
    win._refresh_crossings()
    return path


def _backups(tmp_path):
    return sorted((tmp_path / "temp").glob("results*.txt"))


def test_the_tab_lists_the_results_file(win, results):
    assert [
        win._crossings.item(i).text() for i in range(win._crossings.count())
    ] == LINES


def test_adding_a_crossing_appends_it_after_a_backup(
    win, results, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        win, "_ask_crossing", lambda *a: ("23", "1 10:1:2.300", "nextLap")
    )
    win._on_add_crossing()
    assert results.read_text(encoding="utf-8").splitlines() == [
        *LINES,
        "23#1 10:1:2.300#nextLap#",
    ]
    assert _backups(tmp_path)[0].read_text(encoding="utf-8").splitlines() == LINES
    assert win._crossings.count() == 3
    assert (
        "added 23#1 10:1:2.300#nextLap#" in win._log.item(win._log.count() - 1).text()
    )
    assert win._finish_upload_timer.isActive()


def test_editing_changes_that_line_in_place(win, results, monkeypatch):
    seen = []

    def ask(number, time_str, action):
        seen.append((number, time_str, action))
        return ("51", time_str, action)

    monkeypatch.setattr(win, "_ask_crossing", ask)
    win._crossings.setCurrentRow(0)
    win._on_edit_crossing()
    assert seen == [("15", "1 10:0:0.000", "nextLap")]
    assert results.read_text(encoding="utf-8").splitlines() == [
        "51#1 10:0:0.000#nextLap#",
        LINES[1],
    ]


def test_deleting_asks_first_and_keeps_a_backup(win, results, tmp_path, monkeypatch):
    answer = [mw.QMessageBox.StandardButton.No]
    monkeypatch.setattr(mw.QMessageBox, "question", lambda *a: answer[0])
    win._crossings.setCurrentRow(1)
    win._on_delete_crossing()
    assert results.read_text(encoding="utf-8").splitlines() == LINES
    answer[0] = mw.QMessageBox.StandardButton.Yes
    win._on_delete_crossing()
    assert results.read_text(encoding="utf-8").splitlines() == [LINES[0]]
    assert _backups(tmp_path)[-1].read_text(encoding="utf-8").splitlines() == LINES


def test_a_change_without_a_backup_is_refused(win, results, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    monkeypatch.setattr(win, "_ask_crossing", lambda *a: ("23", "1 10:1:2", "finish"))

    def refuse(self, data):
        raise OSError("disk full")

    monkeypatch.setattr(rf.Path, "write_bytes", refuse)
    win._on_add_crossing()
    assert results.read_text(encoding="utf-8").splitlines() == LINES
    assert "disk full" in warnings[0]


def test_a_line_that_changed_meanwhile_is_not_edited(win, results, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    monkeypatch.setattr(win, "_ask_crossing", lambda *a: ("99", "1 10:0:0", "finish"))
    win._crossings.setCurrentRow(0)
    results.write_text("77#1 9:0:0.000#nextLap#\n", encoding="utf-8")
    win._on_edit_crossing()
    assert results.read_text(encoding="utf-8") == "77#1 9:0:0.000#nextLap#\n"
    assert "changed meanwhile" in warnings[0]


def test_without_a_results_file_nothing_is_asked(win, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    monkeypatch.setattr(win, "_ask_crossing", lambda *a: pytest.fail("asked"))
    win._edit_results_file.setText("")
    win._on_add_crossing()
    assert "not configured" in warnings[0]


def test_a_saved_slot_shows_up_in_the_tab(win, results):
    win._number_edits[0].setText("42")
    win._time_edits[0].setText("1 10:5:0.000#finish")
    win._on_save(0)
    assert (
        win._crossings.item(win._crossings.count() - 1).text()
        == "42#1 10:5:0.000#finish#"
    )


def test_crossing_counts_follow_the_results_file(win, results, monkeypatch):
    win._number_edits[0].setText("15")
    win._update_crosses()
    assert win._cross_labels[0].text() == "2"  # the file's line and the slot
    monkeypatch.setattr(
        mw.QMessageBox, "question", lambda *a: mw.QMessageBox.StandardButton.Yes
    )
    win._crossings.setCurrentRow(0)
    win._on_delete_crossing()
    assert win._cross_labels[0].text() == "1"


def test_counts_include_crossings_written_before_a_restart(win, results):
    # The action log of a new window is empty; the file is not.
    assert win._log.count() == 0
    win._number_edits[1].setText("16")
    win._update_crosses()
    assert win._cross_labels[1].text() == "2"


DEVICE = "22#1 10:0:5.000#nextLap#"


def _a_device_writes(results) -> None:
    """A chip crossing appended while a dialog of the tab is open."""
    with results.open("a", encoding="utf-8") as f:
        f.write(DEVICE + "\n")


@pytest.mark.parametrize("change", ["add", "edit"])
def test_a_crossing_written_while_the_dialog_is_open_is_kept(
    win, results, monkeypatch, change
):
    def ask(*a):
        _a_device_writes(results)
        return ("51", "1 10:0:0.000", "nextLap")

    monkeypatch.setattr(win, "_ask_crossing", ask)
    win._crossings.setCurrentRow(0)
    getattr(win, f"_on_{change}_crossing")()
    lines = results.read_text(encoding="utf-8").splitlines()
    assert DEVICE in lines
    assert "51#1 10:0:0.000#nextLap#" in lines


def test_a_crossing_written_while_a_delete_is_asked_is_kept(win, results, monkeypatch):
    def yes(*a):
        _a_device_writes(results)
        return mw.QMessageBox.StandardButton.Yes

    monkeypatch.setattr(mw.QMessageBox, "question", yes)
    win._crossings.setCurrentRow(1)
    win._on_delete_crossing()
    assert results.read_text(encoding="utf-8").splitlines() == [LINES[0], DEVICE]


def test_a_line_gone_while_the_dialog_is_open_is_not_edited(win, results, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))

    def ask(*a):
        results.write_text(LINES[1] + "\n", encoding="utf-8")
        return ("51", "1 10:0:0.000", "nextLap")

    monkeypatch.setattr(win, "_ask_crossing", ask)
    win._crossings.setCurrentRow(0)
    win._on_edit_crossing()
    assert results.read_text(encoding="utf-8").splitlines() == [LINES[1]]
    assert "changed meanwhile" in warnings[0]
