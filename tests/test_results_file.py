"""Rewriting the results file: backup first, one-step replace, refusals."""

from __future__ import annotations

import os

import pytest

from app import results_file as rf


def _results(tmp_path, *lines: str):
    path = tmp_path / "results.txt"
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def test_a_rewrite_keeps_the_old_file_in_a_backup(tmp_path):
    path = _results(tmp_path, "15#1 10:0:0.000#nextLap#", "16#1 10:0:1.000#nextLap#")
    backup = rf.rewrite_results(str(path), ["15#1 10:0:0.000#nextLap#"], tmp_path / "b")
    assert path.read_text(encoding="utf-8") == "15#1 10:0:0.000#nextLap#\n"
    assert backup.read_text(encoding="utf-8").splitlines() == [
        "15#1 10:0:0.000#nextLap#",
        "16#1 10:0:1.000#nextLap#",
    ]
    assert rf.rewrite_results(str(path), [], tmp_path / "b") != backup  # never reused


def test_a_failed_backup_leaves_the_file_untouched(tmp_path, monkeypatch):
    path = _results(tmp_path, "15#1 10:0:0.000#nextLap#")

    def refuse(self, data):
        raise OSError("disk full")

    monkeypatch.setattr(rf.Path, "write_bytes", refuse)
    with pytest.raises(OSError, match="disk full"):
        rf.rewrite_results(str(path), [], tmp_path / "b")
    assert path.read_text(encoding="utf-8") == "15#1 10:0:0.000#nextLap#\n"


def test_a_replace_held_up_by_a_reader_is_retried(tmp_path, monkeypatch):
    path = _results(tmp_path, "15#1 10:0:0.000#nextLap#")
    real, calls = os.replace, []

    def busy_twice(source, target):
        calls.append(source)
        if len(calls) < 3:
            raise PermissionError("sharing violation")
        real(source, target)

    monkeypatch.setattr(rf.os, "replace", busy_twice)
    monkeypatch.setattr(rf.time, "sleep", lambda s: None)
    rf.rewrite_results(str(path), ["16#1 10:0:1.000#nextLap#"], tmp_path / "b")
    assert len(calls) == 3
    assert path.read_text(encoding="utf-8") == "16#1 10:0:1.000#nextLap#\n"


def test_a_replace_that_never_succeeds_fails_and_keeps_the_old_file(
    tmp_path, monkeypatch
):
    path = _results(tmp_path, "15#1 10:0:0.000#nextLap#")
    clock = iter(range(100))

    def busy(source, target):
        raise PermissionError("sharing violation")

    monkeypatch.setattr(rf.os, "replace", busy)
    monkeypatch.setattr(rf.time, "sleep", lambda s: None)
    monkeypatch.setattr(rf.time, "monotonic", lambda: next(clock))
    with pytest.raises(PermissionError):
        rf.rewrite_results(str(path), [], tmp_path / "b")
    assert path.read_text(encoding="utf-8") == "15#1 10:0:0.000#nextLap#\n"
    assert not (tmp_path / "results.txt.tmp").exists()


def test_the_first_rewrite_of_a_missing_file_backs_up_nothing(tmp_path):
    path = tmp_path / "results.txt"
    backup = rf.rewrite_results(str(path), ["15#1 10:0:0#finish#"], tmp_path / "b")
    assert backup.read_bytes() == b""
    assert path.read_text(encoding="utf-8").splitlines() == ["15#1 10:0:0#finish#"]


@pytest.mark.parametrize(
    ("number", "time_str", "action", "problem"),
    [
        ("15", "1 10:0:0.000", "nextLap", None),
        ("15", "1 10:0:0", "finish", None),
        ("15", "1 10:0:0.000", "DSQ: crossed the tape", None),
        ("", "1 10:0:0.000", "nextLap", "empty"),
        ("1#5", "1 10:0:0.000", "nextLap", "'#'"),
        ("15", "10:0:0", "nextLap", "time"),
        ("15", "1 10:0:0.000", "lap", "action"),
    ],
)
def test_a_crossing_is_checked_before_it_is_written(number, time_str, action, problem):
    found = rf.crossing_problem(number, time_str, action)
    assert (found is None) if problem is None else (problem in found)
    assert rf.crossing_line("15", "1 10:0:0", "finish") == "15#1 10:0:0#finish#"


def test_a_rewrite_ends_its_lines_as_appends_do(tmp_path):
    from app.models import append_to_finish_file

    path = tmp_path / "results.txt"
    assert append_to_finish_file(str(path), "15", "1 10:0:0.000#nextLap")
    appended = path.read_bytes()  # CRLF on Windows, LF elsewhere
    rf.rewrite_results(str(path), ["15#1 10:0:0.000#nextLap#"], tmp_path / "b")
    assert path.read_bytes() == appended


def test_a_crossing_is_known_by_its_number_and_time_whatever_its_action():
    line = rf.crossing_line("15", "1 10:0:0.000", "nextLap")
    assert rf.crossing_key(line) == ("15", "1 10:0:0.000")
    assert rf.crossing_key(line) == rf.crossing_key("15#1 10:0:0.000#finish#")


@pytest.mark.parametrize("number", ["15\u2028", "1\x0c5", "15\x85"])
def test_a_number_with_any_line_break_is_refused(number):
    assert "line break" in rf.crossing_problem(number, "1 10:0:0.000", "finish")


@pytest.mark.parametrize("step", ["fsync", "replace"])
def test_a_failed_write_leaves_no_temporary_file(tmp_path, monkeypatch, step):
    def fail(*a):
        raise OSError("disk full")

    monkeypatch.setattr(rf.os, step, fail)
    target = tmp_path / "results.chip_state.json"
    with pytest.raises(OSError, match="disk full"):
        rf.write_in_one_step(target, "{}")
    assert list(tmp_path.iterdir()) == []


def test_a_time_in_digits_other_than_ascii_is_refused():
    arabic_indic = "".join(chr(0x660 + int(c)) for c in "1")  # one, as typed in Arabic
    problem = rf.crossing_problem("15", f"{arabic_indic} 10:0:0.000", "finish")
    assert problem is not None and "D H:M:S" in problem
