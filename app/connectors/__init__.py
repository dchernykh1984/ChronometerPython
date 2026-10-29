"""The connectors the chronometer knows: built-in ones, a custom command, stubs.

A connector is a separate process that speaks app.connector_protocol. Built-in
connectors run from the chronometer itself (``--connector <name>``), so no second
program is shipped; stubs stand for devices that are not supported yet.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

# What a built-in connector produces: pauses and the events that follow them.
Events = Iterator[tuple[float, dict[str, Any]]]


def positive(settings: dict[str, Any], key: str, default: float) -> float | None:
    """A setting that must be a number above 0, or None when it is not one."""
    try:
        value = float(settings.get(key, default))
    except TypeError, ValueError:
        return None
    return value if value > 0 else None  # NaN is not above 0 either


def trouble(message: str) -> dict[str, Any]:
    """An error the judge reads in the action log; the connector then just waits."""
    return {"type": "error", "message": message, "fatal": False}


@dataclass(frozen=True)
class ConnectorInfo:
    name: str
    kind: str | None  # "chips", "beam", or None for a custom command of either kind
    label: str
    available: bool = True
    test: bool = False  # its crossings are test data
    settings: dict[str, Any] = field(default_factory=dict)


CONNECTORS = (
    ConnectorInfo(
        "dummy-chips", "chips", "Test chips", test=True, settings={"period_s": 3}
    ),
    ConnectorInfo(
        "dummy-beam", "beam", "Test beam", test=True, settings={"min_s": 5, "max_s": 20}
    ),
    ConnectorInfo(
        "replay",
        "chips",
        "Replay a chip reads file",
        test=True,
        settings={"path": "", "speed": 1},
    ),
    ConnectorInfo("custom", None, "Custom command"),
    ConnectorInfo("llrp", "chips", "LLRP reader (Impinj, Zebra)", available=False),
    ConnectorInfo("raceresult", "chips", "RaceResult decoder", available=False),
    ConnectorInfo("r2000", "chips", "R2000 reader (serial or TCP)", available=False),
    ConnectorInfo("beam-usb", "beam", "USB beam", available=False),
    ConnectorInfo("beam-ble", "beam", "Bluetooth beam", available=False),
)


def connectors_for(kind: str) -> list[ConnectorInfo]:
    """The connectors offered for a source kind, stubs included."""
    return [c for c in CONNECTORS if c.kind in (kind, None)]


def find(name: str) -> ConnectorInfo | None:
    return next((c for c in CONNECTORS if c.name == name), None)


def builtin(name: str) -> tuple[str, Callable[[dict[str, Any]], Events]] | None:
    """The kind and event source of a connector the chronometer runs itself."""
    from app.connectors import dummy_beam, dummy_chips, replay

    sources: dict[str, tuple[str, Callable[[dict[str, Any]], Events]]] = {
        "dummy-chips": ("chips", dummy_chips.events),
        "dummy-beam": ("beam", dummy_beam.events),
        "replay": ("chips", replay.events),
    }
    return sources.get(name)
