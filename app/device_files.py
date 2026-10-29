"""The append-only files of what devices reported, next to the results file.

Formats in specs/001-event-sources/contracts/raw-files.md. The names come from the
results file's, so two results files in one folder keep their device files apart,
and a new results file starts with fresh ones.
"""

from __future__ import annotations

from pathlib import Path


def side_file(results_path: str, kind: str, extension: str = "txt") -> str:
    """``results.txt`` -> ``results.<kind>.<extension>``, in the same folder.

    Only a ``.txt`` ending is dropped: ``finish.day1`` and ``finish.day2`` keep
    their whole names, and a name with no ending at all keeps an empty one
    (``finish..chip_reads.txt``), so that ``finish`` and ``finish.txt`` stay apart
    too. "" when there is no results file to sit next to.
    """
    if not results_path:
        return ""
    path = Path(results_path)
    name = path.name
    if name.lower().endswith(".txt"):
        name = name[:-4]
    elif not path.suffix:
        name += "."
    return str(path.with_name(f"{name}.{kind}.{extension}"))
