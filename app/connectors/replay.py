"""Replay: a chip reads file played back at its own pace, times ``speed``.

Settings: ``path`` (a file in the raw chip reads format,
``chip#time#device time#antenna#signal#reader#``) and ``speed``. The reads come
out as if they happened now, with the gaps between them as recorded, so a past
race can rehearse the whole chain; lines that are not reads are skipped.
"""

from __future__ import annotations

from typing import Any

from app.connectors import Events
from app.models import parse_time, read_file_lines


def events(settings: dict[str, Any]) -> Events:
    speed = float(settings.get("speed", 1)) or 1.0
    previous: int | None = None
    for line in read_file_lines(str(settings.get("path", ""))):
        fields = [*line.split("#"), "", "", "", "", ""]
        at = parse_time(fields[1])
        if not fields[0].strip() or at is None:
            continue
        pause = 0.0 if previous is None else max(0, at - previous) / 1000 / speed
        previous = at
        event: dict[str, Any] = {"type": "read", "chip": fields[0]}
        for key, value in (
            ("device_time", fields[2]),
            ("antenna", fields[3]),
            ("reader", fields[5]),
        ):
            if value:
                event[key] = value
        signal = _number(fields[4])
        if signal is not None:
            event["rssi"] = signal
        yield pause, event


def _number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None
