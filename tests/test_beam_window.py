"""Light beam breaks: each stamps the first empty slot and is kept in the beam file."""

from __future__ import annotations

from app import main_window as mw
from app.connector_protocol import Break
from app.device_files import append_record, side_file
from app.models import format_time, record_field

T0 = 1_761_725_400_123  # a break's time on the computer's clock


def test_a_break_stamps_slot_1_with_its_own_time(win, tmp_path):
    win._on_source_event(Break(1, T0, "812"))
    assert win._time_edits[0].text() == f"{format_time(T0)}#nextLap"
    beam = tmp_path / "results.beam_breaks.txt"
    assert beam.read_text(encoding="utf-8") == f"1#{format_time(T0)}#812#\n"


def test_breaks_fill_the_slots_in_turn(win):
    for seq in (1, 2, 3):
        win._on_source_event(Break(seq, T0 + seq))
    assert [e.text().split("#")[0] for e in win._time_edits[:3]] == [
        format_time(T0 + 1),
        format_time(T0 + 2),
        format_time(T0 + 3),
    ]


def test_with_all_slots_stamped_a_break_shifts_and_leaves_next_alone(win, tmp_path):
    for i in range(5):
        win._number_edits[i].setText(str(10 + i))
        win._time_edits[i].setText(f"1 10:0:{i}.000#nextLap")
    win._next_number.setText("4")  # the judge is typing
    win._on_source_event(Break(6, T0))
    results = (tmp_path / "results.txt").read_text(encoding="utf-8")
    assert results == "10#1 10:0:0.000#nextLap#\n"
    assert win._number_edits[4].text() == ""
    assert win._time_edits[4].text() == f"{format_time(T0)}#nextLap"
    assert win._next_number.text() == "4"


def test_a_write_a_break_causes_never_opens_a_dialog(win, monkeypatch):
    monkeypatch.setattr(
        mw.QMessageBox, "warning", lambda *a: (_ for _ in ()).throw(AssertionError)
    )
    monkeypatch.setattr(
        mw.QTimer, "singleShot", lambda *a: (_ for _ in ()).throw(AssertionError)
    )
    win._edit_results_file.setText("")
    for i in range(5):
        win._number_edits[i].setText(str(10 + i))
        win._time_edits[i].setText(f"1 10:0:{i}.000#nextLap")
    win._on_source_event(Break(6, T0))
    assert win._number_edits[0].text() == "10"  # nothing shifted, nothing lost
    log = [win._log.item(i).text() for i in range(win._log.count())]
    assert any(line.startswith("not written: 10#") for line in log)
    assert any("beam break not kept" in line for line in log)


def test_the_second_user_button_still_takes_next(win):
    for i in range(5):
        win._number_edits[i].setText(str(10 + i))
        win._time_edits[i].setText(f"1 10:0:{i}.000#nextLap")
    win._next_number.setText("4")
    win._on_finish_second_user()
    assert win._number_edits[4].text() == "4"
    assert win._next_number.text() == ""


def test_device_files_sit_next_to_the_results_file(tmp_path):
    assert side_file(str(tmp_path / "results.txt"), "chip_reads") == str(
        tmp_path / "results.chip_reads.txt"
    )
    assert side_file("", "chip_reads") == ""
    assert record_field("a#b\r\nc ") == "a b c"
    assert not append_record("", "x")
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert not append_record(str(blocker / "beam.txt"), "x")


def test_a_break_that_finds_no_slot_says_so(win, tmp_path):
    (tmp_path / "results.txt").mkdir()  # held by another program, say
    for i in range(5):
        win._number_edits[i].setText(str(10 + i))
        win._time_edits[i].setText(f"1 10:0:{i}.000#nextLap")
    win._on_source_event(Break(6, T0))
    log = [win._log.item(i).text() for i in range(win._log.count())]
    assert any(
        line.startswith(f"beam break {format_time(T0)} not stamped") for line in log
    )
    beam = tmp_path / "results.beam_breaks.txt"
    assert beam.read_text(encoding="utf-8") == f"6#{format_time(T0)}##\n"


def _two_slots_done_typing_in_slot_3(win) -> None:
    for i in range(2):
        win._number_edits[i].setText(str(10 + i))
        win._time_edits[i].setText(f"1 10:0:{i}.000#nextLap")
    win._focused_slot = 2  # the judge went on to slot 3


def test_a_break_while_the_judge_types_elsewhere_only_stamps(win, tmp_path):
    _two_slots_done_typing_in_slot_3(win)
    win._edit_dsq.setFocus()  # the judge is typing a DSQ meanwhile
    win._on_source_event(Break(1, T0))
    assert win._number_edits[0].text() == "10"  # nothing written, nothing moved
    assert win._time_edits[2].text() == f"{format_time(T0)}#nextLap"
    assert win.focusWidget() is win._edit_dsq
    assert not (tmp_path / "results.txt").exists()


def test_a_break_never_writes_a_slot_still_waiting_for_its_number(win, tmp_path):
    win._focused_slot = 2  # where the judge typed last, before going elsewhere
    win._edit_dsq.setFocus()
    win._on_source_event(Break(1, T0))
    assert win._time_edits[0].text() == f"{format_time(T0)}#nextLap"
    assert win._number_edits[0].text() == ""
    assert not (tmp_path / "results.txt").exists()


def test_the_focus_follows_the_number_being_typed_when_a_break_shifts(win):
    _two_slots_done_typing_in_slot_3(win)
    win._number_edits[2].setText("4")
    win._number_edits[2].setFocus()
    win._on_source_event(Break(1, T0))
    assert win._number_edits[1].text() == "4"
    assert win.focusWidget() is win._number_edits[1]


def test_a_break_with_every_slot_stamped_moves_them_once(win, tmp_path):
    for i in range(5):
        win._time_edits[i].setText(f"1 10:0:{i}.000#nextLap")
    win._focused_slot = 2
    win._number_edits[2].setText("4")  # the judge is typing slot 3's number
    win._number_edits[2].setFocus()
    win._on_source_event(Break(6, T0))
    results = (tmp_path / "results.txt").read_text(encoding="utf-8")
    assert results == "#1 10:0:0.000#nextLap#\n"  # one break, one slot out
    assert win._number_edits[1].text() == "4"
    assert win.focusWidget() is win._number_edits[1]
    assert win._time_edits[4].text() == f"{format_time(T0)}#nextLap"


def test_a_break_never_writes_slot_1_while_its_number_is_typed(win, tmp_path):
    for i in range(5):
        win._time_edits[i].setText(f"1 10:0:{i}.000#nextLap")
    win._focused_slot = 0
    win._number_edits[0].setText("12")  # of 123, say
    win._number_edits[0].setFocus()
    win._on_source_event(Break(6, T0))
    assert not (tmp_path / "results.txt").exists()
    assert win._number_edits[0].text() == "12"
    last = win._log.item(win._log.count() - 1).text()
    assert "slot 1's number is being typed" in last


def test_a_burst_of_breaks_backs_the_slots_up_once(win, monkeypatch):
    backups = []
    monkeypatch.setattr(mw, "save_backup", lambda **k: backups.append(k) or True)
    win._chk_disable_backup.setChecked(False)
    for seq in (1, 2, 3):
        win._on_source_event(Break(seq, T0 + seq))
    assert backups == []
    assert win._backup_timer.isActive()
    win._save_backup_if_enabled()  # the timer's tick, 2 s on
    assert len(backups) == 1


def test_a_break_never_writes_slot_1_before_its_number_is_typed(win, tmp_path):
    win._time_edits[0].setText("1 10:0:0.000#nextLap")  # a rider not known yet
    win._focused_slot = 2
    win._number_edits[2].setFocus()  # the judge went on to slot 3
    win._on_source_event(Break(1, T0))
    assert win._time_edits[1].text() == f"{format_time(T0)}#nextLap"
    assert win._time_edits[0].text() == "1 10:0:0.000#nextLap"
    assert not (tmp_path / "results.txt").exists()
