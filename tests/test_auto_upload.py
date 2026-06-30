"""Qt-level tests for the auto-upload wiring in MainWindow.

The pure HTTP client and config helpers are tested elsewhere; here we verify referee
actions actually trigger an upload of the right stream/endpoint/revision. main_window is
excluded from coverage, so a silent regression (no upload, or wrong endpoint) would
otherwise go unnoticed.
"""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app import http_io
from app import main_window as mw

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def win(monkeypatch, tmp_path):
    cfg = {
        "site_url": "https://s",
        "token": "tok",
        "device_id": "dev",
        "point_number": "0",
        "rev_finish": "0",
        "rev_group": "0",
    }
    monkeypatch.setattr(mw, "load_http_config", lambda *a, **k: dict(cfg))
    monkeypatch.setattr(mw, "save_http_config", lambda *a, **k: True)
    w = mw.MainWindow()
    w._chk_disable_backup.setChecked(True)  # don't write backup files during tests
    w._edit_results_file.setText(str(tmp_path / "results.txt"))
    w._edit_groups_file.setText(str(tmp_path / "groups.txt"))
    yield w
    w.deleteLater()


# -- handlers schedule / trigger an upload ---------------------------------


def test_slot_save_schedules_finish_upload(win):
    win._schedule_finish_upload = Mock()
    win._number_edits[0].setText("12")
    win._time_edits[0].setText("0 0:0:1#finish")
    win._on_save(0)
    win._schedule_finish_upload.assert_called_once()


def test_dsq_schedules_finish_upload(win):
    win._schedule_finish_upload = Mock()
    win._edit_dsq.setText("7")
    win._on_dsq()
    win._schedule_finish_upload.assert_called_once()


def test_save_and_shift_schedules_finish_upload(win):
    win._schedule_finish_upload = Mock()
    win._number_edits[0].setText("3")
    win._time_edits[0].setText("0 0:0:2#finish")
    win._on_save_and_shift()
    win._schedule_finish_upload.assert_called_once()


def test_save_all_schedules_finish_upload(win):
    win._schedule_finish_upload = Mock()
    win._number_edits[0].setText("1")
    win._time_edits[0].setText("0 0:0:1#finish")
    win._number_edits[1].setText("2")
    win._time_edits[1].setText("0 0:0:2#finish")
    win._on_save_all_and_empty()
    win._schedule_finish_upload.assert_called()


def test_save_group_uploads_group_stream(win):
    win._upload_group_stream = Mock()
    win._combo_group.setCurrentText("GroupA")
    win._edit_group_time.setText("0 0:0:5.000")
    win._on_save_group()
    win._upload_group_stream.assert_called_once()


# -- _upload_finish_stream picks endpoint by point_number ------------------


def test_finish_stream_point0_uses_finish_endpoint(win, tmp_path):
    win._start_upload = Mock()
    win._http_cfg["point_number"] = "0"
    (tmp_path / "results.txt").write_text("1#0 0:0:1#\n", encoding="utf-8")
    win._upload_finish_stream()
    args = win._start_upload.call_args.args
    assert args[0] is http_io.upload_finish_times
    assert args[1:4] == ("https://s", "tok", "dev")
    assert args[4] == ["1#0 0:0:1#"]


def test_finish_stream_point_n_uses_remote_endpoint(win, tmp_path):
    win._start_upload = Mock()
    win._http_cfg["point_number"] = "3"
    (tmp_path / "results.txt").write_text("1#0 0:1:0#\n", encoding="utf-8")
    win._upload_finish_stream()
    args = win._start_upload.call_args.args
    assert args[0] is http_io.upload_remote_points
    # upload_remote_points(site, token, device, point_number, items, revision)
    assert args[4] == 3
    assert args[5] == ["1#0 0:1:0#"]


def test_group_stream_uses_group_endpoint_and_bumps_revision(win, tmp_path):
    win._start_upload = Mock()
    (tmp_path / "groups.txt").write_text("GroupA#0 0:0:5#\n", encoding="utf-8")
    win._upload_group_stream()
    args = win._start_upload.call_args.args
    assert args[0] is http_io.upload_group_times
    assert args[4] == ["GroupA#0 0:0:5#"]
    assert args[5] == 1  # revision incremented from 0
    assert win._http_cfg["rev_group"] == "1"


def test_revision_increments_across_uploads(win, tmp_path):
    win._start_upload = Mock()
    (tmp_path / "results.txt").write_text("1#0 0:0:1#\n", encoding="utf-8")
    win._upload_finish_stream()
    win._upload_finish_stream()
    assert win._http_cfg["rev_finish"] == "2"
    assert win._start_upload.call_args_list[0].args[5] == 1
    assert win._start_upload.call_args_list[1].args[5] == 2


def test_no_upload_without_credentials(win, tmp_path):
    win._start_upload = Mock()
    win._http_cfg["token"] = ""  # missing token
    (tmp_path / "results.txt").write_text("1#0 0:0:1#\n", encoding="utf-8")
    win._upload_finish_stream()
    win._start_upload.assert_not_called()
