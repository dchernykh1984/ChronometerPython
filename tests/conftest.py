"""Shared Qt fixtures for the MainWindow tests.

main_window is excluded from coverage, so these Qt-level tests are what keeps its
handlers from drifting silently.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app import main_window as mw

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def win(monkeypatch, tmp_path):
    """A MainWindow wired to a fake HTTP config, writing only into tmp_path."""
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
    w._config_path = str(tmp_path / "groupsList.txt")  # keep config writes out of repo
    w._edit_results_file.setText(str(tmp_path / "results.txt"))
    w._edit_groups_file.setText(str(tmp_path / "groups.txt"))
    yield w
    w.deleteLater()
