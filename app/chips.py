"""Timing chips: from the start protocol to bibs.

Field 11 of a start protocol line, as StartProtocolMaker writes it
(specs/002-chip-ids/contracts/start-protocol-line.md there): semicolons separate
the riders of a team in stage order, commas the ids of one rider. On a line with
N > 1 stages and a numeric bib, the k-th rider binds to bib + k -- the way
FinishProtocolGenerator and the site number stage riders -- and riders past the
N-th bind nothing; any other line binds every chip to its bib.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models import read_file_lines
from app.paths import app_path

CHIPS_FIELD = 11
NOT_PAID = "NOT_PAID"
_NOT_CHIP = re.compile(r"[^A-Za-z0-9]")


def normalise_chip(text: str) -> str:
    """How every reader compares ids: upper case, ASCII letters and digits only."""
    return _NOT_CHIP.sub("", text).upper()


def chip_bindings(line: str) -> list[tuple[str, str]]:
    """(chip, bib) for every chip a start protocol line binds."""
    fields = line.split("#")
    bib = fields[0].strip()
    if not bib or bib == NOT_PAID or len(fields) <= CHIPS_FIELD + 1:
        return []
    stage = fields[4].strip()
    stages = (
        int(stage) if stage.isdecimal() and int(stage) > 1 and bib.isdecimal() else 0
    )
    pairs: list[tuple[str, str]] = []
    for k, rider in enumerate(fields[CHIPS_FIELD].split(";")):
        if stages and k >= stages:
            break
        rider_bib = str(int(bib) + k) if stages and k else bib
        ids = dict.fromkeys(normalise_chip(t) for t in rider.split(","))
        pairs.extend((chip, rider_bib) for chip in ids if chip)
    return pairs


@dataclass
class ChipMap:
    """Chip id to bib; a chip bound to two bibs is a conflict and maps to neither."""

    bib_of: dict[str, str] = field(default_factory=dict)
    conflicts: dict[str, list[str]] = field(default_factory=dict)

    @property
    def bibs(self) -> int:
        return len(set(self.bib_of.values()))


def build_chip_map(lines: list[str]) -> ChipMap:
    owners: dict[str, list[str]] = {}
    for line in lines:
        for chip, bib in chip_bindings(line):
            if bib not in owners.setdefault(chip, []):
                owners[chip].append(bib)
    chip_map = ChipMap()
    for chip, bibs in owners.items():
        if len(bibs) == 1:
            chip_map.bib_of[chip] = bibs[0]
        else:
            chip_map.conflicts[chip] = bibs
    return chip_map


def read_start_protocol(path: str) -> list[str] | None:
    """The start protocol file's lines, or None when there is no such file."""
    if not path or not app_path(path).is_file():
        return None
    return read_file_lines(path)
