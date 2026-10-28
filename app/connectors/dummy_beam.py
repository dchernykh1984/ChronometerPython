"""Test beam: a break every ``min_s`` to ``max_s`` seconds, at random (``seed``)."""

from __future__ import annotations

import random
from typing import Any

from app.connectors import Events


def events(settings: dict[str, Any]) -> Events:
    rnd = random.Random(settings.get("seed"))  # noqa: S311 - test data, not secrets
    low, high = float(settings.get("min_s", 5)), float(settings.get("max_s", 20))
    seq = 0
    while True:
        seq += 1
        yield rnd.uniform(low, high), {"type": "beam", "seq": seq}
