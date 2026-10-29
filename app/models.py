"""Pure-logic helpers for Windows Chronometer (no GUI dependencies)."""

from __future__ import annotations

import re
import time
import uuid

from app.paths import app_path

# Persisted HTTP/site settings for pushing timing data to the cycling site. Kept in a
# separate key=value file so it never disturbs the positional groupsList.txt parsing.
# ``device_id`` is the stable per-machine id (generated once); ``rev_finish`` and
# ``rev_group`` are the per-stream counters the server uses to reject a stale overwrite.
HTTP_CONFIG_PATH = str(app_path("data", "http_config.txt"))
_HTTP_CONFIG_DEFAULTS: dict[str, str] = {
    "site_url": "",
    "token": "",
    "device_id": "",
    "point_number": "0",
    "rev_finish": "0",
    "rev_group": "0",
}


def load_http_config(path: str = HTTP_CONFIG_PATH) -> dict[str, str]:
    """Load the HTTP config; generate and persist a device_id on first use."""
    cfg = dict(_HTTP_CONFIG_DEFAULTS)
    p = app_path(path)
    if p.exists():
        lines: list[str] = []
        for enc in ("utf-8", "cp1251", "latin-1"):
            try:
                lines = p.read_text(encoding=enc).splitlines()
                break
            except UnicodeDecodeError:
                continue
        for ln in lines:
            if "=" in ln:
                key, _, value = ln.partition("=")
                key = key.strip()
                if key in cfg:
                    cfg[key] = value.strip()
    if not cfg["device_id"]:
        cfg["device_id"] = str(uuid.uuid4())
        save_http_config(cfg, path)
    return cfg


def save_http_config(cfg: dict[str, str], path: str = HTTP_CONFIG_PATH) -> bool:
    """Persist the HTTP config (only the known keys, as key=value lines)."""
    try:
        app_path(path).parent.mkdir(parents=True, exist_ok=True)
        with app_path(path).open("w", encoding="utf-8") as f:
            for key in _HTTP_CONFIG_DEFAULTS:
                f.write(f"{key}={cfg.get(key, _HTTP_CONFIG_DEFAULTS[key])}\n")
        return True
    except OSError:
        return False


def read_file_lines(path: str) -> list[str]:
    """Read non-empty lines from a results/groups file; [] if missing.

    A folder is no file: a path typed letter by letter passes through folders.
    """
    p = app_path(path)
    if not path or not p.is_file():
        return []
    lines: list[str] = []
    for raw in p.read_bytes().split(b"\n"):
        lines += [ln for ln in _decoded(raw.rstrip(b"\r")).splitlines() if ln.strip()]
    return lines


def _decoded(raw: bytes) -> str:
    """One line as UTF-8, or else as the older C++ chronometer wrote it (cp1251).

    Line by line: a file the old program began and this one went on with holds
    both, and a rewrite must keep both readable.
    """
    for encoding in ("utf-8", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


# ---------------------------------------------------------------------------
# time helpers
# ---------------------------------------------------------------------------


# ASCII digits only: a time in other digits would be written as typed and read by
# no other tool of the set.
_TIME = re.compile(r"(\d+) (\d{1,2}):(\d{1,2}):(\d{1,2})(?:\.(\d{3}))?", re.ASCII)


def format_time(epoch_ms: int, accuracy: int = 3, dst: bool = False) -> str:
    """'D H:M:S[.mmm]' of a moment given in Unix milliseconds, in local standard time.

    ``dst`` adds the summer hour; the caller decides it, as the summer-time option and
    the system's daylight-saving flag say. accuracy=0 leaves out the milliseconds.
    """
    return scale_time(
        epoch_ms - time.timezone * 1000 + (3_600_000 if dst else 0), accuracy
    )


def scale_time(ms: int, accuracy: int = 3) -> str:
    """'D H:M:S[.mmm]' of milliseconds on the results file's scale (parse_time's)."""
    days, rem = divmod(ms, 86_400_000)
    hours, rem = divmod(rem, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, ms = divmod(rem, 1000)
    base = f"{days} {hours}:{minutes}:{seconds}"
    return base + (f".{ms:03d}" if accuracy != 0 else "")


def parse_time(text: str) -> int | None:
    """Milliseconds of a 'D H:M:S[.mmm]' time on its own scale, or None if not one.

    The inverse of format_time up to the zone: two times parsed this way can be
    compared and subtracted, which is all the chip logic needs.
    """
    m = _TIME.fullmatch(text.strip())
    if not m:
        return None
    days, hours, minutes, seconds = (int(g) for g in m.groups()[:4])
    if hours > 23 or minutes > 59 or seconds > 59:
        return None
    ms = int(m.group(5) or 0)
    return ((days * 24 + hours) * 60 + minutes) * 60_000 + seconds * 1000 + ms


def get_current_time(accuracy: int = 3, summer_time: bool = False) -> str:
    """
    Return current local time as 'D H:M:S[.mmm]'.
    accuracy=3 -> include milliseconds; accuracy=0 -> seconds only.
    summer_time=True adds +3600s only when OS DST flag is active
    (C++ checkBoxUseSummerTimeShifting + _ftime dstflag check).
    Port of C++ getCurrentTime(accuracy).
    """
    dst = summer_time and bool(time.localtime().tm_isdst)
    return format_time(int(time.time() * 1000), accuracy, dst)


def format_elapsed(seconds_since_start: float) -> str:
    """Format elapsed seconds as 'HH:MM:SS' for the timer label."""
    t = int(seconds_since_start)
    h = t // 3600
    m = (t % 3600) // 60
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def dsq_status(reason: str = "") -> str:
    """Build the DSQ status field written into ``number#time#<status>#``.

    Returns bare ``DSQ`` when no reason is given (backward compatible), else
    ``DSQ: <reason>``. ``#`` and newlines are stripped from the reason so they can never
    break the ``#``-delimited record; surrounding whitespace is trimmed.
    """
    cleaned = record_field(reason)
    return f"DSQ: {cleaned}" if cleaned else "DSQ"


def one_line(text: str) -> bool:
    """True when text holds none of the line breaks str.splitlines() knows."""
    return text.splitlines() in ([text], [])


def record_field(text: str) -> str:
    """Text made safe for one field of a #-separated line.

    No "#", and none of the line breaks str.splitlines() knows -- form feed and
    U+2028 among them, not only CR and LF -- or the line would read back as two;
    each becomes a space, and the ends are trimmed.
    """
    return " ".join(text.replace("#", " ").splitlines()).strip()


# ---------------------------------------------------------------------------
# file I/O helpers
# ---------------------------------------------------------------------------


def append_to_finish_file(path: str, number: str, time_str: str) -> bool:
    """
    Append 'number#time_str#' to the results file.
    Returns True on success, False if file cannot be opened.
    Port of C++ writeToFinishFile logic.
    """
    return append_line(path, f"{number}#{time_str}#")


def end_cut_line(path: str) -> None:
    """End a last line a crash cut short, so the next one appended never joins it:
    a file's line count stays the count of what was appended to it."""
    try:
        with app_path(path).open("rb") as f:
            f.seek(-1, 2)  # an empty or missing file has nothing to end
            last = f.read(1)
        if path and last not in (b"\n", b"\r"):
            with app_path(path).open("a", encoding="utf-8") as f:
                f.write("\n")
    except OSError:
        pass


def append_line(path: str, line: str) -> bool:
    """Append one line to a text file, ended as the platform ends lines (the results
    file and the device files beside it alike); False if it cannot be opened."""
    if not path:
        return False
    try:
        app_path(path).parent.mkdir(parents=True, exist_ok=True)
        with app_path(path).open("a", encoding="utf-8") as f:
            f.write(line + "\n")
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
        app_path(path).parent.mkdir(parents=True, exist_ok=True)
        with app_path(path).open("a", encoding="utf-8") as f:
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
        app_path(path).parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        lines.extend(log_items)
        lines.append(f"{group_number}#{group_time}#")
        action = "finish" if finish_mode else "nextLap"
        for number, time_str in slots:
            lines.append(f"{number}#{time_str}#{action}#")
        with app_path(path).open("w", encoding="utf-8") as f:
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
    p = app_path(path)
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


def save_config(
    path: str,
    groups: list[str],
    results_file: str,
    group_start_file: str,
) -> bool:
    """
    Write groupsList.txt: one group per line, then a ``configFiles`` marker followed by
    the results-file and group-start-file paths. Inverse of load_config.
    Returns True on success, False if the file cannot be written.
    """
    try:
        app_path(path).parent.mkdir(parents=True, exist_ok=True)
        lines = [*groups, "configFiles", results_file, group_start_file]
        with app_path(path).open("w", encoding="utf-8") as f:
            for ln in lines:
                f.write(ln + "\n")
        return True
    except OSError:
        return False
