"""Runtime files belong to the portable app even when launched elsewhere."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import main_window as mw
from app import paths
from app.models import (
    append_to_finish_file,
    append_to_group_file,
    load_config,
    load_http_config,
    read_file_lines,
    save_config,
    save_http_config,
)


@pytest.fixture
def race_dir(tmp_path, monkeypatch):
    race = tmp_path / "race"
    race.mkdir()
    unrelated = tmp_path / "working"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        paths.sys,
        "executable",
        str(race / "Chronometer.app/Contents/MacOS/Chronometer"),
    )
    return race


def test_group_start_creates_backup_next_to_app(win, race_dir, monkeypatch):
    win._chk_disable_backup.setChecked(False)
    monkeypatch.setattr(mw, "get_current_time", lambda **kw: "0 12:00:00.000")
    win._combo_group.clear()
    win._combo_group.addItem("GroupA")
    win._on_start_group()

    backups = list((race_dir / "temp").glob("stc*.txt"))
    assert len(backups) == 1
    assert "GroupA#0 12:00:00.000#" in backups[0].read_text(encoding="utf-8")
    assert not (Path.cwd() / "temp").exists()


def test_relative_timing_files_and_upload_snapshots_use_app_folder(race_dir):
    assert append_to_finish_file("data/results.txt", "12", "0 12:01:00#finish")
    assert append_to_group_file("data/groups.txt", "GroupA", "0 12:00:00")
    assert read_file_lines("data/results.txt") == ["12#0 12:01:00#finish#"]
    assert read_file_lines("data/groups.txt") == ["GroupA#0 12:00:00#"]
    assert (race_dir / "data/results.txt").exists()
    assert not (Path.cwd() / "data").exists()


def test_relative_config_keeps_portable_file_names(race_dir):
    assert save_config(
        "data/groupsList.txt", ["GroupA"], "data/results.txt", "data/groups.txt"
    )
    assert load_config("data/groupsList.txt") == (
        ["GroupA"],
        "data/results.txt",
        "data/groups.txt",
    )
    assert (race_dir / "data/groupsList.txt").exists()


def test_relative_http_config_is_kept_with_the_event(race_dir):
    assert save_http_config({"device_id": "test-device"}, "data/http_config.txt")
    assert load_http_config("data/http_config.txt")["device_id"] == "test-device"
    assert (race_dir / "data/http_config.txt").exists()
    assert not (Path.cwd() / "data").exists()
