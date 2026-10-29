"""Test chips: riders pass in turn, each read two to four times within a second.

Settings: ``riders`` (a list of each rider's chip ids, as the chip map gives them),
``period_s`` (seconds between passes), ``seed`` (for tests). Every tenth pass reads
a chip no start protocol holds, so the unknown-chip list has something to show.
"""

from __future__ import annotations

import random
from typing import Any

from app.connectors import Events, positive, trouble

UNKNOWN_CHIP = "TEST0000"


def events(settings: dict[str, Any]) -> Events:
    rnd = random.Random(settings.get("seed"))  # noqa: S311 - test data, not secrets
    given = settings.get("riders", [])
    period = positive(settings, "period_s", 3)
    if not isinstance(given, list) or not all(isinstance(r, list) for r in given):
        yield 0.0, trouble("riders must be a list of each rider's chip ids")
        return
    if period is None:
        yield 0.0, trouble("period_s must be seconds above 0")
        return
    riders = [list(map(str, r)) for r in given if r]
    passes = 0
    while True:
        passes += 1
        chips = riders[(passes - 1) % len(riders)] if riders and passes % 10 else []
        chips = chips or [UNKNOWN_CHIP]
        for i in range(rnd.randint(2, 4)):
            yield (
                (period if i == 0 else rnd.uniform(0.05, 0.3)),
                {
                    "type": "read",
                    "chip": rnd.choice(chips),
                    "antenna": str(rnd.randint(1, 4)),
                    "rssi": round(rnd.uniform(-75, -45), 1),
                    "reader": "dummy",
                },
            )
