"""Timing chips: from the start protocol to bibs.

Field 11 of a start protocol line, as StartProtocolMaker writes it
(specs/002-chip-ids/contracts/start-protocol-line.md there): semicolons separate
the riders of a team in stage order, commas the ids of one rider. On a line with
N > 1 stages and a numeric bib, the k-th rider binds to bib + k -- the way
FinishProtocolGenerator and the site number stage riders -- and riders past the
N-th bind nothing; any other line binds every chip to its bib.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.models import parse_time, read_file_lines
from app.paths import app_path
from app.results_file import write_in_one_step

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


# -- reads to crossings ------------------------------------------------------------

STATE_VERSION = 1


def raw_read(line: str) -> tuple[str, int] | None:
    """(chip, ms) of a raw chip reads line, or None when it is not one."""
    fields = line.split("#")
    at = parse_time(fields[1]) if len(fields) > 1 else None
    chip = normalise_chip(fields[0])
    return (chip, at) if chip and at is not None else None


class ChipTiming:
    """Chip reads to crossings, one pass at a time (spec FR-009, FR-010).

    A bib's reads less than the dead time apart are one pass. A read that joins no
    pass starts one, and that pass's crossing is made at once, at the read's time;
    a read that joins passes merges them and makes nothing, so a crossing is never
    moved, and one the judge deleted never comes back. Passes formed under another
    dead time keep their shape. Reads of a chip the map does not bind wait, for
    when it does. Times are milliseconds on the results file's scale.
    """

    def __init__(self, dead_ms: int = 5000) -> None:
        self.dead_ms = dead_ms
        self.chip_map = ChipMap()
        self.passes: dict[str, list[list[int]]] = {}
        self.pending: list[tuple[str, int]] = []
        self.unwritten: list[str] = []
        self.processed_lines = 0

    def on_read(self, chip: str, at: int) -> list[tuple[str, int]]:
        """Take one read; return the crossings it makes, as (bib, ms)."""
        bib = self.chip_map.bib_of.get(chip)
        if bib is None:
            self.pending.append((chip, at))
            return []
        return [(bib, at)] if self._into_passes(bib, at) else []

    def set_map(self, chip_map: ChipMap) -> list[tuple[str, int]]:
        """Use a new map; the waiting reads of chips it binds become crossings.

        They go into their bib's passes in time order, so a pass gets its crossing
        at its first read. A chip that moved to another bib keeps its past
        crossings on the old one: only waiting reads are replayed.
        """
        self.chip_map = chip_map
        known = sorted(
            (at, chip) for chip, at in self.pending if chip in chip_map.bib_of
        )
        self.pending = [(c, at) for c, at in self.pending if c not in chip_map.bib_of]
        made: list[tuple[str, int]] = []
        for at, chip in known:
            made += self.on_read(chip, at)
        return made

    def unknown(self) -> dict[str, tuple[int, int, int]]:
        """Chips no map binds, with first read, last read and number of reads.

        A chip on two bibs is not unknown: the conflicts list names it.
        """
        found: dict[str, tuple[int, int, int]] = {}
        for chip, at in self.pending:
            if chip not in self.chip_map.conflicts:
                first, last, count = found.get(chip, (at, at, 0))
                found[chip] = (min(first, at), max(last, at), count + 1)
        return found

    def _into_passes(self, bib: str, at: int) -> bool:
        """Put a read into the bib's passes; True when it starts a new one."""
        passes = self.passes.setdefault(bib, [])
        near = [p for p in passes if p[0] - self.dead_ms < at < p[1] + self.dead_ms]
        if not near:
            passes.append([at, at])
            passes.sort()
            return True
        merged = [min(at, *(p[0] for p in near)), max(at, *(p[1] for p in near))]
        passes[:] = sorted([p for p in passes if p not in near] + [merged])
        return False

    def to_json(self) -> dict:
        return {
            "version": STATE_VERSION,
            "processed_lines": self.processed_lines,
            "passes": self.passes,
            "pending": [list(read) for read in self.pending],
            "unwritten": self.unwritten,
        }

    @classmethod
    def from_json(cls, data: dict, dead_ms: int) -> ChipTiming:
        timing = cls(dead_ms)
        timing.processed_lines = int(data.get("processed_lines", 0))
        timing.passes = {
            str(bib): [[int(a), int(b)] for a, b in spans]
            for bib, spans in data.get("passes", {}).items()
        }
        timing.pending = [(str(c), int(t)) for c, t in data.get("pending", [])]
        timing.unwritten = [str(line) for line in data.get("unwritten", [])]
        return timing


def load_chip_state(path: str, dead_ms: int) -> ChipTiming | None:
    """The chip state saved next to a results file; None when missing or unreadable."""
    try:
        data = json.loads(app_path(path).read_text(encoding="utf-8"))
        if data.get("version") == STATE_VERSION:
            return ChipTiming.from_json(data, dead_ms)
    except OSError, ValueError, TypeError, AttributeError:
        pass
    return None


def rebuilt_timing(raw: list[str], chip_map: ChipMap, dead_ms: int) -> ChipTiming:
    """A chip state made again from the raw reads file when the saved one is lost.

    The passes come back, so a rider's next read still joins the pass it belongs
    to. Their crossings do not: they were written when the reads came in, and one
    the judge deleted must stay deleted. Reads of unbound chips wait as before.
    """
    timing = ChipTiming(dead_ms)
    timing.set_map(chip_map)
    for line in raw:
        if (read := raw_read(line)) is not None:
            timing.on_read(*read)
    timing.processed_lines = len(raw)
    return timing


def save_chip_state(path: str, timing: ChipTiming) -> bool:
    """Write the chip state in one step; False when it cannot be written.

    On disk before it replaces the old state: a power cut must not leave an empty
    file where the passes were.
    """
    try:
        write_in_one_step(app_path(path), json.dumps(timing.to_json()))
        return True
    except OSError:
        return False
