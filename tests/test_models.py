"""Tests for WindowsChronometer models (pure logic, no GUI)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.models import (
    append_to_finish_file,
    append_to_group_file,
    format_elapsed,
    get_current_time,
    get_number_of_crosses,
    load_config,
    save_backup,
)

# ---------------------------------------------------------------------------
# get_current_time
# ---------------------------------------------------------------------------


class TestGetCurrentTime:
    def test_returns_string(self) -> None:
        t = get_current_time()
        assert isinstance(t, str)
        assert "#" not in t

    def test_has_dot_for_accuracy_3(self) -> None:
        t = get_current_time(3)
        assert "." in t

    def test_no_dot_for_accuracy_0(self) -> None:
        t = get_current_time(0)
        assert "." not in t

    def test_format_day_h_m_s(self) -> None:
        t = get_current_time(0)
        parts = t.split(" ")
        assert len(parts) == 2
        assert ":" in parts[1]

    def test_ms_three_digits(self) -> None:
        t = get_current_time(3)
        frac = t.split(".")[-1]
        assert len(frac) == 3

    def test_applies_timezone_offset(self, monkeypatch) -> None:
        # 90000s UTC = day 1, 01:00:00. UTC+5 (timezone=-18000) -> 06:00:00 local.
        import time as _time
        import types

        monkeypatch.setattr(_time, "time", lambda: 90_000.0)
        monkeypatch.setattr(_time, "timezone", -18_000)  # UTC+5
        monkeypatch.setattr(
            _time, "localtime", lambda: types.SimpleNamespace(tm_isdst=0)
        )
        result = get_current_time(0)
        assert result == "1 6:0:0"

    def test_summer_time_adds_hour_when_dst_active(self, monkeypatch) -> None:
        import time as _time
        import types

        monkeypatch.setattr(_time, "time", lambda: 90_000.0)
        monkeypatch.setattr(_time, "timezone", 0)
        monkeypatch.setattr(
            _time, "localtime", lambda: types.SimpleNamespace(tm_isdst=1)
        )
        result = get_current_time(0, summer_time=True)
        # 90000 + 3600 = 93600 = day 1, 02:00:00
        assert result == "1 2:0:0"

    def test_summer_time_no_extra_hour_when_dst_inactive(self, monkeypatch) -> None:
        import time as _time
        import types

        monkeypatch.setattr(_time, "time", lambda: 90_000.0)
        monkeypatch.setattr(_time, "timezone", 0)
        monkeypatch.setattr(
            _time, "localtime", lambda: types.SimpleNamespace(tm_isdst=0)
        )
        result = get_current_time(0, summer_time=True)
        # DST not active -> no extra hour, stays at day 1, 01:00:00
        assert result == "1 1:0:0"


# ---------------------------------------------------------------------------
# format_elapsed
# ---------------------------------------------------------------------------


class TestFormatElapsed:
    def test_zero(self) -> None:
        assert format_elapsed(0) == "00:00:00"

    def test_one_hour(self) -> None:
        assert format_elapsed(3600) == "01:00:00"

    def test_complex(self) -> None:
        assert format_elapsed(3661) == "01:01:01"

    def test_two_hours(self) -> None:
        assert format_elapsed(7200) == "02:00:00"


# ---------------------------------------------------------------------------
# append_to_finish_file
# ---------------------------------------------------------------------------


class TestAppendToFinishFile:
    def test_creates_and_appends(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        ok = append_to_finish_file(path, "42", "15921 11:35:29.615#nextLap")
        assert ok is True
        content = Path(path).read_text(encoding="utf-8")
        assert "42#15921 11:35:29.615#nextLap#" in content

    def test_appends_multiple(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        append_to_finish_file(path, "1", "T1#nextLap")
        append_to_finish_file(path, "2", "T2#finish")
        content = Path(path).read_text(encoding="utf-8")
        assert "1#T1#nextLap#" in content
        assert "2#T2#finish#" in content

    def test_empty_path_returns_false(self) -> None:
        ok = append_to_finish_file("", "1", "time")
        assert ok is False

    def test_invalid_path_returns_false(self) -> None:
        ok = append_to_finish_file("/nonexistent_root/path/file.txt", "1", "T")
        assert ok is False


# ---------------------------------------------------------------------------
# append_to_group_file
# ---------------------------------------------------------------------------


class TestAppendToGroupFile:
    def test_creates_and_appends(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        ok = append_to_group_file(path, "GroupA", "15921 11:11:5.846")
        assert ok is True
        content = Path(path).read_text(encoding="utf-8")
        assert "GroupA#15921 11:11:5.846#" in content

    def test_empty_path_returns_false(self) -> None:
        assert append_to_group_file("", "G", "T") is False


# ---------------------------------------------------------------------------
# save_backup
# ---------------------------------------------------------------------------


class TestSaveBackup:
    def test_creates_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        slots = [("1", "T1#nextLap"), ("2", "T2#nextLap"), ("", ""), ("", ""), ("", "")]
        ok = save_backup(
            path=path,
            log_items=["1#T0#nextLap#"],
            group_number="GroupA",
            group_time="15921 11:11:5.846",
            slots=slots,
            finish_mode=False,
        )
        assert ok is True
        content = Path(path).read_text(encoding="utf-8")
        assert "1#T0#nextLap#" in content
        assert "GroupA#15921 11:11:5.846#" in content
        assert "1#T1#nextLap#nextLap#" in content

    def test_finish_mode(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = f.name
        slots = [("5", "T5#finish")] + [("", "")] * 4
        ok = save_backup(path, [], "", "", slots, finish_mode=True)
        assert ok is True
        content = Path(path).read_text(encoding="utf-8")
        assert "finish#" in content

    def test_invalid_path_returns_false(self) -> None:
        ok = save_backup(
            "/nonexistent_root/file.txt", [], "", "", [("", "")] * 5, False
        )
        assert ok is False


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def _tmp(self, content: str, encoding: str = "utf-8") -> str:
        f = tempfile.NamedTemporaryFile(
            mode="w", encoding=encoding, suffix=".txt", delete=False
        )
        f.write(content)
        f.close()
        return f.name

    def test_groups_only(self) -> None:
        path = self._tmp("GroupA\nGroupB\nGroupC\n")
        groups, results, group_start = load_config(path)
        assert groups == ["GroupA", "GroupB", "GroupC"]
        assert results == ""
        assert group_start == ""

    def test_config_files_section(self) -> None:
        path = self._tmp("GroupA\nGroupB\nconfigFiles\nresults.txt\ngroups.txt\n")
        groups, results, group_start = load_config(path)
        assert groups == ["GroupA", "GroupB"]
        assert results == "results.txt"
        assert group_start == "groups.txt"

    def test_nonexistent_returns_empty(self) -> None:
        groups, results, group_start = load_config("/nonexistent/path.txt")
        assert groups == []
        assert results == ""
        assert group_start == ""

    def test_config_files_at_start(self) -> None:
        path = self._tmp("configFiles\nresults.txt\ngroups.txt\n")
        groups, results, group_start = load_config(path)
        assert groups == []
        assert results == "results.txt"
        assert group_start == "groups.txt"

    def test_cp1251_encoding(self) -> None:
        content = (
            "\u0413\u0440\u0443\u043f\u043f\u0430 \u0410\n"
            "\u0413\u0440\u0443\u043f\u043f\u0430 \u0411\n"
        )
        path = self._tmp(content, encoding="cp1251")
        groups, _, _ = load_config(path)
        assert len(groups) == 2


# ---------------------------------------------------------------------------
# get_number_of_crosses
# ---------------------------------------------------------------------------


class TestGetNumberOfCrosses:
    def test_empty(self) -> None:
        assert get_number_of_crosses("1", [], []) == 0

    def test_empty_number(self) -> None:
        assert get_number_of_crosses("", ["1#T#nextLap#"], ["1"]) == 0

    def test_from_log(self) -> None:
        log = ["1#T1#nextLap#", "1#T2#nextLap#", "2#T3#nextLap#"]
        assert get_number_of_crosses("1", log, []) == 2
        assert get_number_of_crosses("2", log, []) == 1

    def test_from_slots(self) -> None:
        assert get_number_of_crosses("1", [], ["1", "1", "2", "", ""]) == 2

    def test_combined(self) -> None:
        log = ["1#T1#nextLap#"]
        slots = ["1", "2", "", "", ""]
        assert get_number_of_crosses("1", log, slots) == 2
        assert get_number_of_crosses("2", log, slots) == 1

    def test_partial_match_not_counted(self) -> None:
        log = ["12#T1#nextLap#"]
        assert get_number_of_crosses("1", log, []) == 0
