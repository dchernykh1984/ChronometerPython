"""The append-only files of what devices reported, next to the results file.

Formats in specs/001-event-sources/contracts/raw-files.md. The names come from the
results file's, so two results files in one folder keep their device files apart,
and a new results file starts with fresh ones.
"""

from __future__ import annotations

from pathlib import Path

from app.paths import app_path


def side_file(results_path: str, kind: str, extension: str = "txt") -> str:
    """``results.txt`` -> ``results.<kind>.<extension>``, in the same folder.

    "" when there is no results file to sit next to.
    """
    if not results_path:
        return ""
    return f"{Path(results_path).with_suffix('')}.{kind}.{extension}"


def field(text: str) -> str:
    """Device text made safe for a #-separated line."""
    return text.replace("#", " ").replace("\r", " ").replace("\n", " ").strip()


def append_record(path: str, record: str) -> bool:
    """Append one line; False (and nothing raised) when it cannot be written."""
    if not path:
        return False
    try:
        target = app_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="\n") as f:
            f.write(record + "\n")
        return True
    except OSError:
        return False
