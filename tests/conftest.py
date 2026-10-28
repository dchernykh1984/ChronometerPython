"""Shared Qt fixtures for the MainWindow tests.

main_window is excluded from coverage, so these Qt-level tests are what keeps its
handlers from drifting silently.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import main_window as mw
from app import sources_config as sources

_app = QApplication.instance() or QApplication([])

# The developer's own settings, token included, and results live in data/.
_DATA = Path(__file__).resolve().parents[1] / "data"


def _data_state() -> dict[str, int]:
    return {p.name: p.stat().st_mtime_ns for p in _DATA.glob("*")}


@pytest.fixture(scope="session", autouse=True)
def _data_untouched():
    """Fail the run when a test wrote into data/: it holds what no test may change."""
    before = _data_state()
    yield
    assert _data_state() == before, "a test wrote into the developer's data/ folder"


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
    # Event source settings stay in memory: data/sources.txt is the developer's.
    monkeypatch.setattr(mw, "load_sources", lambda *a, **k: dict(sources.DEFAULTS))
    monkeypatch.setattr(mw, "save_sources", lambda *a, **k: True)
    w = mw.MainWindow()
    w._chk_disable_backup.setChecked(True)  # don't write backup files during tests
    w._config_path = str(tmp_path / "groupsList.txt")  # keep config writes out of repo
    w._edit_results_file.setText(str(tmp_path / "results.txt"))
    w._edit_groups_file.setText(str(tmp_path / "groups.txt"))
    yield w
    w._stop_source(wait=True)  # no connector process outlives its test
    # deleteLater waits for an event loop: a later test would run these timers,
    # the 500 ms config save among them, after the fakes above are undone.
    for timer in w.findChildren(QTimer):
        timer.stop()
    w.deleteLater()
