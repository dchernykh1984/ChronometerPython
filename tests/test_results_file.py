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
    assert rf.read_results(str(path)) == ["15#1 10:0:0#finish#"]


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
