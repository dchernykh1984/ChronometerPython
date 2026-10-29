"""Read and rewrite the results file. A rewrite never starts without a backup.

A crossing already written is the record of a race that cannot be run again, so a
change to it first copies the whole file aside and is refused if that copy fails;
the new content then replaces the file in one step, so a crash leaves the old file
or the new one, never a mix.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from app.models import parse_time
from app.paths import app_path

ACTIONS = ("nextLap", "finish", "nextStage")
# On Windows a program holding the file open without delete sharing (PhotoFinish
# reading it, an editor, an antivirus scan) makes os.replace fail for a moment.
_REPLACE_PATIENCE_S = 2.0
_REPLACE_PAUSE_S = 0.05


def crossing_line(number: str, time_str: str, action: str) -> str:
    return f"{number}#{time_str}#{action}#"


def crossing_key(line: str) -> tuple[str, str]:
    """A crossing's number and time: two lines with both the same are one crossing."""
    number, _, rest = line.partition("#")
    return number, rest.partition("#")[0]


def crossing_problem(number: str, time_str: str, action: str) -> str | None:
    """Why a crossing cannot be written as given, or None when it can."""
    if not number.strip():
        return "The number is empty."
    text = number + action
    if "#" in text or text.splitlines() != [text]:  # any break splitlines() knows
        return "A number or an action cannot hold '#' or a line break."
    if parse_time(time_str) is None:
        return "The time is not 'D H:M:S' or 'D H:M:S.mmm'."
    if action not in ACTIONS and action != "DSQ" and not action.startswith("DSQ: "):
        return f"The action must be one of {', '.join(ACTIONS)} or DSQ."
    return None


def rewrite_results(
    path: str,
    lines: list[str],
    backup_dir: Path | None = None,
    stem: str = "results",
) -> Path:
    """Replace a file with lines after copying it aside; return the copy.

    The results file by default; the start protocol file too (stem "start").
    Raises OSError, with the file untouched, when the backup or the write fails.
    """
    target = app_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    folder = backup_dir or app_path("temp")
    folder.mkdir(parents=True, exist_ok=True)
    backup = _free_name(folder, f"{stem}{int(time.time())}")
    backup.write_bytes(target.read_bytes() if target.exists() else b"")
    write_in_one_step(target, "".join(line + "\n" for line in lines))
    return backup


def write_in_one_step(
    target: Path, text: str, patience_s: float = _REPLACE_PATIENCE_S
) -> None:
    """Put text in target through a temporary file flushed to disk.

    A crash leaves the old content or the new one, never a mix, and a replace that
    Windows holds up is retried for patience_s. Raises OSError, with target
    untouched, when it cannot be done.
    """
    temporary = target.with_name(target.name + ".tmp")
    try:
        # The platform's line end, as every append to the results file writes it.
        with temporary.open("w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        _replace(temporary, target, patience_s)
    except OSError:
        temporary.unlink(missing_ok=True)  # never left beside the file
        raise


def _free_name(folder: Path, stem: str) -> Path:
    n = 0
    while (folder / f"{stem}_{n}.txt").exists():
        n += 1
    return folder / f"{stem}_{n}.txt"


def _replace(source: Path, target: Path, patience_s: float) -> None:
    deadline = time.monotonic() + patience_s
    while True:
        try:
            source.replace(target)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                source.unlink(missing_ok=True)
                raise
            time.sleep(_REPLACE_PAUSE_S)
