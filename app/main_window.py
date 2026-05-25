"""PySide6 main window for Windows Chronometer (SportTimerClient)."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
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
    QVBoxLayout,
    QWidget,
)

from app.models import (
    append_to_finish_file,
    append_to_group_file,
    get_current_time,
    get_number_of_crosses,
    load_config,
    save_backup,
)

_CONFIG_PATH = "data/groupsList.txt"
_N_SLOTS = 5


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Chronometer")
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "app.ico")))
        self._results_file: str = ""
        self._group_start_file: str = ""
        self._show_time: bool = False
        self._setup_ui()
        self._load_config(_CONFIG_PATH)
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

        root.addWidget(slots_box)

        # ---- RIGHT panel ----
        right = QVBoxLayout()

        # Group start section
        grp_box = QGroupBox("Group start")
        grp_layout = QVBoxLayout(grp_box)
        self._combo_group = QComboBox()
        self._combo_group.setEditable(True)
        grp_layout.addWidget(self._combo_group)
        grp_btn_row = QHBoxLayout()
        self._edit_group_time = QLineEdit()
        self._edit_group_time.setReadOnly(True)
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
        dsq_row.addStretch()
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

        # Action log
        right.addWidget(QLabel("Action log:"))
        self._log = QListWidget()
        right.addWidget(self._log)

        root.addLayout(right)

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
        log_items = [self._log.item(i).text() for i in range(self._log.count())]
        current_slots = self._slot_numbers()
        max_laps = self._spin_max_laps.value()
        show_finish_all = False
        for i, lbl in enumerate(self._cross_labels):
            n = self._number_edits[i].text()
            count = get_number_of_crosses(n, log_items, current_slots)
            lbl.setText(str(count))
            if n and count >= max_laps:
                show_finish_all = True
        self._lbl_finish_all.setVisible(show_finish_all)

    def _write_to_finish(self, number: str, time_str: str) -> bool:
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
            QMessageBox.warning(self, "File error", msg)
            return False
        self._log.addItem(result_line)
        self._log.scrollToBottom()
        return True

    def _save_backup_if_enabled(self) -> None:
        if self._chk_disable_backup.isChecked():
            return
        ts = int(time.time())
        path = str(Path("temp") / f"stc{ts}.txt")
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

    def _start_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start(1)

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
        self._combo_group.removeItem(self._combo_group.currentIndex())
        self._combo_group.setCurrentText("")
        self._edit_group_time.clear()

    def _on_dsq(self) -> None:
        number = self._edit_dsq.text().strip()
        if not number:
            return
        t = get_current_time(summer_time=self._chk_summer_time.isChecked())
        time_str = t + "#DSQ"
        ok = self._write_to_finish(number, time_str)
        if ok:
            self._edit_dsq.clear()
        self._update_crosses()

    def _on_second_user_toggled(self, checked: bool) -> None:
        self._btn_second_user.setEnabled(checked)

    def _on_finish_second_user(self) -> None:
        current = get_current_time(summer_time=self._chk_summer_time.isChecked())
        action = self._action()
        filled = False
        for i in range(_N_SLOTS):
            if not self._time_edits[i].text():
                self._time_edits[i].setText(current + "#" + action)
                filled = True
                break
        if not filled:
            self._shift_fields_up(get_next_competitor=True)
        self._check_possibility_to_empty_upper()
        self._save_backup_if_enabled()
        self._update_crosses()

    def _shift_fields_up(self, get_next_competitor: bool) -> bool:
        number_0 = self._number_edits[0].text()
        time_0 = self._time_edits[0].text()
        if number_0 or time_0:
            ok = self._write_to_finish(number_0, time_0)
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
        else:
            self._number_edits[_N_SLOTS - 1].clear()
            self._time_edits[_N_SLOTS - 1].clear()

        self._update_crosses()
        return True

    def _check_possibility_to_empty_upper(self) -> None:
        focused_idx = None
        for i, edit in enumerate(self._number_edits):
            if edit.hasFocus():
                focused_idx = i
                break
        if focused_idx is None:
            focused_idx = 0
        if focused_idx != 0 and self._time_edits[0].text():
            self._shift_fields_up(get_next_competitor=False)

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
            event.accept()
        else:
            event.ignore()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802, C901
        from PySide6.QtCore import QEvent

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
