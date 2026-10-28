"""PySide6 main window for Windows Chronometer (SportTimerClient)."""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import connector_protocol as cp
from app.chip_report import chip_report
from app.chips import (
    ChipMap,
    ChipTiming,
    build_chip_map,
    load_chip_state,
    normalise_chip,
    raw_read,
    read_start_protocol,
    rebuilt_timing,
    save_chip_state,
)
from app.connector_host import ConnectorHost, builtin_command
from app.connectors import builtin, connectors_for, find
from app.device_files import append_record, field, side_file
from app.http_io import (
    fetch_groups,
    fetch_start_list,
    upload_finish_times,
    upload_group_times,
    upload_remote_points,
)
from app.models import (
    append_to_finish_file,
    append_to_group_file,
    dsq_status,
    format_time,
    get_current_time,
    load_config,
    load_http_config,
    parse_time,
    read_file_lines,
    save_backup,
    save_config,
    save_http_config,
    scale_time,
)
from app.paths import app_path
from app.results_file import (
    ACTIONS,
    crossing_line,
    crossing_problem,
    read_results,
    rewrite_results,
)
from app.sources_config import (
    connector_settings,
    dead_time_s,
    load_sources,
    save_sources,
    set_connector_settings,
)

_CONFIG_PATH = str(app_path("data", "groupsList.txt"))
_N_SLOTS = 5


class _UploadWorker(QThread):
    """Runs one timing upload off the UI thread so a slow network never blocks timing.

    Emits ``log`` (marshalled to the main thread) with a short result so the action log
    can show success/failure; any network error is reported, never raised into the UI.
    """

    log = Signal(str)

    def __init__(self, func, *args) -> None:
        super().__init__()
        self._func = func
        self._args = args

    def run(self) -> None:
        try:
            count = self._func(*self._args)
            self.log.emit(f"  site: uploaded {count} item(s)")
        except Exception as exc:  # network errors must not crash timing
            self.log.emit(f"  site upload error: {exc}")


class _FetchWorker(QThread):
    """Runs one download off the UI thread; ``done`` carries the result or the error."""

    done = Signal(object)

    def __init__(self, func, *args) -> None:
        super().__init__()
        self._func = func
        self._args = args

    def run(self) -> None:
        try:
            self.done.emit(self._func(*self._args))
        except Exception as exc:  # a network error must not reach the UI as one
            self.done.emit(exc)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Chronometer")
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "app.ico")))
        self._results_file: str = ""
        self._group_start_file: str = ""
        self._show_time: bool = False
        self._focused_slot: int = 0
        # Site-upload state: settings persisted in a key=value file; running upload
        # threads are kept alive until they finish (a GC'd running QThread would crash).
        self._http_cfg: dict[str, str] = load_http_config()
        self._upload_workers: list[_UploadWorker] = []
        # Debounce finish/remote uploads: a batch save writes several lines, but we push
        # the resulting file snapshot once, shortly after the last write.
        self._finish_upload_timer = QTimer(self)
        self._finish_upload_timer.setSingleShot(True)
        self._finish_upload_timer.timeout.connect(self._upload_finish_stream)
        # Debounce config writes: field edits (and initial population) fire textChanged
        # per keystroke, so persist once shortly after the last change.
        self._http_save_timer = QTimer(self)
        self._http_save_timer.setSingleShot(True)
        self._http_save_timer.timeout.connect(self._flush_http_config)
        # The event source: by hand, or a connector process for a beam or chips.
        # A connector starts only on Start, also after a restart of the program.
        self._sources: dict[str, str] = load_sources()
        self._host: ConnectorHost | None = None
        self._setup_ui()
        self._reload_chip_map()  # the file used last; the site is never asked here
        self._config_path: str = _CONFIG_PATH
        self._load_config(self._config_path)
        self._apply_http_config_to_ui()
        if self._results_path():
            self._timing()  # replays reads a crash left, retries waiting crossings
        self._start_timer()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # ---- LEFT: 5 finish slots ----
        slots_box = QGroupBox("Finish slots")
        slots_layout = QGridLayout(slots_box)

        # header row
        slots_layout.addWidget(QLabel("#"), 0, 0)
        slots_layout.addWidget(QLabel("Number"), 0, 1)
        slots_layout.addWidget(QLabel("Time"), 0, 2)
        slots_layout.addWidget(QLabel("Crosses"), 0, 3)
        slots_layout.addWidget(QLabel("Finish"), 0, 4)
        slots_layout.addWidget(QLabel("Save"), 0, 5)

        self._number_edits: list[QLineEdit] = []
        self._time_edits: list[QLineEdit] = []
        self._cross_labels: list[QLabel] = []

        for i in range(_N_SLOTS):
            row = i + 1
            slots_layout.addWidget(QLabel(str(row)), row, 0)

            num_edit = QLineEdit()
            num_edit.setFixedWidth(70)
            num_edit.textChanged.connect(self._on_number_changed)
            num_edit.installEventFilter(self)
            self._number_edits.append(num_edit)
            slots_layout.addWidget(num_edit, row, 1)

            time_edit = QLineEdit()
            time_edit.setMinimumWidth(200)
            self._time_edits.append(time_edit)
            slots_layout.addWidget(time_edit, row, 2)

            cross_lbl = QLabel("0")
            cross_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cross_lbl.setFixedWidth(30)
            self._cross_labels.append(cross_lbl)
            slots_layout.addWidget(cross_lbl, row, 3)

            finish_btn = QPushButton("F")
            finish_btn.setFixedWidth(30)
            finish_btn.clicked.connect(lambda _, idx=i: self._on_finish(idx))
            slots_layout.addWidget(finish_btn, row, 4)

            save_btn = QPushButton("S")
            save_btn.setFixedWidth(30)
            save_btn.clicked.connect(lambda _, idx=i: self._on_save(idx))
            slots_layout.addWidget(save_btn, row, 5)

        # next-number row
        next_row = _N_SLOTS + 1
        slots_layout.addWidget(QLabel("Next:"), next_row, 0, 1, 1)
        self._next_number = QLineEdit()
        self._next_number.setFixedWidth(70)
        self._next_number.installEventFilter(self)
        slots_layout.addWidget(self._next_number, next_row, 1)

        # action buttons
        btn_row = _N_SLOTS + 2
        self._btn_save_all_empty = QPushButton("Save All and Clear")
        self._btn_save_all_empty.clicked.connect(self._on_save_all_and_empty)
        slots_layout.addWidget(self._btn_save_all_empty, btn_row, 0, 1, 3)

        self._btn_save_shift = QPushButton("Save+Shift")
        self._btn_save_shift.clicked.connect(self._on_save_and_shift)
        slots_layout.addWidget(self._btn_save_shift, btn_row, 3, 1, 3)

        btn_row2 = _N_SLOTS + 3
        self._btn_finish_all = QPushButton("Finish ALL empty")
        self._btn_finish_all.clicked.connect(self._on_finish_all)
        slots_layout.addWidget(self._btn_finish_all, btn_row2, 0, 1, 3)

        self._btn_empty_all = QPushButton("Clear all")
        self._btn_empty_all.clicked.connect(self._on_empty_all)
        slots_layout.addWidget(self._btn_empty_all, btn_row2, 3, 1, 3)

        self._chk_finish = QCheckBox("Finish mode (finish / nextLap)")
        slots_layout.addWidget(self._chk_finish, _N_SLOTS + 4, 0, 1, 6)

        # FINISH ALL label
        self._lbl_finish_all = QLabel("FINISH ALL")
        self._lbl_finish_all.setStyleSheet(
            "color: red; font-size: 18pt; font-weight: bold;"
        )
        self._lbl_finish_all.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_finish_all.setVisible(False)
        slots_layout.addWidget(self._lbl_finish_all, _N_SLOTS + 5, 0, 1, 6)
        slots_layout.setRowStretch(_N_SLOTS + 6, 1)

        left = QVBoxLayout()
        left.addWidget(slots_box)
        # The action log stays as it was, as the first tab; the others show files.
        self._tabs = QTabWidget()
        self._log = QListWidget()
        self._tabs.addTab(self._log, "Action log")
        self._tabs.addTab(self._build_crossings_tab(), "Crossings")
        self._tabs.addTab(self._build_chips_tab(), "Chips")
        left.addWidget(self._tabs)
        root.addLayout(left)

        # ---- RIGHT panel ----
        right = QVBoxLayout()
        right.addWidget(self._build_source_box())

        # Group start section
        grp_box = QGroupBox("Group start")
        grp_layout = QVBoxLayout(grp_box)
        self._combo_group = QComboBox()
        self._combo_group.setEditable(True)
        grp_layout.addWidget(self._combo_group)
        grp_btn_row = QHBoxLayout()
        self._edit_group_time = QLineEdit()
        self._edit_group_time.setText("0 00:00:00.000")
        self._edit_group_time.setMinimumWidth(180)
        grp_btn_row.addWidget(self._edit_group_time)
        self._btn_start_group = QPushButton("Start")
        self._btn_start_group.clicked.connect(self._on_start_group)
        grp_btn_row.addWidget(self._btn_start_group)
        self._btn_save_group = QPushButton("Save group")
        self._btn_save_group.clicked.connect(self._on_save_group)
        grp_btn_row.addWidget(self._btn_save_group)
        grp_layout.addLayout(grp_btn_row)
        right.addWidget(grp_box)

        # DSQ section
        dsq_row = QHBoxLayout()
        dsq_row.addWidget(QLabel("DSQ number:"))
        self._edit_dsq = QLineEdit()
        self._edit_dsq.setFixedWidth(70)
        dsq_row.addWidget(self._edit_dsq)
        btn_dsq = QPushButton("DSQ")
        btn_dsq.clicked.connect(self._on_dsq)
        dsq_row.addWidget(btn_dsq)
        dsq_row.addWidget(QLabel("DSQ reason:"))
        self._edit_dsq_reason = QLineEdit()
        self._edit_dsq_reason.setPlaceholderText("optional reason")
        dsq_row.addWidget(self._edit_dsq_reason)
        right.addLayout(dsq_row)

        # Second user section
        second_row = QHBoxLayout()
        self._chk_second_user = QCheckBox("Second user mode")
        self._chk_second_user.toggled.connect(self._on_second_user_toggled)
        second_row.addWidget(self._chk_second_user)
        self._btn_second_user = QPushButton("FINISH")
        self._btn_second_user.setFixedHeight(50)
        self._btn_second_user.setEnabled(False)
        self._btn_second_user.clicked.connect(self._on_finish_second_user)
        self._btn_second_user.setStyleSheet("font-size: 14pt; font-weight: bold;")
        second_row.addWidget(self._btn_second_user)
        right.addLayout(second_row)

        # Max laps + timer
        laps_row = QHBoxLayout()
        laps_row.addWidget(QLabel("Max laps:"))
        self._spin_max_laps = QSpinBox()
        self._spin_max_laps.setRange(1, 999)
        self._spin_max_laps.setValue(99)
        laps_row.addWidget(self._spin_max_laps)
        laps_row.addStretch()
        self._lbl_timer = QLabel("00:00:00")
        self._lbl_timer.setStyleSheet("font-size: 16pt; font-weight: bold;")
        laps_row.addWidget(self._lbl_timer)
        right.addLayout(laps_row)

        # File paths
        file_box = QGroupBox("Files")
        file_layout = QGridLayout(file_box)
        file_layout.addWidget(QLabel("Results:"), 0, 0)
        self._edit_results_file = QLineEdit()
        self._edit_results_file.textChanged.connect(self._refresh_crossings)
        file_layout.addWidget(self._edit_results_file, 0, 1)
        btn_results = QPushButton("...")
        btn_results.setFixedWidth(30)
        btn_results.clicked.connect(self._on_select_results_file)
        file_layout.addWidget(btn_results, 0, 2)
        file_layout.addWidget(QLabel("Groups:"), 1, 0)
        self._edit_groups_file = QLineEdit()
        file_layout.addWidget(self._edit_groups_file, 1, 1)
        btn_groups = QPushButton("...")
        btn_groups.setFixedWidth(30)
        btn_groups.clicked.connect(self._on_select_groups_file)
        file_layout.addWidget(btn_groups, 1, 2)
        self._chk_freeze = QCheckBox("Freeze file paths")
        self._chk_freeze.toggled.connect(self._on_freeze_toggled)
        file_layout.addWidget(self._chk_freeze, 2, 0, 1, 3)
        self._chk_disable_backup = QCheckBox("Disable backup")
        file_layout.addWidget(self._chk_disable_backup, 3, 0, 1, 3)
        self._chk_summer_time = QCheckBox("Summer time (+1h)")
        file_layout.addWidget(self._chk_summer_time, 4, 0, 1, 3)
        btn_load_config = QPushButton("Load race config")
        btn_load_config.clicked.connect(self._on_load_config)
        file_layout.addWidget(btn_load_config, 5, 0, 1, 3)
        right.addWidget(file_box)

        # HTTP (site upload) section
        http_box = QGroupBox("Site upload (HTTP)")
        http_layout = QGridLayout(http_box)
        http_layout.addWidget(QLabel("Site URL:"), 0, 0)
        self._edit_site_url = QLineEdit()
        self._edit_site_url.textChanged.connect(
            lambda t: self._save_http_field("site_url", t)
        )
        http_layout.addWidget(self._edit_site_url, 0, 1, 1, 2)
        http_layout.addWidget(QLabel("Token:"), 1, 0)
        self._edit_token = QLineEdit()
        self._edit_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_token.textChanged.connect(
            lambda t: self._save_http_field("token", t)
        )
        http_layout.addWidget(self._edit_token, 1, 1, 1, 2)
        http_layout.addWidget(QLabel("Device ID:"), 2, 0)
        self._edit_device_id = QLineEdit()
        self._edit_device_id.textChanged.connect(
            lambda t: self._save_http_field("device_id", t)
        )
        http_layout.addWidget(self._edit_device_id, 2, 1)
        btn_gen_device = QPushButton("Generate")
        btn_gen_device.clicked.connect(self._on_generate_device_id)
        http_layout.addWidget(btn_gen_device, 2, 2)
        http_layout.addWidget(QLabel("Point number (0 = finish):"), 3, 0, 1, 2)
        self._spin_point = QSpinBox()
        self._spin_point.setRange(0, 10000)
        self._spin_point.valueChanged.connect(
            lambda v: self._save_http_field("point_number", str(v))
        )
        http_layout.addWidget(self._spin_point, 3, 2)
        self._btn_get_groups = QPushButton("Get groups")
        self._btn_get_groups.clicked.connect(self._on_get_groups)
        http_layout.addWidget(self._btn_get_groups, 4, 0, 1, 3)
        right.addWidget(http_box)

        root.addLayout(right)
        self._chk_freeze.setChecked(True)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _action(self) -> str:
        return "finish" if self._chk_finish.isChecked() else "nextLap"

    def _results_path(self) -> str:
        return self._edit_results_file.text().strip()

    def _groups_path(self) -> str:
        return self._edit_groups_file.text().strip()

    def _slot_numbers(self) -> list[str]:
        return [e.text() for e in self._number_edits]

    def _update_crosses(self) -> None:
        # From the results file, not the action log: an edit or a deletion changes
        # the file, and the counts must follow it (also after a restart).
        current_slots = self._slot_numbers()
        max_laps = self._spin_max_laps.value()
        show_finish_all = False
        for i, lbl in enumerate(self._cross_labels):
            n = self._number_edits[i].text()
            count = (self._result_counts[n] + current_slots.count(n)) if n else 0
            lbl.setText(str(count))
            if n and count >= max_laps:
                show_finish_all = True
        self._lbl_finish_all.setVisible(show_finish_all)

    def _write_to_finish(self, number: str, time_str: str, quiet: bool = False) -> bool:
        if not number and not time_str:
            return False
        result_line = f"{number}#{time_str}#"
        path = self._results_path()
        ok = append_to_finish_file(path, number, time_str)
        if not ok:
            msg = (
                "Results file path is not configured."
                if not path
                else f"Cannot open results file:\n{path}"
            )
            if quiet:  # a device caused it: no dialog in the middle of a race
                self._append_log(f"not written: {result_line} ({msg})")
            else:
                QTimer.singleShot(
                    0, lambda m=msg: QMessageBox.warning(self, "File error", m)
                )
            return False
        self._log.addItem(result_line)
        self._log.scrollToBottom()
        self._schedule_finish_upload()
        self._note_written(result_line)
        return True

    # ------------------------------------------------------------------
    # event source: by hand, light beam or chips through a connector
    # ------------------------------------------------------------------

    def _build_source_box(self) -> QGroupBox:
        box = QGroupBox("Event source")
        grid = QGridLayout(box)
        self._combo_source = QComboBox()
        for key, label in (
            ("hand", "By hand"),
            ("beam", "Light beam"),
            ("chips", "Timing chips"),
        ):
            self._combo_source.addItem(label, key)
        self._combo_connector = QComboBox()
        self._edit_connector_settings = QLineEdit()
        self._btn_source_start = QPushButton("Start")
        self._btn_source_stop = QPushButton("Stop")
        self._lbl_source_state = QLabel("stopped")
        self._lbl_test_data = QLabel("TEST CONNECTOR: its crossings are test data")
        self._lbl_test_data.setStyleSheet("color: red; font-weight: bold;")
        self._lbl_test_data.setVisible(False)
        grid.addWidget(QLabel("Source:"), 0, 0)
        grid.addWidget(self._combo_source, 0, 1, 1, 2)
        grid.addWidget(QLabel("Device:"), 1, 0)
        grid.addWidget(self._combo_connector, 1, 1, 1, 2)
        grid.addWidget(QLabel("Settings:"), 2, 0)
        grid.addWidget(self._edit_connector_settings, 2, 1, 1, 2)
        grid.addWidget(self._btn_source_start, 3, 1)
        grid.addWidget(self._btn_source_stop, 3, 2)
        grid.addWidget(self._lbl_source_state, 4, 0, 1, 3)
        grid.addWidget(self._lbl_test_data, 5, 0, 1, 3)
        index = self._combo_source.findData(self._sources["source"])
        self._combo_source.setCurrentIndex(max(index, 0))
        self._fill_connectors()
        self._combo_source.currentIndexChanged.connect(self._on_source_changed)
        self._combo_connector.currentIndexChanged.connect(self._on_connector_changed)
        self._edit_connector_settings.editingFinished.connect(
            self._on_connector_settings_edited
        )
        self._btn_source_start.clicked.connect(self._on_source_start)
        self._btn_source_stop.clicked.connect(self._on_source_stop)
        return box

    def _source_kind(self) -> str:
        return str(self._combo_source.currentData())

    def _connector_name(self) -> str:
        return str(self._combo_connector.currentData() or "")

    def _fill_connectors(self) -> None:
        """List the source's connectors; a stub is shown but cannot be chosen."""
        kind = self._source_kind()
        self._combo_connector.blockSignals(True)
        self._combo_connector.clear()
        if kind != "hand":
            for info in connectors_for(kind):
                suffix = "" if info.available else " (not available yet)"
                self._combo_connector.addItem(info.label + suffix, info.name)
                if not info.available:
                    item = self._combo_connector.model().item(  # type: ignore[attr-defined]
                        self._combo_connector.count() - 1
                    )
                    item.setEnabled(False)
            index = self._combo_connector.findData(
                self._sources.get(f"{kind}_connector")
            )
            self._combo_connector.setCurrentIndex(max(index, 0))
        self._combo_connector.blockSignals(False)
        for widget in (
            self._combo_connector,
            self._edit_connector_settings,
            self._btn_source_start,
        ):
            widget.setEnabled(kind != "hand")
        self._show_connector_settings()

    def _show_connector_settings(self) -> None:
        name = self._connector_name()
        if name == "custom":
            self._edit_connector_settings.setText(
                self._sources.get("custom_command", "")
            )
            self._edit_connector_settings.setPlaceholderText(
                "command line of a program that speaks the connector protocol"
            )
        else:
            settings = connector_settings(self._sources, name) if name else {}
            self._edit_connector_settings.setText(json.dumps(settings) if name else "")
            self._edit_connector_settings.setPlaceholderText("")

    def _save_sources(self) -> None:
        if not save_sources(self._sources):
            self._append_log("event source settings could not be saved")

    def _on_source_changed(self) -> None:
        self._stop_source()
        self._sources["source"] = self._source_kind()
        self._save_sources()
        self._fill_connectors()

    def _on_connector_changed(self) -> None:
        self._stop_source()
        self._sources[f"{self._source_kind()}_connector"] = self._connector_name()
        self._save_sources()
        self._show_connector_settings()

    def _on_connector_settings_edited(self) -> None:
        name, text = (
            self._connector_name(),
            self._edit_connector_settings.text().strip(),
        )
        if name == "custom":
            self._sources["custom_command"] = text
        elif name:
            try:
                settings = json.loads(text or "{}")
                if not isinstance(settings, dict):
                    raise ValueError("not an object")
            except ValueError:
                QMessageBox.warning(
                    self, "Event source", 'Settings are JSON, e.g. {"min_s": 5}.'
                )
                self._show_connector_settings()
                return
            set_connector_settings(self._sources, name, settings)
        self._save_sources()

    def _on_source_start(self) -> None:
        kind, name = self._source_kind(), self._connector_name()
        info = find(name)
        if kind == "hand" or info is None or not info.available:
            return
        if not self._results_path():
            QMessageBox.warning(
                self,
                "Event source",
                "Choose the results file first: the device's files go next to it.",
            )
            return
        if name == "custom":
            program = QProcess.splitCommand(self._sources.get("custom_command", ""))
            if not program:
                QMessageBox.warning(
                    self, "Event source", "Type the command line first."
                )
                return
            settings: dict = {}
        elif builtin(name) is not None:
            program, settings = (
                builtin_command(name),
                connector_settings(self._sources, name),
            )
            if name == "dummy-chips" and "riders" not in settings:
                riders: dict[str, list[str]] = {}
                for chip, bib in self._chip_map.bib_of.items():
                    riders.setdefault(bib, []).append(chip)
                settings["riders"] = list(riders.values())
        else:
            return
        self._stop_source()
        host = ConnectorHost(kind, self)
        host.received.connect(self._on_source_event)
        host.state_changed.connect(self._lbl_source_state.setText)
        host.log.connect(self._append_log)
        self._host = host
        self._lbl_test_data.setVisible(info.test)
        host.start(program, settings)

    def _on_source_stop(self) -> None:
        self._stop_source()

    def _stop_source(self, wait: bool = False) -> None:
        host, self._host = self._host, None
        if host is not None:
            host.stop(wait)
            host.deleteLater()
        self._lbl_source_state.setText("stopped")
        self._lbl_test_data.setVisible(False)

    def _event_time(self, time_ms: int | None) -> str:
        """A device event's time as the results file writes it, summer time included."""
        ms = round(time.time() * 1000) if time_ms is None else time_ms
        summer = (
            self._chk_summer_time.isChecked() and time.localtime(ms / 1000).tm_isdst
        )
        return format_time(ms, dst=bool(summer))

    def _on_beam_break(self, event: cp.Break) -> None:
        """Keep the break in the beam file first, then stamp a slot with its time."""
        stamp = self._event_time(event.time_ms)
        record = f"{event.seq}#{stamp}#{field(event.device_time)}#"
        if not append_record(side_file(self._results_path(), "beam_breaks"), record):
            self._append_log(f"beam break not kept in the beam file: {record}")
        if not self._stamp_first_empty_slot(stamp, take_next=False, quiet=True):
            self._append_log(
                f"beam break {stamp} not stamped: slot 1 could not be written, "
                "so no slot was free; the break is in the beam file"
            )

    def _on_source_event(self, event: object) -> None:
        if isinstance(event, cp.Read):
            self._on_chip_read(event)
        elif isinstance(event, cp.Break):
            self._on_beam_break(event)
        elif isinstance(event, cp.Status):
            self._append_log(f"source {event.state} {event.detail}".rstrip())
        elif isinstance(event, cp.Error):
            self._append_log(f"source error: {event.message}")

    # ------------------------------------------------------------------
    # chips: the start protocol file and the map from chip to bib
    # ------------------------------------------------------------------

    def _build_chips_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        row.addWidget(QLabel("Start protocol:"))
        self._edit_start_protocol = QLineEdit(self._sources["start_protocol"])
        self._edit_start_protocol.editingFinished.connect(self._on_start_protocol_path)
        row.addWidget(self._edit_start_protocol)
        browse = QPushButton("...")
        browse.setFixedWidth(30)
        browse.clicked.connect(self._on_select_start_protocol)
        row.addWidget(browse)
        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self._reload_chip_map)
        row.addWidget(reload_button)
        layout.addLayout(row)
        # Only on this button: nothing is ever downloaded on its own (constitution IV).
        self._btn_download_start = QPushButton("Download start protocol from the site")
        self._btn_download_start.clicked.connect(self._on_download_start_protocol)
        layout.addWidget(self._btn_download_start)
        self._fetch_worker: _FetchWorker | None = None
        self._lbl_chip_map = QLabel()
        layout.addWidget(self._lbl_chip_map)
        dead_row = QHBoxLayout()
        dead_row.addWidget(QLabel("Dead time, s (one pass):"))
        self._spin_dead_time = QSpinBox()
        self._spin_dead_time.setRange(1, 120)
        self._spin_dead_time.setValue(dead_time_s(self._sources))
        self._spin_dead_time.valueChanged.connect(self._on_dead_time)
        dead_row.addWidget(self._spin_dead_time)
        dead_row.addStretch(1)
        layout.addLayout(dead_row)
        self._lbl_unwritten = QLabel()
        self._lbl_unwritten.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self._lbl_unwritten)
        layout.addWidget(QLabel("Chips on two bibs (bound to neither):"))
        self._list_conflicts = QListWidget()
        layout.addWidget(self._list_conflicts)
        layout.addWidget(
            QLabel("Unknown chips (timed once the start protocol has them):")
        )
        self._list_unknown = QListWidget()
        layout.addWidget(self._list_unknown)
        self._unknown_timer = QTimer(self)
        self._unknown_timer.setSingleShot(True)
        self._unknown_timer.timeout.connect(self._show_unknown)
        report_button = QPushButton("Chip report")
        report_button.clicked.connect(self._on_chip_report)
        layout.addWidget(report_button)
        self._chip_map = ChipMap()
        # Chip state belongs to one results file; loaded when that file is in use.
        self._chip_timing: ChipTiming | None = None
        self._chip_timing_for = ""
        self._chip_state_dirty = False  # never write a state nothing changed
        self._chip_state_timer = QTimer(self)
        self._chip_state_timer.setSingleShot(True)
        self._chip_state_timer.timeout.connect(self._save_chip_state)
        self._unwritten_timer = QTimer(self)
        self._unwritten_timer.setInterval(1000)
        self._unwritten_timer.timeout.connect(self._retry_unwritten)
        return page

    def _on_start_protocol_path(self) -> None:
        self._sources["start_protocol"] = self._edit_start_protocol.text().strip()
        self._save_sources()
        self._reload_chip_map()

    def _on_select_start_protocol(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Start protocol file")
        if path:
            self._edit_start_protocol.setText(path)
            self._on_start_protocol_path()

    def _reload_chip_map(self) -> None:
        """Build the chip map from the start protocol file as it is now."""
        path = self._sources["start_protocol"]
        lines = read_start_protocol(path)
        self._chip_map = build_chip_map(lines or [])
        if self._chip_timing is not None:
            self._write_chip_crossings(self._chip_timing.set_map(self._chip_map))
            self._show_unknown()
        self._list_conflicts.clear()
        for chip, bibs in sorted(self._chip_map.conflicts.items()):
            self._list_conflicts.addItem(f"{chip}: bibs {', '.join(bibs)}")
        if lines is None:
            text = f"No start protocol file: {path or '(none chosen)'}"
        else:
            text = (
                f"{len(self._chip_map.bib_of)} chips of {self._chip_map.bibs} bibs "
                f"from {path}; {len(self._chip_map.conflicts)} on two bibs"
            )
        self._lbl_chip_map.setText(text)

    def _on_download_start_protocol(self) -> None:
        site = self._http_cfg.get("site_url", "").strip()
        token = self._http_cfg.get("token", "").strip()
        if not site or not token:
            QMessageBox.warning(
                self, "Start protocol", "Site URL and Token must be set first."
            )
            return
        worker = _FetchWorker(fetch_start_list, site, token)
        worker.done.connect(self._on_start_list)
        self._fetch_worker = worker
        self._btn_download_start.setEnabled(False)
        worker.start()

    def _on_start_list(self, result: object) -> None:
        """Keep the previous file, write the new one in one step, rebuild the map."""
        if self._fetch_worker is not None:
            self._fetch_worker.wait()
            self._fetch_worker = None
        self._btn_download_start.setEnabled(True)
        if not isinstance(result, list):  # the error the download ended with
            QMessageBox.warning(self, "Start protocol", f"Nothing changed: {result}")
            return
        try:
            backup = rewrite_results(
                self._sources["start_protocol"], result, stem="start"
            )
        except OSError as exc:
            QMessageBox.warning(self, "Start protocol", f"Nothing changed: {exc}")
            return
        self._reload_chip_map()
        self._append_log(
            f"start protocol downloaded: {len(result)} line(s); "
            f"{self._lbl_chip_map.text()}; previous file kept as {backup.name}"
        )

    def _on_chip_report(self) -> None:
        """Write how well each chip was read next to the results file (Story 6)."""
        results = self._results_path()
        if not results:
            QMessageBox.warning(self, "Chip report", "Choose the results file first.")
            return
        raw = read_file_lines(side_file(results, "chip_reads"))
        reads = [read for line in raw if (read := raw_read(line)) is not None]
        lines = chip_report(reads, self._chip_map, self._spin_dead_time.value() * 1000)
        path = app_path(side_file(results, "chip_report"))
        try:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        except OSError as exc:
            QMessageBox.warning(self, "Chip report", f"Not written: {exc}")
            return
        self._append_log(f"chip report written: {path}")
        QMessageBox.information(self, "Chip report", f"Written to {path}")

    def _on_dead_time(self, seconds: int) -> None:
        self._sources["dead_time_s"] = str(seconds)
        self._save_sources()
        if self._chip_timing is not None:
            self._chip_timing.dead_ms = seconds * 1000  # for reads from now on

    def _timing(self) -> ChipTiming:
        """The chip state of the results file in use; loaded, or switched, here.

        On loading, raw reads appended after the state was last saved -- a crash in
        between -- are replayed, and crossings still waiting are written.
        """
        path = self._results_path()
        if self._chip_timing is not None and self._chip_timing_for == path:
            return self._chip_timing
        if self._chip_timing is not None:
            self._save_chip_state()
        dead_ms = self._spin_dead_time.value() * 1000
        raw = read_file_lines(side_file(path, "chip_reads")) if path else []
        timing = load_chip_state(side_file(path, "chip_state", "json"), dead_ms)
        # More reads processed than the raw file holds: a state left from another
        # race, whose waiting crossings must not go into this results file.
        stale = timing is not None and timing.processed_lines > len(raw)
        if timing is None or stale:
            timing = rebuilt_timing(raw, self._chip_map, dead_ms)
            if raw or stale:
                why = "belongs to another raw reads file" if stale else "lost"
                self._append_log(
                    f"chip state {why}: rebuilt from {len(raw)} raw read(s) without "
                    "writing their crossings again; check the results file"
                )
                self._chip_state_dirty = True
        self._chip_timing, self._chip_timing_for = timing, path
        # The map may have changed while the program was closed.
        made = timing.set_map(self._chip_map)
        for line in raw[timing.processed_lines :]:
            read = raw_read(line)
            if read is not None:
                made += timing.on_read(*read)
        if len(raw) > timing.processed_lines:
            timing.processed_lines = len(raw)
            self._chip_state_dirty = True
        # A crash between writing a crossing and saving the state leaves it in the
        # results file, still waiting or made again here: never written twice.
        done = {tuple(line.split("#")[:2]) for line in read_results(path)}
        waiting = [
            line for line in timing.unwritten if tuple(line.split("#")[:2]) not in done
        ]
        if len(waiting) < len(timing.unwritten):
            timing.unwritten = waiting
            self._chip_state_dirty = True
        self._write_chip_crossings(
            [(bib, at) for bib, at in made if (bib, scale_time(at)) not in done]
        )
        self._retry_unwritten()
        self._save_chip_state()  # whatever loading changed, unless nothing did
        return timing

    def _on_chip_read(self, event: cp.Read) -> None:
        """Keep the read in the raw file first, then turn it into crossings."""
        chip = normalise_chip(event.chip)
        if not chip:
            self._append_log(f"chip read without a usable id: {event.chip!r}")
            return
        stamp = self._event_time(event.time_ms)
        if not self._results_path():  # cleared while the source runs
            self._append_log(f"chip read {chip} {stamp} not timed: no results file")
            return
        timing = self._timing()
        rssi = "" if event.rssi is None else f"{event.rssi:g}"
        record = (
            f"{chip}#{stamp}#{field(event.device_time)}#{field(event.antenna)}#"
            f"{rssi}#{field(event.reader)}#"
        )
        if append_record(side_file(self._results_path(), "chip_reads"), record):
            timing.processed_lines += 1
        else:
            self._append_log(f"chip read not kept in the raw file: {record}")
        at = parse_time(stamp)
        if at is not None:
            self._write_chip_crossings(timing.on_read(chip, at))
            if (
                chip not in timing.chip_map.bib_of
                and not self._unknown_timer.isActive()
            ):
                self._unknown_timer.start(500)  # a burst refreshes the list once
        self._chip_state_dirty = True
        self._chip_state_timer.start(1000)

    def _show_unknown(self) -> None:
        self._list_unknown.clear()
        if self._chip_timing is None:
            return
        for chip, (first, last, count) in sorted(self._chip_timing.unknown().items()):
            self._list_unknown.addItem(
                f"{chip}: {count} read(s), first {scale_time(first)}, "
                f"last {scale_time(last)}"
            )

    def _write_chip_crossings(self, made: list[tuple[str, int]]) -> None:
        if not made or self._chip_timing is None:
            return
        for bib, at in made:
            self._chip_timing.unwritten.append(
                f"{bib}#{scale_time(at)}#{self._action()}#"
            )
        self._chip_state_dirty = True
        self._retry_unwritten()
        self._save_chip_state()  # a crossing made is recorded at once

    def _retry_unwritten(self) -> None:
        """Write waiting chip crossings in order; never a dialog (constitution III).

        Only into the results file they belong to: after a switch to another file
        they wait in their own state until that file is in use again.
        """
        timing = self._chip_timing
        if timing is None or self._chip_timing_for != self._results_path():
            return
        written = False
        while timing.unwritten:
            line = timing.unwritten[0]
            number, _, rest = line.partition("#")
            if not append_to_finish_file(self._results_path(), number, rest[:-1]):
                if not self._unwritten_timer.isActive():
                    self._append_log(
                        f"chip crossing waits: results file not writable ({line})"
                    )
                    self._unwritten_timer.start()
                break
            timing.unwritten.pop(0)
            self._chip_state_dirty = True
            written = True
            self._log.addItem(line)
            self._log.scrollToBottom()
            self._schedule_finish_upload()
            self._note_written(line)
        if written:
            self._update_crosses()
            self._save_chip_state()  # a restart must not write them a second time
        if not timing.unwritten:
            self._unwritten_timer.stop()
        waiting = len(timing.unwritten)
        self._lbl_unwritten.setText(
            f"{waiting} chip crossing(s) wait for the results file" if waiting else ""
        )

    def _save_chip_state(self) -> None:
        self._chip_state_timer.stop()
        if not self._chip_state_dirty:
            return
        self._chip_state_dirty = False
        if self._chip_timing is not None and self._chip_timing_for:
            path = side_file(self._chip_timing_for, "chip_state", "json")
            if not save_chip_state(path, self._chip_timing):
                self._append_log("chip state not saved; trying again in 5 s")
                self._chip_state_dirty = True
                self._chip_state_timer.start(5000)

    # ------------------------------------------------------------------
    # crossings: the results file, corrected by hand
    # ------------------------------------------------------------------

    def _build_crossings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self._crossings = QListWidget()
        # The results file's lines and how often each number crossed: re-read after a
        # rewrite or a path change, kept up to date as lines are appended.
        self._result_lines: list[str] = []
        self._result_counts: Counter[str] = Counter()
        layout.addWidget(self._crossings)
        row = QHBoxLayout()
        for text, slot in (
            ("Add", self._on_add_crossing),
            ("Edit", self._on_edit_crossing),
            ("Delete", self._on_delete_crossing),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        layout.addLayout(row)
        return page

    def _refresh_crossings(self) -> None:
        """Re-read the results file: after a rewrite or a change of its path."""
        self._result_lines = read_results(self._results_path())
        self._result_counts = Counter(line.split("#")[0] for line in self._result_lines)
        self._crossings.clear()
        self._crossings.addItems(self._result_lines)
        self._crossings.scrollToBottom()

    def _note_written(self, line: str) -> None:
        """A line appended to the results file: shown and counted without a re-read,
        which a mass finish of chip crossings would pay for once per crossing."""
        self._result_lines.append(line)
        self._result_counts[line.split("#")[0]] += 1
        self._crossings.addItem(line)
        self._crossings.scrollToBottom()

    def _ask_crossing(
        self, number: str, time_str: str, action: str
    ) -> tuple[str, str, str] | None:
        """Ask for a crossing until it is valid or the judge cancels."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Crossing")
        form = QFormLayout(dialog)
        edit_number, edit_time = QLineEdit(number), QLineEdit(time_str)
        combo = QComboBox()
        combo.setEditable(True)  # a DSQ line keeps its own "DSQ: reason"
        combo.addItems(ACTIONS)
        combo.setCurrentText(action)
        form.addRow("Number:", edit_number)
        form.addRow("Time:", edit_time)
        form.addRow("Action:", combo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        while dialog.exec() == QDialog.DialogCode.Accepted:
            got = (
                edit_number.text().strip(),
                edit_time.text().strip(),
                combo.currentText(),
            )
            problem = crossing_problem(*got)
            if problem is None:
                return got
            QMessageBox.warning(self, "Crossing", problem)
        return None

    def _crossing_lines(self) -> list[str] | None:
        """The results file now, or None (with a message) when there is no path."""
        if not self._results_path():
            QMessageBox.warning(
                self, "Crossings", "Results file path is not configured."
            )
            return None
        return read_results(self._results_path())

    def _selected_crossing(self, lines: list[str]) -> int:
        """The selected line's place in the file as it is now, or -1 (said aloud)."""
        row = self._crossings.currentRow()
        item = self._crossings.currentItem()
        if row < 0 or item is None:
            return -1
        if row >= len(lines) or lines[row] != item.text():
            QMessageBox.warning(
                self, "Crossings", "The results file changed meanwhile; try again."
            )
            self._refresh_crossings()
            return -1
        return row

    def _still_holding(self, row: int, line: str) -> list[str] | None:
        """The results file read again after a dialog, if line is still its row-th.

        A device appends crossings while a dialog waits, so a change is made to the
        file as it is then, never to a copy read before the dialog.
        """
        lines = read_results(self._results_path())
        if row < len(lines) and lines[row] == line:
            return lines
        QMessageBox.warning(
            self, "Crossings", "The results file changed meanwhile; try again."
        )
        self._refresh_crossings()
        return None

    def _on_add_crossing(self) -> None:
        if self._crossing_lines() is None:
            return
        now = get_current_time(summer_time=self._chk_summer_time.isChecked())
        got = self._ask_crossing("", now, self._action())
        if got is not None:
            line = crossing_line(*got)
            lines = read_results(self._results_path())  # as it is after the dialog
            self._change_results([*lines, line], f"added {line}")

    def _on_edit_crossing(self) -> None:
        lines = self._crossing_lines()
        row = -1 if lines is None else self._selected_crossing(lines)
        if lines is None or row < 0:
            return
        old = lines[row]
        number, time_str, action = ([*old.split("#"), "", ""])[:3]
        got = self._ask_crossing(number, time_str, action)
        lines = None if got is None else self._still_holding(row, old)
        if got is not None and lines is not None:
            new = crossing_line(*got)
            changed = [*lines[:row], new, *lines[row + 1 :]]
            self._change_results(changed, f"changed {old} to {new}")

    def _on_delete_crossing(self) -> None:
        lines = self._crossing_lines()
        row = -1 if lines is None else self._selected_crossing(lines)
        if lines is None or row < 0:
            return
        old = lines[row]
        reply = QMessageBox.question(self, "Crossings", f"Delete {old}?")
        if reply != QMessageBox.StandardButton.Yes:
            return
        lines = self._still_holding(row, old)
        if lines is not None:
            changed = [*lines[:row], *lines[row + 1 :]]
            self._change_results(changed, f"deleted {old}")

    def _change_results(self, lines: list[str], what: str) -> None:
        """Rewrite the results file after its backup, then log, show and upload it."""
        try:
            backup = rewrite_results(self._results_path(), lines)
        except OSError as exc:
            QMessageBox.warning(self, "Crossings", f"Nothing changed: {exc}")
            return
        self._log.addItem(f"{what} (previous file kept as {backup.name})")
        self._log.scrollToBottom()
        self._refresh_crossings()
        self._schedule_finish_upload()
        self._update_crosses()

    def _save_backup_if_enabled(self) -> None:
        if self._chk_disable_backup.isChecked():
            return
        ts = int(time.time())
        path = str(app_path("temp", f"stc{ts}.txt"))
        log_items = [self._log.item(i).text() for i in range(self._log.count())]
        slots = [
            (self._number_edits[i].text(), self._time_edits[i].text())
            for i in range(_N_SLOTS)
        ]
        save_backup(
            path=path,
            log_items=log_items,
            group_number=self._combo_group.currentText(),
            group_time=self._edit_group_time.text(),
            slots=slots,
            finish_mode=self._chk_finish.isChecked(),
        )

    def _load_config(self, path: str) -> None:
        groups, results_file, group_start_file = load_config(path)
        self._combo_group.clear()
        for g in groups:
            self._combo_group.addItem(g)
        if results_file:
            self._edit_results_file.setText(results_file)
        if group_start_file:
            self._edit_groups_file.setText(group_start_file)

    def _on_get_groups(self) -> None:
        """Fetch the group list from the site and replace the Group start dropdown.

        Only a failure (missing URL/token, offline/timeout, or a bad response) leaves
        the dropdown unchanged. A successful response is applied as-is -- including an
        empty list, which clears the dropdown so a start with no groups does not keep
        showing a previous start's groups.
        """
        site = self._http_cfg.get("site_url", "").strip()
        token = self._http_cfg.get("token", "").strip()
        if not site or not token:
            QMessageBox.warning(self, "Get groups", "Site URL and Token must be set.")
            return
        try:
            groups = fetch_groups(site, token)
        except ValueError as exc:
            QMessageBox.warning(self, "Get groups", f"Could not load groups:\n{exc}")
            return
        current = self._combo_group.currentText()
        self._combo_group.clear()
        for group in groups:
            self._combo_group.addItem(group)
        idx = self._combo_group.findText(current)
        if idx >= 0:
            self._combo_group.setCurrentIndex(idx)
        saved = save_config(
            self._config_path,
            groups,
            self._results_path(),
            self._groups_path(),
        )
        if not saved:
            QMessageBox.warning(
                self,
                "Get groups",
                f"Loaded {len(groups)} group(s), but could not save the list to "
                f"{self._config_path}.",
            )
            return
        QMessageBox.information(self, "Get groups", f"Loaded {len(groups)} group(s).")

    def _start_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start(1)

    # ------------------------------------------------------------------
    # site upload (HTTP)
    # ------------------------------------------------------------------

    def _append_log(self, text: str) -> None:
        self._log.addItem(text)
        self._log.scrollToBottom()

    def _apply_http_config_to_ui(self) -> None:
        self._edit_site_url.setText(self._http_cfg.get("site_url", ""))
        self._edit_token.setText(self._http_cfg.get("token", ""))
        self._edit_device_id.setText(self._http_cfg.get("device_id", ""))
        try:
            self._spin_point.setValue(int(self._http_cfg.get("point_number", "0")))
        except ValueError:
            self._spin_point.setValue(0)

    def _save_http_field(self, key: str, value: str) -> None:
        self._http_cfg[key] = value.strip()
        self._http_save_timer.start(500)

    def _flush_http_config(self) -> None:
        save_http_config(self._http_cfg)

    def _on_generate_device_id(self) -> None:
        import uuid

        self._edit_device_id.setText(str(uuid.uuid4()))  # textChanged persists it

    def _next_revision(self, key: str) -> int:
        """Increment and persist a per-stream revision counter; return the new value."""
        try:
            rev = int(self._http_cfg.get(key, "0")) + 1
        except ValueError:
            rev = 1
        self._http_cfg[key] = str(rev)
        save_http_config(self._http_cfg)
        return rev

    def _start_upload(self, func, *args) -> None:
        worker = _UploadWorker(func, *args)
        worker.log.connect(self._append_log)
        worker.finished.connect(
            lambda w=worker: (
                self._upload_workers.remove(w) if w in self._upload_workers else None
            )
        )
        self._upload_workers.append(worker)
        worker.start()

    def _schedule_finish_upload(self) -> None:
        # Collapse a batch of writes into a single upload shortly after the last one.
        self._finish_upload_timer.start(400)

    def _upload_finish_stream(self) -> None:
        """Push results-file snapshot: point 0 -> finish endpoint, else remote point."""
        site = self._http_cfg.get("site_url", "")
        token = self._http_cfg.get("token", "")
        device = self._http_cfg.get("device_id", "")
        if not site or not token or not device:
            return
        path = self._results_path()
        rev = self._next_revision("rev_finish")
        try:
            point = int(self._http_cfg.get("point_number", "0"))
        except ValueError:
            point = 0
        if point == 0:
            self._start_upload(
                lambda: upload_finish_times(
                    site, token, device, read_file_lines(path), rev
                )
            )
        else:
            self._start_upload(
                lambda: upload_remote_points(
                    site, token, device, point, read_file_lines(path), rev
                )
            )

    def _upload_group_stream(self) -> None:
        """Push the current groups-file snapshot to the group-times endpoint."""
        site = self._http_cfg.get("site_url", "")
        token = self._http_cfg.get("token", "")
        device = self._http_cfg.get("device_id", "")
        if not site or not token or not device:
            return
        path = self._groups_path()
        rev = self._next_revision("rev_group")
        self._start_upload(
            lambda: upload_group_times(site, token, device, read_file_lines(path), rev)
        )

    # ------------------------------------------------------------------
    # slots
    # ------------------------------------------------------------------

    def _on_timer_tick(self) -> None:
        if self._show_time:
            summer = self._chk_summer_time.isChecked()
            self._lbl_timer.setText(get_current_time(accuracy=0, summer_time=summer))
        else:
            ms = int((time.time() - int(time.time())) * 1000)
            if ms == 0:
                self._timer.setInterval(1000)
                self._show_time = True

    def _on_number_changed(self) -> None:
        self._update_crosses()

    def _on_finish(self, idx: int) -> None:
        t = get_current_time(summer_time=self._chk_summer_time.isChecked())
        self._time_edits[idx].setText(t + "#" + self._action())
        self._save_backup_if_enabled()
        self._update_crosses()
        if idx + 1 < _N_SLOTS:
            self._number_edits[idx + 1].setFocus()

    def _on_save(self, idx: int) -> None:
        number = self._number_edits[idx].text()
        time_str = self._time_edits[idx].text()
        if not number and not time_str:
            return
        ok = self._write_to_finish(number, time_str)
        if ok:
            self._number_edits[idx].clear()
            self._time_edits[idx].clear()
        self._save_backup_if_enabled()
        self._update_crosses()

    def _on_finish_all(self) -> None:
        current = get_current_time(summer_time=self._chk_summer_time.isChecked())
        action = self._action()
        for i in range(_N_SLOTS):
            if not self._time_edits[i].text():
                self._time_edits[i].setText(current + "#" + action)
        self._save_backup_if_enabled()
        self._update_crosses()

    def _on_save_and_shift(self) -> None:
        self._shift_fields_up(get_next_competitor=True)
        self._save_backup_if_enabled()

    def _on_save_all_and_empty(self) -> None:
        has_data = any(
            self._number_edits[i].text() or self._time_edits[i].text()
            for i in range(_N_SLOTS)
        )
        if has_data and not self._results_path():
            QMessageBox.warning(
                self,
                "File error",
                "Results file path is not configured.\n"
                "Set the path in the Files section before saving.",
            )
            return
        for i in range(_N_SLOTS):
            number = self._number_edits[i].text()
            time_str = self._time_edits[i].text()
            if number or time_str:
                ok = self._write_to_finish(number, time_str)
                if ok:
                    self._number_edits[i].clear()
                    self._time_edits[i].clear()
        self._save_backup_if_enabled()
        self._update_crosses()

    def _on_empty_all(self) -> None:
        reply = QMessageBox.question(
            self, "Warning", "Are you sure to empty all fields?"
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for i in range(_N_SLOTS):
            self._number_edits[i].clear()
            self._time_edits[i].clear()
        self._next_number.clear()
        self._update_crosses()

    def _on_start_group(self) -> None:
        self._edit_group_time.setText(
            get_current_time(summer_time=self._chk_summer_time.isChecked())
        )
        self._save_backup_if_enabled()

    def _on_save_group(self) -> None:
        group = self._combo_group.currentText()
        time_str = self._edit_group_time.text()
        if not group or not time_str:
            return
        self._save_backup_if_enabled()
        result_line = f"{group}#{time_str}#"
        ok = append_to_group_file(self._groups_path(), group, time_str)
        if not ok:
            QMessageBox.warning(
                self, "File error", f"Cannot open groups file: {self._groups_path()}"
            )
            return
        self._log.addItem(result_line)
        self._log.scrollToBottom()
        self._upload_group_stream()
        self._combo_group.removeItem(self._combo_group.currentIndex())
        self._combo_group.setCurrentText("")
        # The time stays: groups often set off together, and saving each of them
        # would otherwise mean copying the same start time back in every time.
        # "Start" is what replaces it.

    def _on_dsq(self) -> None:
        number = self._edit_dsq.text().strip()
        if not number:
            return
        t = get_current_time(summer_time=self._chk_summer_time.isChecked())
        time_str = t + "#" + dsq_status(self._edit_dsq_reason.text())
        ok = self._write_to_finish(number, time_str)
        if ok:
            self._edit_dsq.clear()
            self._edit_dsq_reason.clear()
        self._update_crosses()

    def _on_second_user_toggled(self, checked: bool) -> None:
        self._btn_second_user.setEnabled(checked)

    def _on_finish_second_user(self) -> None:
        current = get_current_time(summer_time=self._chk_summer_time.isChecked())
        self._stamp_first_empty_slot(current, take_next=True)

    def _stamp_first_empty_slot(
        self, time_str: str, take_next: bool, quiet: bool = False
    ) -> bool:
        """Put time_str into the first slot without a time, shifting when all have one.

        A beam break comes here with take_next False -- the Next field is the judge's
        typing, never a machine's to take -- and quiet, so a write it causes reports
        in the action log rather than in a dialog. False when every slot had a time
        and slot 1 could not be written, so time_str is in no slot.
        """
        stamped = True
        for i in range(_N_SLOTS):
            if not self._time_edits[i].text():
                self._time_edits[i].setText(time_str + "#" + self._action())
                break
        else:
            stamped = self._shift_fields_up(
                get_next_competitor=take_next,
                stamp=None if take_next else time_str,
                quiet=quiet,
            )
        self._check_possibility_to_empty_upper(quiet)
        self._save_backup_if_enabled()
        self._update_crosses()
        return stamped

    def _shift_fields_up(
        self, get_next_competitor: bool, stamp: str | None = None, quiet: bool = False
    ) -> bool:
        number_0 = self._number_edits[0].text()
        time_0 = self._time_edits[0].text()
        if number_0 or time_0:
            ok = self._write_to_finish(number_0, time_0, quiet)
            if not ok:
                return False

        for i in range(_N_SLOTS - 1):
            self._number_edits[i].setText(self._number_edits[i + 1].text())
            self._time_edits[i].setText(self._time_edits[i + 1].text())

        if get_next_competitor:
            self._number_edits[_N_SLOTS - 1].setText(self._next_number.text())
            t = get_current_time(summer_time=self._chk_summer_time.isChecked())
            self._time_edits[_N_SLOTS - 1].setText(t + "#" + self._action())
            self._next_number.clear()
            self._next_number.setFocus()
        elif stamp is not None:
            self._number_edits[_N_SLOTS - 1].clear()
            self._time_edits[_N_SLOTS - 1].setText(stamp + "#" + self._action())
        else:
            self._number_edits[_N_SLOTS - 1].clear()
            self._time_edits[_N_SLOTS - 1].clear()

        self._update_crosses()
        return True

    def _check_possibility_to_empty_upper(self, quiet: bool = False) -> None:
        # A device's stamp moves the slots only while the judge types in one: the
        # slot typed in last, long ago maybe, says nothing about slot 1 being done,
        # and the focus must stay in any other field the judge types in.
        if quiet and self.focusWidget() not in self._number_edits:
            return
        if self._focused_slot != 0 and self._time_edits[0].text():
            shifted = self._shift_fields_up(get_next_competitor=False, quiet=quiet)
            if shifted:
                self._focused_slot = max(0, self._focused_slot - 1)
                self._number_edits[self._focused_slot].setFocus()

    def _on_select_results_file(self) -> None:
        if self._chk_freeze.isChecked():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Select results file")
        if path and path != self._edit_groups_file.text():
            self._edit_results_file.setText(path)
        elif path:
            QMessageBox.warning(
                self,
                "Error",
                "Output files for groups and results must not be the same!",
            )

    def _on_select_groups_file(self) -> None:
        if self._chk_freeze.isChecked():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Select groups file")
        if path and path != self._edit_results_file.text():
            self._edit_groups_file.setText(path)
        elif path:
            QMessageBox.warning(
                self,
                "Error",
                "Output files for groups and results must not be the same!",
            )

    def _on_freeze_toggled(self, checked: bool) -> None:
        for widget in (
            self._edit_results_file,
            self._edit_groups_file,
            self._spin_max_laps,
        ):
            widget.setEnabled(not checked)
        self._lbl_finish_all.setVisible(False)
        self._update_crosses()

    def _on_load_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load groups list")
        if path:
            self._load_config(path)

    def closeEvent(self, event) -> None:  # noqa: N802
        reply = QMessageBox.question(self, "Warning", "Are you sure to exit?")
        if reply == QMessageBox.StandardButton.Yes:
            self._stop_source(wait=True)
            self._save_chip_state()
            self._finish_upload_timer.stop()
            if self._http_save_timer.isActive():
                self._http_save_timer.stop()
                save_http_config(self._http_cfg)
            # Never accept the close while an upload QThread runs: destroying a running
            # QThread aborts the app. Wait until each finishes -- uploads are bounded by
            # the 10s urlopen timeout, so this cannot hang indefinitely.
            for worker in list(self._upload_workers):
                try:
                    worker.log.disconnect()
                    worker.finished.disconnect()
                except RuntimeError:
                    pass
                worker.wait()
            self._upload_workers.clear()
            if self._fetch_worker is not None:  # a download also ends within 10 s
                self._fetch_worker.done.disconnect()
                self._fetch_worker.wait()
            event.accept()
        else:
            event.ignore()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802, C901
        from PySide6.QtCore import QEvent

        if event.type() == QEvent.Type.FocusIn:
            if obj in self._number_edits:
                self._focused_slot = self._number_edits.index(obj)
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if obj in self._number_edits:
                idx = self._number_edits.index(obj)
                if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                    no_time = not self._time_edits[idx].text()
                    if no_time and not self._chk_second_user.isChecked():
                        self._on_finish(idx)
                    next_idx = idx + 1
                    if next_idx < _N_SLOTS:
                        self._number_edits[next_idx].setFocus()
                    else:
                        self._next_number.setFocus()
                    if self._chk_second_user.isChecked():
                        self._check_possibility_to_empty_upper()
                    return True
                if key == Qt.Key.Key_Up and idx > 0:
                    self._number_edits[idx - 1].setFocus()
                    return True
                if key == Qt.Key.Key_Down:
                    if idx + 1 < _N_SLOTS:
                        self._number_edits[idx + 1].setFocus()
                    else:
                        self._next_number.setFocus()
                    return True
            elif obj is self._next_number:
                if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                    if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                        shifted = self._shift_fields_up(True)
                        if shifted and _N_SLOTS > 0:
                            t = get_current_time(
                                summer_time=self._chk_summer_time.isChecked()
                            )
                            self._time_edits[_N_SLOTS - 1].setText(t + "#nextStage")
                    else:
                        self._on_save_and_shift()
                    return True
                if key == Qt.Key.Key_Up:
                    self._number_edits[_N_SLOTS - 1].setFocus()
                    return True
        return super().eventFilter(obj, event)
