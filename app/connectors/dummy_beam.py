"""Test beam: a break every ``min_s`` to ``max_s`` seconds, at random (``seed``)."""

from __future__ import annotations

import random
from typing import Any

from app.connectors import Events, positive, trouble


def events(settings: dict[str, Any]) -> Events:
    rnd = random.Random(settings.get("seed"))  # noqa: S311 - test data, not secrets
    low, high = positive(settings, "min_s", 5), positive(settings, "max_s", 20)
    if low is None or high is None or high < low:
        yield 0.0, trouble("min_s and max_s must be seconds above 0, min_s <= max_s")
        return
    seq = 0
    while True:
        seq += 1
        yield rnd.uniform(low, high), {"type": "beam", "seq": seq}
