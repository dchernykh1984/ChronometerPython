"""Hand timing backs the log and the slots up at once, whatever key or button did it."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from app import main_window as mw


def _backups(win, monkeypatch):
    found = []
    monkeypatch.setattr(mw, "save_backup", lambda **k: found.append(k) or True)
    win._chk_disable_backup.setChecked(False)
    return found


def _enter(win, widget, modifiers=Qt.KeyboardModifier.NoModifier):
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, modifiers)
    assert win.eventFilter(widget, event)


def test_a_dsq_is_backed_up_at_once(win, monkeypatch):
    backups = _backups(win, monkeypatch)
    win._edit_dsq.setText("7")
    win._on_dsq()
    (backup,) = backups
    assert backup["log_items"][-1].startswith("7#")
    assert not win._backup_timer.isActive()


def test_ctrl_enter_in_next_is_backed_up_at_once(win, monkeypatch):
    backups = _backups(win, monkeypatch)
    win._next_number.setText("9")
    _enter(win, win._next_number, Qt.KeyboardModifier.ControlModifier)
    assert len(backups) == 1


def test_enter_for_a_second_judge_is_backed_up_once_it_writes_slot_1(win, monkeypatch):
    backups = _backups(win, monkeypatch)
    win._chk_second_user.setChecked(True)
    win._number_edits[0].setText("12")
    _enter(win, win._number_edits[0])  # slot 1 has no time: nothing moves
    assert backups == []
    win._time_edits[0].setText("1 10:0:0.000#finish")
    win._focused_slot = 1
    _enter(win, win._number_edits[1])  # slot 1 goes to the results file
    assert len(backups) == 1


def test_empty_all_backs_the_slots_up_before_it_clears_them(win, monkeypatch):
    backups = _backups(win, monkeypatch)
    monkeypatch.setattr(
        mw.QMessageBox, "question", lambda *a, **k: mw.QMessageBox.StandardButton.Yes
    )
    win._number_edits[0].setText("12")
    win._time_edits[0].setText("1 10:0:0.000#finish")  # stamped, not yet saved
    win._on_empty_all()
    (backup,) = backups
    assert backup["slots"][0] == ("12", "1 10:0:0.000#finish")
    assert not win._number_edits[0].text()
