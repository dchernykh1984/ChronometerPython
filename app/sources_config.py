"""Event source settings: data/sources.txt, key=value, next to http_config.txt.

Kept apart from the positional groupsList.txt and from the site settings, as one
copied event folder keeps its own. Connector settings are one-line JSON per
connector, so a reader's address or a replay file survives a restart.
"""

from __future__ import annotations

import json
from typing import Any

from app.connectors import find
from app.models import read_file_lines
from app.paths import app_path
from app.results_file import write_in_one_step

SOURCES_PATH = str(app_path("data", "sources.txt"))
SOURCES = ("hand", "beam", "chips")
DEFAULTS = {
    "source": "hand",
    "beam_connector": "dummy-beam",
    "chips_connector": "dummy-chips",
    "custom_command": "",
    "dead_time_s": "5",
    "start_protocol": "data/start.txt",
}


def load_sources(path: str = SOURCES_PATH) -> dict[str, str]:
    """The saved settings over the defaults; unknown keys are kept for later writers."""
    cfg = dict(DEFAULTS)
    for line in read_file_lines(path):
        key, sep, value = line.partition("=")
        if sep and key.strip():
            cfg[key.strip()] = value.strip()
    if cfg["source"] not in SOURCES:
        cfg["source"] = "hand"
    return cfg


def save_sources(cfg: dict[str, str], path: str = SOURCES_PATH) -> bool:
    """Write the settings in one step: a crash never leaves the file half written."""
    try:
        target = app_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        write_in_one_step(
            target, "".join(f"{key}={value}\n" for key, value in cfg.items())
        )
        return True
    except OSError:
        return False


def dead_time_s(cfg: dict[str, str]) -> int:
    """The saved dead time in seconds; the default when it is not a whole number.

    The file can be edited by hand, and a typo must not keep the window shut.
    """
    try:
        return int(cfg.get("dead_time_s", ""))
    except ValueError:
        return int(DEFAULTS["dead_time_s"])


def connector_settings(cfg: dict[str, str], name: str) -> dict[str, Any]:
    """A connector's saved settings, or its defaults when none or not valid JSON."""
    info = find(name)
    defaults = dict(info.settings) if info else {}
    try:
        saved = json.loads(cfg.get(f"settings.{name}", ""))
    except ValueError:
        return defaults
    return saved if isinstance(saved, dict) else defaults


def set_connector_settings(
    cfg: dict[str, str], name: str, settings: dict[str, Any]
) -> None:
    cfg[f"settings.{name}"] = json.dumps(settings, separators=(",", ":"))
