"""The Event source group: choosing a source and a device, Start and Stop."""

from __future__ import annotations

import time

from PySide6.QtWidgets import QApplication

from app import main_window as mw
from app import sources_config as sources


def _wait_until(condition, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


def _choose(win, source: str, connector: str | None = None) -> None:
    win._combo_source.setCurrentIndex(win._combo_source.findData(source))
    if connector is not None:
        win._combo_connector.setCurrentIndex(win._combo_connector.findData(connector))


def test_by_hand_is_the_default_and_starts_nothing(win):
    assert win._source_kind() == "hand"
    assert not win._btn_source_start.isEnabled()
    win._on_source_start()
    assert win._host is None


def test_chips_list_the_test_connector_custom_and_disabled_stubs(win):
    _choose(win, "chips")
    names = [
        win._combo_connector.itemData(i) for i in range(win._combo_connector.count())
    ]
    assert names[:2] == ["dummy-chips", "replay"]
    llrp = names.index("llrp")
    assert "not available yet" in win._combo_connector.itemText(llrp)
    assert not win._combo_connector.model().item(llrp).isEnabled()
    assert win._sources["source"] == "chips"


def test_the_test_beam_runs_with_a_test_data_warning_and_stops(win):
    _choose(win, "beam", "dummy-beam")
    win._on_source_start()
    assert _wait_until(lambda: win._lbl_source_state.text() == "running")
    assert not win._lbl_test_data.isHidden()
    win._on_source_stop()
    assert win._host is None
    assert win._lbl_source_state.text() == "stopped"
    assert win._lbl_test_data.isHidden()


def test_a_saved_source_does_not_start_on_its_own(monkeypatch):
    saved = dict(sources.DEFAULTS, source="beam")
    monkeypatch.setattr(mw, "load_sources", lambda *a, **k: dict(saved))
    monkeypatch.setattr(mw, "save_sources", lambda *a, **k: True)
    monkeypatch.setattr(mw, "load_http_config", lambda *a, **k: {})
    window = mw.MainWindow()
    try:
        assert window._source_kind() == "beam"
        assert window._host is None
        assert window._lbl_source_state.text() == "stopped"
    finally:
        window.deleteLater()


def test_settings_must_be_json(win, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    _choose(win, "beam", "dummy-beam")
    win._edit_connector_settings.setText("{broken")
    win._on_connector_settings_edited()
    assert "JSON" in warnings[0]
    assert sources.connector_settings(win._sources, "dummy-beam") == {
        "min_s": 5,
        "max_s": 20,
    }
    win._edit_connector_settings.setText('{"min_s": 1, "max_s": 2}')
    win._on_connector_settings_edited()
    assert sources.connector_settings(win._sources, "dummy-beam") == {
        "min_s": 1,
        "max_s": 2,
    }


def test_a_custom_connector_needs_a_command_line(win, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    _choose(win, "beam", "custom")
    win._on_source_start()
    assert win._host is None and "command line" in warnings[0]
    win._edit_connector_settings.setText("my-beam --port 3")
    win._on_connector_settings_edited()
    assert win._sources["custom_command"] == "my-beam --port 3"


def test_closing_the_window_stops_the_connector(win, monkeypatch):
    _choose(win, "beam", "dummy-beam")
    win._on_source_start()
    assert _wait_until(lambda: win._lbl_source_state.text() == "running")
    monkeypatch.setattr(
        mw.QMessageBox, "question", lambda *a: mw.QMessageBox.StandardButton.Yes
    )
    win.close()
    assert win._host is None


def test_a_source_event_is_logged(win):
    win._on_source_event(mw.cp.Status("connected", "COM3"))
    win._on_source_event(mw.cp.Error("lost"))
    log = [win._log.item(i).text() for i in range(win._log.count())]
    assert "source connected COM3" in log and "source error: lost" in log


def test_a_source_needs_a_results_file_to_start(win, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    win._edit_results_file.setText("")
    _choose(win, "beam")
    win._on_source_start()
    assert win._host is None
    assert warnings[0].startswith("Choose the results file first")


def test_start_uses_the_settings_typed_without_pressing_return(win, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    _choose(win, "beam", "custom")
    win._edit_connector_settings.setText("my-beam --port 3")  # no editingFinished
    started = []
    monkeypatch.setattr(mw.ConnectorHost, "start", lambda self, *a: started.append(a))
    win._on_source_start()
    assert warnings == []
    assert started[0][0] == ["my-beam", "--port", "3"]
    assert win._sources["custom_command"] == "my-beam --port 3"


def test_start_refuses_settings_typed_that_are_not_json(win, monkeypatch):
    warnings = []
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *a: warnings.append(a[2]))
    _choose(win, "beam", "dummy-beam")
    win._edit_connector_settings.setText("{min_s: 5")
    win._on_source_start()
    assert win._host is None
    assert "JSON" in warnings[0]


def test_settings_typed_are_kept_when_another_device_is_picked(win):
    _choose(win, "beam", "custom")
    win._edit_connector_settings.setText("my-beam --port 3")  # no Return pressed
    _choose(win, "beam", "dummy-beam")
    assert win._sources["custom_command"] == "my-beam --port 3"
    assert "min_s" in win._edit_connector_settings.text()  # the test beam's own


def test_settings_typed_are_kept_when_another_source_is_picked(win):
    _choose(win, "beam", "dummy-beam")
    win._edit_connector_settings.setText('{"min_s": 1, "max_s": 2}')
    _choose(win, "chips")
    assert sources.connector_settings(win._sources, "dummy-beam") == {
        "min_s": 1,
        "max_s": 2,
    }
