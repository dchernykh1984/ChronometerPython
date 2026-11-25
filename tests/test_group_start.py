"""Qt-level tests for the group start section of MainWindow.

Groups often set off together, so saving one must not force the referee to type the
same start time back in for the next one. main_window is excluded from coverage, so
this is what guards the behaviour.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from PySide6.QtTest import QTest

from app import main_window as mw


@pytest.fixture(autouse=True)
def _no_upload_threads(win):
    """Saving a group also uploads it; the network is not what these tests cover."""
    win._start_upload = Mock()


def _group_lines(win) -> list[str]:
    return [win._log.item(i).text() for i in range(win._log.count())]


def _set_groups(win, *names: str) -> None:
    """Replace whatever the window loaded from the real config with a known list."""
    win._combo_group.clear()
    win._combo_group.addItems(list(names))


def test_saving_a_group_keeps_the_start_time(win):
    _set_groups(win, "GroupA")
    win._combo_group.setCurrentText("GroupA")
    win._edit_group_time.setText("0 12:00:00.000")
    win._on_save_group()
    assert win._edit_group_time.text() == "0 12:00:00.000"


def test_two_groups_can_be_saved_with_one_start_time(win):
    # The reason the time is kept: a mass start covering several groups.
    _set_groups(win, "GroupA", "GroupB")
    win._edit_group_time.setText("0 12:00:00.000")
    for group in ("GroupA", "GroupB"):
        win._combo_group.setCurrentText(group)
        win._on_save_group()
    assert _group_lines(win) == [
        "GroupA#0 12:00:00.000#",
        "GroupB#0 12:00:00.000#",
    ]


def test_saving_a_group_still_clears_the_group_name(win):
    # Only the time is kept; the saved group leaves the dropdown as before.
    _set_groups(win, "GroupA", "GroupB")
    win._combo_group.setCurrentText("GroupA")
    win._edit_group_time.setText("0 12:00:00.000")
    win._on_save_group()
    assert win._combo_group.currentText() == ""
    items = [win._combo_group.itemText(i) for i in range(win._combo_group.count())]
    assert items == ["GroupB"]


def test_saving_a_typed_group_removes_that_group_from_the_list(win):
    # Typed, not picked: the combo's index stays on M40, the first one listed.
    _set_groups(win, "M40", "W30", "Juniors")
    win._combo_group.lineEdit().clear()
    QTest.keyClicks(win._combo_group.lineEdit(), "Juniors")
    win._edit_group_time.setText("0 10:00:00.000")
    win._on_save_group()
    assert _group_lines(win) == ["Juniors#0 10:00:00.000#"]
    items = [win._combo_group.itemText(i) for i in range(win._combo_group.count())]
    assert items == ["M40", "W30"]


def test_start_replaces_the_kept_time(win, monkeypatch):
    monkeypatch.setattr(mw, "get_current_time", lambda summer_time: "0 13:30:00.000")
    _set_groups(win, "GroupA")
    win._combo_group.setCurrentText("GroupA")
    win._edit_group_time.setText("0 12:00:00.000")
    win._on_save_group()
    win._on_start_group()
    assert win._edit_group_time.text() == "0 13:30:00.000"


def test_a_failed_write_keeps_the_time_too(win, monkeypatch):
    # The referee has to be able to retry after fixing the groups file path.
    monkeypatch.setattr(mw, "append_to_group_file", lambda *a, **k: False)
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a, **k: None)
    _set_groups(win, "GroupA")
    win._combo_group.setCurrentText("GroupA")
    win._edit_group_time.setText("0 12:00:00.000")
    win._on_save_group()
    assert win._edit_group_time.text() == "0 12:00:00.000"
    assert _group_lines(win) == []


def test_a_typed_start_that_is_no_time_is_refused_saying_why(
    win, monkeypatch, tmp_path
):
    """A letter O for a zero, refused as the Crossings tab refuses it: written, it would
    stop FinishProtocolGenerator's whole protocol."""
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    _set_groups(win, "J18")
    win._combo_group.setCurrentText("J18")
    win._edit_group_time.setText("11:1O:00")
    win._on_save_group()
    assert warnings == ["The time is not 'D H:M:S' or 'D H:M:S.mmm'."]
    assert not (tmp_path / "groups.txt").exists()
    win._start_upload.assert_not_called()
    assert win._combo_group.currentText() == "J18"  # to be saved once corrected


def test_a_start_pasted_with_its_line_break_is_saved_as_one_line(win, tmp_path):
    """An Excel cell pasted keeps its line break in the field: written as it is, the
    groups file would read back a stray '#' line, a group with no name."""
    _set_groups(win, "J18")
    win._combo_group.setCurrentText("J18")
    win._edit_group_time.setText("1 11:10:00\r\n")
    win._on_save_group()
    groups = (tmp_path / "groups.txt").read_text(encoding="utf-8")
    assert groups == "J18#1 11:10:00#\n"


def test_saving_without_a_time_does_nothing(win):
    _set_groups(win, "GroupA")
    win._combo_group.setCurrentText("GroupA")
    win._edit_group_time.clear()
    win._on_save_group()
    win._start_upload.assert_not_called()
    assert _group_lines(win) == []


def test_a_saved_group_is_backed_up_with_its_line(win, monkeypatch):
    backups = []
    monkeypatch.setattr(mw, "save_backup", lambda **k: backups.append(k) or True)
    win._chk_disable_backup.setChecked(False)
    _set_groups(win, "GroupA")
    win._combo_group.setCurrentText("GroupA")
    win._edit_group_time.setText("0 12:00:00.000")
    win._on_save_group()
    (backup,) = backups
    assert backup["log_items"][-1] == "GroupA#0 12:00:00.000#"
    assert backup["group_number"] == "GroupA"


def test_a_group_that_cannot_be_saved_is_backed_up(win, monkeypatch):
    backups = []
    monkeypatch.setattr(mw, "save_backup", lambda **k: backups.append(k) or True)
    monkeypatch.setattr(mw, "append_to_group_file", lambda *a: False)
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: None)
    win._chk_disable_backup.setChecked(False)
    _set_groups(win, "GroupA")
    win._combo_group.setCurrentText("GroupA")
    win._edit_group_time.setText("0 12:00:00.000")  # typed by hand
    win._on_save_group()
    (backup,) = backups
    assert (backup["group_number"], backup["group_time"]) == (
        "GroupA",
        "0 12:00:00.000",
    )


def test_a_start_time_typed_by_hand_is_backed_up(win, monkeypatch):
    backups = []
    monkeypatch.setattr(mw, "save_backup", lambda **k: backups.append(k) or True)
    win._chk_disable_backup.setChecked(False)
    assert not win._backup_timer.isActive()  # none for the window's own start value
    win._edit_group_time.setText("0 12:00:00.000")  # typed, not yet saved
    assert win._backup_timer.isActive()
    win._backup_timer.timeout.emit()  # 2 s on
    (backup,) = backups
    assert backup["group_time"] == "0 12:00:00.000"
