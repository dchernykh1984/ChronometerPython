"""Downloading the start protocol: only on the button, never changing on a failure."""

from __future__ import annotations

import time
import urllib.request
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from app import main_window as mw
from app import results_file as rf

LINES = ["15#Rider#M40#3#1#1990#T#C##0 00:00:00.000#r1#A#"]


def _wait_until(condition, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def start_file(win, tmp_path, monkeypatch):
    monkeypatch.setattr(rf, "app_path", lambda *parts: tmp_path.joinpath(*parts))
    path = tmp_path / "start.txt"
    path.write_text("old#line#\n", encoding="utf-8")
    win._edit_start_protocol.setText(str(path))
    win._on_start_protocol_path()
    return path


def test_a_download_replaces_the_file_and_keeps_the_old_one(
    win, start_file, tmp_path, monkeypatch
):
    asked = []
    monkeypatch.setattr(mw, "fetch_start_list", lambda *a: asked.append(a) or LINES)
    win._on_download_start_protocol()
    assert _wait_until(lambda: win._fetch_worker is None)
    assert asked == [("https://s", "tok")]
    assert start_file.read_text(encoding="utf-8") == LINES[0] + "\n"
    backups = list((tmp_path / "temp").glob("start*.txt"))
    assert [b.read_text(encoding="utf-8") for b in backups] == ["old#line#\n"]
    assert win._chip_map.bib_of == {"A": "15"}
    assert (
        "start protocol downloaded: 1 line(s)"
        in win._log.item(win._log.count() - 1).text()
    )
    assert win._btn_download_start.isEnabled()


def test_a_failed_download_changes_nothing(win, start_file, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))

    def offline(*a):
        raise ValueError("Connection error: offline")

    monkeypatch.setattr(mw, "fetch_start_list", offline)
    win._on_download_start_protocol()
    assert _wait_until(lambda: win._fetch_worker is None)
    assert start_file.read_text(encoding="utf-8") == "old#line#\n"
    assert "offline" in warnings[0]


def test_without_a_site_nothing_is_asked(win, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    monkeypatch.setattr(mw, "fetch_start_list", lambda *a: pytest.fail("asked"))
    win._http_cfg["site_url"] = ""
    win._on_download_start_protocol()
    assert win._fetch_worker is None and "must be set" in warnings[0]


def test_nothing_reaches_the_network_without_a_button(monkeypatch, request):
    """SC-005: opening the window and running a connector ask the site nothing."""
    asked: list = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: asked.append(a))
    win = request.getfixturevalue("win")  # made only now, with the network gone
    win._combo_source.setCurrentIndex(win._combo_source.findData("beam"))
    win._on_source_start()
    assert _wait_until(lambda: win._lbl_source_state.text() == "running")
    assert not _wait_until(lambda: asked, timeout=1.0)


def test_closing_waits_for_a_running_download(win, start_file, monkeypatch):
    """A running thread destroyed with the window would abort the program."""
    monkeypatch.setattr(
        mw.QMessageBox, "question", lambda *a: mw.QMessageBox.StandardButton.Yes
    )
    monkeypatch.setattr(mw, "fetch_start_list", lambda *a: time.sleep(0.5) or LINES)
    win._on_download_start_protocol()
    worker = win._fetch_worker
    event = Mock()
    win.closeEvent(event)
    assert not worker.isRunning()
    event.accept.assert_called_once()
    assert start_file.read_text(encoding="utf-8") == "old#line#\n"  # closed first


def test_download_goes_into_the_path_as_typed(win, start_file, tmp_path, monkeypatch):
    typed = tmp_path / "typed.txt"
    win._edit_start_protocol.setText(str(typed))  # no Return pressed
    monkeypatch.setattr(mw, "fetch_start_list", lambda *a: LINES)
    win._on_download_start_protocol()
    assert _wait_until(lambda: win._fetch_worker is None)
    assert typed.read_text(encoding="utf-8") == LINES[0] + "\n"
    assert start_file.read_text(encoding="utf-8") == "old#line#\n"


def test_reload_reads_the_path_as_typed(win, start_file, tmp_path):
    typed = tmp_path / "typed.txt"
    typed.write_text(LINES[0] + "\n", encoding="utf-8")
    win._edit_start_protocol.setText(str(typed))
    win._btn_reload_start.click()
    assert win._chip_map.bib_of == {"A": "15"}
