"""Qt-level tests for the group start section of MainWindow.

Groups often set off together, so saving one must not force the referee to type the
same start time back in for the next one. main_window is excluded from coverage, so
this is what guards the behaviour.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

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


def test_saving_without_a_time_does_nothing(win):
    _set_groups(win, "GroupA")
    win._combo_group.setCurrentText("GroupA")
    win._edit_group_time.clear()
    win._on_save_group()
    win._start_upload.assert_not_called()
    assert _group_lines(win) == []
