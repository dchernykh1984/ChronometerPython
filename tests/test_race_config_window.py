"""Qt-level tests for the race config: the groups and the two file paths a start reads.

"Save race config" keeps them in the default file, data/groupsList.txt, read at the
next start; "Load race config" only reads another file in. Closing with groups or
paths that differ from the file saved offers to save them first. main_window is
excluded from coverage, so these are what guard it.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QPushButton

from app import main_window as mw
from app.models import load_config, save_config

Buttons = mw.QMessageBox.StandardButton


def _said(win) -> list[str]:
    return [win._log.item(i).text() for i in range(win._log.count())]


def _closing(win, monkeypatch, answer) -> tuple[list[str], Mock]:
    """Close the window, the question answered with ``answer``: the titles asked."""
    asked: list[str] = []

    def question(_parent, title, *_rest):
        asked.append(title)
        return answer

    monkeypatch.setattr(mw.QMessageBox, "question", question)
    event = Mock()
    win.closeEvent(event)
    return asked, event


def test_save_race_config_keeps_the_groups_and_paths_for_the_next_start(win, tmp_path):
    win._combo_group.clear()
    win._combo_group.addItems(["M40", "W30"])
    finish = str(tmp_path / "race" / "finish.txt")
    win._edit_results_file.setText(finish)
    save = next(
        b for b in win.findChildren(QPushButton) if b.text() == "Save race config"
    )
    save.click()
    groups = str(tmp_path / "groups.txt")
    assert load_config(win._config_path) == (["M40", "W30"], finish, groups)
    assert _said(win)[-1] == f"race config saved: {win._config_path}"
    win._edit_results_file.clear()
    win._load_config(win._config_path)  # as the next start reads it
    assert win._race_config() == (["M40", "W30"], finish, groups)


def test_a_race_config_that_cannot_be_saved_is_said(win, monkeypatch):
    monkeypatch.setattr(mw, "save_config", lambda *a: False)
    assert not win._on_save_config()
    assert _said(win)[-1] == f"race config not saved: {win._config_path}"


def test_loading_a_race_config_leaves_the_default_one_as_it_was(
    win, tmp_path, monkeypatch
):
    assert win._on_save_config()
    default = Path(win._config_path).read_bytes()
    other = tmp_path / "race.txt"
    results, groups = str(tmp_path / "r.txt"), str(tmp_path / "g.txt")
    save_config(str(other), ["Open"], results, groups)
    monkeypatch.setattr(mw.QFileDialog, "getOpenFileName", lambda *a: (str(other), ""))
    win._on_load_config()
    assert win._race_config() == (["Open"], results, groups)
    assert Path(win._config_path).read_bytes() == default
    assert not win._race_config_saved()  # read in: not yet what the next start reads


def test_groups_from_the_site_are_saved_with_the_paths_as_before(win):
    win._on_groups(["A", "B"])
    assert win._race_config_saved()


def test_closing_with_the_race_config_saved_asks_only_whether_to_exit(win, monkeypatch):
    asked, event = _closing(win, monkeypatch, Buttons.Yes)
    assert asked == ["Warning"]
    event.accept.assert_called_once()


@pytest.mark.parametrize(
    ("answer", "closes", "saved"),
    [
        (Buttons.Save, True, True),
        (Buttons.Discard, True, False),
        (Buttons.Cancel, False, False),
    ],
    ids=["save", "discard", "cancel"],
)
def test_closing_with_the_race_config_not_saved_offers_to_save_it_first(
    win, tmp_path, monkeypatch, answer, closes, saved
):
    win._edit_results_file.setText(str(tmp_path / "another.txt"))
    asked, event = _closing(win, monkeypatch, answer)
    assert asked == ["Race config not saved"]
    assert (event.accept.called, event.ignore.called) == (closes, not closes)
    assert win._race_config_saved() is saved


def test_a_race_config_not_saved_at_exit_keeps_the_window_open(
    win, tmp_path, monkeypatch
):
    win._edit_results_file.setText(str(tmp_path / "another.txt"))
    monkeypatch.setattr(mw, "save_config", lambda *a: False)
    _asked, event = _closing(win, monkeypatch, Buttons.Save)
    event.ignore.assert_called_once()
    assert _said(win)[-1] == f"race config not saved: {win._config_path}"
