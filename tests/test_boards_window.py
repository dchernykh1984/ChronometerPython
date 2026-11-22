"""Qt-level tests of the beam boards in the Event source group (spec 003, FR-001 to
FR-006): the list found by a search, the pick by its checks, Blink. main_window is out
of coverage: these guard it. The search and the blink are fake programs here."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt

from app import main_window as mw
from app import sources_config as sources
from tests.test_sources_window import _choose, _wait_until

USB = {"link": "usb", "name": "beam-rp2040", "port": "COM3", "kind": "beam-rp2040"}
NEAR = {"link": "ble", "name": "beam-7c1c", "device": "AA", "rssi": -61}
SEARCH = f"""
import json
print(json.dumps({{"type": "hello", "protocol": 1, "connector": "beam-scan"}}))
print(json.dumps({{"type": "error", "message": "Bluetooth: off"}}))
print(json.dumps({{"type": "found", "boards": [{USB!r}, {NEAR!r}]}}))
"""
BLINK = """
import json, sys
board = json.loads(sys.stdin.readline())["settings"]["boards"][0]
if board.get("device") == "AA":
    said = {"type": "error", "message": board["name"] + ": not reached"}
    print(json.dumps(said), flush=True)
sys.exit(3 if board.get("port") == "COM4" else 0)
"""


def _programs(monkeypatch, **programs: str) -> None:
    def command(name: str) -> list[str]:
        if name not in programs:
            return ["/no/such/program"]
        return [sys.executable, "-c", programs[name]]

    monkeypatch.setattr(mw, "builtin_command", command)


def _log(win) -> list[str]:
    return [win._log.item(i).text() for i in range(win._log.count())]


def _rows(win) -> list[tuple[str, bool]]:
    items = [win._list_boards.item(i) for i in range(win._list_boards.count())]
    return [(one.text(), one.checkState() == Qt.CheckState.Checked) for one in items]


def _found(win, monkeypatch) -> None:
    _programs(monkeypatch, **{"beam-scan": SEARCH})
    win._on_find_boards()
    assert not win._btn_find_boards.isEnabled()
    assert _wait_until(lambda: win._boards_search is None)


def test_the_boards_come_first_and_only_they_show_the_list(win):
    _choose(win, "beam")
    names = [
        win._combo_connector.itemData(i) for i in range(win._combo_connector.count())
    ]
    assert names == ["beam-boards", "dummy-beam", "custom"]
    assert win._connector_name() == "beam-boards"  # the default
    assert not win._boards_panel.isHidden()
    _choose(win, "beam", "dummy-beam")
    assert win._boards_panel.isHidden()


def test_a_search_lists_the_boards_and_the_checks_are_the_pick(win, monkeypatch):
    _choose(win, "beam", "beam-boards")
    _found(win, monkeypatch)
    assert win._btn_find_boards.isEnabled()
    assert _rows(win) == [
        ("beam-rp2040 (USB, COM3)", False),
        ("beam-7c1c (Bluetooth, -61 dBm)", False),
    ]
    assert "boards search: Bluetooth: off" in _log(win)
    assert "boards search: 2 found" in _log(win)
    win._list_boards.item(1).setCheckState(Qt.CheckState.Checked)
    pick = {"link": "ble", "name": "beam-7c1c", "device": "AA"}  # no signal kept
    settings = sources.connector_settings(win._sources, "beam-boards")
    assert settings["boards"] == [pick]
    assert '"device": "AA"' in win._edit_connector_settings.text()


def test_a_pick_typed_in_settings_shows_in_the_list_not_found(win):
    _choose(win, "beam", "beam-boards")
    gone = {"link": "ble", "name": "beam-b6b0", "device": "BB"}
    win._edit_connector_settings.setText(f'{{"boards": [{gone!s}]}}'.replace("'", '"'))
    assert win._on_connector_settings_edited()
    assert _rows(win) == [("beam-b6b0 (Bluetooth, not found by the last search)", True)]
    item = win._list_boards.item(0)
    assert item.foreground().color() == Qt.GlobalColor.gray


def test_the_pick_is_locked_while_the_source_reads_it(win, monkeypatch):
    _choose(win, "beam", "beam-boards")
    _found(win, monkeypatch)
    win._list_boards.item(0).setCheckState(Qt.CheckState.Checked)
    monkeypatch.setattr(mw.ConnectorHost, "start", lambda *_: None)
    win._on_source_start()
    assert win._reading == {"COM3"}
    item = win._list_boards.item(0)
    assert not item.flags() & Qt.ItemFlag.ItemIsUserCheckable
    assert item.checkState() == Qt.CheckState.Checked
    win._on_source_stop()
    assert win._reading == set()
    assert win._list_boards.item(0).flags() & Qt.ItemFlag.ItemIsUserCheckable


def test_blink_goes_through_the_source_reading_the_board(win, monkeypatch):
    _choose(win, "beam", "beam-boards")
    win._on_blink()
    assert _log(win)[-1] == "blink: choose a board in the list first"
    _found(win, monkeypatch)
    win._list_boards.setCurrentRow(1)
    told: list[dict] = []

    class Host:
        answer = True

        def tell(self, command: dict) -> bool:
            told.append(command)
            return self.answer

    host = Host()
    win._host, win._reading = host, {"AA"}  # undone below: the fixture stops it
    win._on_blink()
    assert told == [{"cmd": "blink", "board": "AA"}]
    assert _log(win)[-1] == "blink beam-7c1c: its LED flashes 5 times"
    host.answer = False  # restarting: no hello yet
    win._on_blink()
    assert _log(win)[-1] == "blink beam-7c1c: the source is starting, try again"
    win._host, win._reading = None, set()


def test_blink_of_a_board_not_read_runs_a_blink_of_its_own(win, monkeypatch):
    _choose(win, "beam", "beam-boards")
    _found(win, monkeypatch)
    _programs(monkeypatch, **{"beam-blink": BLINK})
    win._list_boards.setCurrentRow(1)
    win._on_blink()
    assert _log(win)[-1] == "blink beam-7c1c: reaching it"
    assert _wait_until(lambda: not win._blinks)
    assert _log(win)[-1] == "blink beam-7c1c: not reached"
    win._list_boards.setCurrentRow(0)
    win._on_blink()
    assert _wait_until(lambda: not win._blinks)
    assert _log(win)[-1] == "blink beam-rp2040: its LED flashed 5 times"
    win._boards_found = [dict(USB, port="COM4")]
    win._show_boards()
    win._list_boards.setCurrentRow(0)
    win._on_blink()
    assert _wait_until(lambda: not win._blinks)
    assert _log(win)[-1] == "blink beam-rp2040: failed, exit code 3"


def test_a_search_or_a_blink_that_cannot_start_is_said(win, monkeypatch):
    _choose(win, "beam", "beam-boards")
    _programs(monkeypatch)  # no program at all
    win._on_find_boards()
    assert _wait_until(lambda: win._boards_search is None)
    assert _log(win)[-1] == "boards search could not start"
    assert win._btn_find_boards.isEnabled()
    win._boards_found = [USB]
    win._show_boards()
    win._list_boards.setCurrentRow(0)
    win._on_blink()
    assert _wait_until(lambda: not win._blinks)
    assert _log(win)[-1] == "blink beam-rp2040: could not start"
