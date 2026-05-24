"""Pure-logic helpers for Windows Chronometer (no GUI dependencies)."""

from __future__ import annotations

import time
from pathlib import Path

# ---------------------------------------------------------------------------
# time helpers
# ---------------------------------------------------------------------------


def get_current_time(accuracy: int = 3, summer_time: bool = False) -> str:
    """
    Return current local time as 'D H:M:S[.mmm]'.
    accuracy=3 -> include milliseconds; accuracy=0 -> seconds only.
    summer_time=True adds +3600s only when OS DST flag is active
    (C++ checkBoxUseSummerTimeShifting + _ftime dstflag check).
    Port of C++ getCurrentTime(accuracy).
    """
    ts = time.time() - time.timezone  # UTC -> local standard time
    if summer_time and time.localtime().tm_isdst:
        ts += 3600
    days = int(ts // 86400)
    rem = ts - days * 86400
    hours = int(rem // 3600)
    rem -= hours * 3600
    minutes = int(rem // 60)
    seconds = int(rem - minutes * 60)
    ms = int((ts - int(ts)) * 1000)
    ms_str = str(ms).zfill(3)
    base = f"{days} {hours}:{minutes}:{seconds}"
    return base + (f".{ms_str}" if accuracy != 0 else "")


def format_elapsed(seconds_since_start: float) -> str:
    """Format elapsed seconds as 'HH:MM:SS' for the timer label."""
    t = int(seconds_since_start)
    h = t // 3600
    m = (t % 3600) // 60
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# file I/O helpers
# ---------------------------------------------------------------------------


def append_to_finish_file(path: str, number: str, time_str: str) -> bool:
    """
    Append 'number#time_str#' to the results file.
    Returns True on success, False if file cannot be opened.
    Port of C++ writeToFinishFile logic.
    """
    if not path:
        return False
    try:
        record = f"{number}#{time_str}#\n"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(record)
        return True
    except OSError:
        return False


def append_to_group_file(path: str, group: str, time_str: str) -> bool:
    """
    Append 'group#time_str#' to the groups file.
    Returns True on success, False if file cannot be opened.
    Port of C++ writeToGroupFile logic.
    """
    if not path:
        return False
    try:
        record = f"{group}#{time_str}#\n"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(record)
        return True
    except OSError:
        return False


def save_backup(
    path: str,
    log_items: list[str],
    group_number: str,
    group_time: str,
    slots: list[tuple[str, str]],
    finish_mode: bool,
) -> bool:
    """
    Write chronometer backup file.
    slots is a list of (number, time) for the 5 finish slots.
    finish_mode: True -> "finish", False -> "nextLap" for pending slots.
    Port of C++ saveBackupFile logic.
    Returns True on success.
    """
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        lines.extend(log_items)
        lines.append(f"{group_number}#{group_time}#")
        action = "finish" if finish_mode else "nextLap"
        for number, time_str in slots:
            lines.append(f"{number}#{time_str}#{action}#")
        with Path(path).open("w", encoding="utf-8") as f:
            for ln in lines:
                f.write(ln + "\n")
        return True
    except OSError:
        return False


def load_config(path: str) -> tuple[list[str], str, str]:
    """
    Load groupsList.txt config file.
    Returns (groups_list, results_file_path, group_start_file_path).
    Port of C++ loadConfig logic.
    """
    groups: list[str] = []
    results_file = ""
    group_start_file = ""
    p = Path(path)
    if not p.exists():
        return groups, results_file, group_start_file
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            lines = [ln.rstrip("\r\n") for ln in p.read_text(encoding=enc).splitlines()]
            break
        except UnicodeDecodeError:
            continue
    else:
        return groups, results_file, group_start_file

    i = 0
    while i < len(lines):
        if lines[i] == "configFiles":
            i += 1
            if i < len(lines):
                results_file = lines[i].replace("\\", "/")
                i += 1
            if i < len(lines):
                group_start_file = lines[i].replace("\\", "/")
            break
        groups.append(lines[i])
        i += 1
    return groups, results_file, group_start_file


# ---------------------------------------------------------------------------
# crossing count
# ---------------------------------------------------------------------------


def get_number_of_crosses(
    number: str,
    log_items: list[str],
    current_slots: list[str],
) -> int:
    """
    Count how many times number appears in log_items + current_slots.
    Port of C++ getNumberOfCrosses logic.
    """
    if not number:
        return 0
    count = 0
    for entry in log_items:
        entry_number = entry.split("#")[0] if "#" in entry else entry
        if entry_number == number:
            count += 1
    for slot_number in current_slots:
        if slot_number == number:
            count += 1
    return count
