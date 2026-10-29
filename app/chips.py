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

STATE_VERSION = 2  # 2: reads of unbound chips kept as runs


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
    when it does, as runs: a chip left by the antenna for hours is one run, not
    100 000 reads in every save. Times are milliseconds on the results file's scale.
    """

    def __init__(self, dead_ms: int = 5000) -> None:
        self.dead_ms = dead_ms
        self.chip_map = ChipMap()
        self.passes: dict[str, list[list[int]]] = {}
        # chip -> runs [first, last, count] of its reads less than the dead time apart
        self.pending: dict[str, list[list[int]]] = {}
        self.unwritten: list[str] = []
        self.processed_lines = 0

    def on_read(self, chip: str, at: int) -> list[tuple[str, int]]:
        """Take one read; return the crossings it makes, as (bib, ms)."""
        bib = self.chip_map.bib_of.get(chip)
        if bib is None:
            self._into_runs(chip, at)
            return []
        return [(bib, at)] if self._into_passes(bib, at, at) else []

    def set_map(self, chip_map: ChipMap) -> list[tuple[str, int]]:
        """Use a new map; the waiting reads of chips it binds join their bibs' reads.

        As FR-010 says: the bib's reads less than the dead time apart are one pass,
        and only a pass that never had a crossing gets one, at its first read. So
        the newly bound reads are grouped first, and a group that comes near a pass
        makes nothing, however much earlier its first read is. A chip that moved to
        another bib keeps its past crossings on the old one: only waiting reads join.
        """
        self.chip_map = chip_map
        spans: dict[str, list[list[int]]] = {}
        for chip in [chip for chip in self.pending if chip in chip_map.bib_of]:
            spans.setdefault(chip_map.bib_of[chip], []).extend(
                [first, last] for first, last, _ in self.pending.pop(chip)
            )
        made: list[tuple[str, int]] = []
        for bib, runs in spans.items():
            for first, last in self._groups(sorted(runs)):
                if self._into_passes(bib, first, last):
                    made.append((bib, first))
        return sorted(made, key=lambda crossing: crossing[1])

    def unknown(self) -> dict[str, tuple[int, int, int]]:
        """Chips no map binds, with first read, last read and number of reads.

        A chip on two bibs is not unknown: the conflicts list names it.
        """
        return {
            chip: (
                min(run[0] for run in runs),
                max(run[1] for run in runs),
                sum(run[2] for run in runs),
            )
            for chip, runs in self.pending.items()
            if chip not in self.chip_map.conflicts
        }

    def _into_runs(self, chip: str, at: int) -> None:
        """Keep a read of an unbound chip in the run it is near, or start one."""
        runs = self.pending.setdefault(chip, [])
        for run in reversed(runs):
            if run[0] - self.dead_ms < at < run[1] + self.dead_ms:
                run[0], run[1], run[2] = min(run[0], at), max(run[1], at), run[2] + 1
                return
        runs.append([at, at, 1])

    def _groups(self, spans: list[list[int]]) -> list[list[int]]:
        """Sorted spans of reads joined wherever less than the dead time apart."""
        groups: list[list[int]] = []
        for first, last in spans:
            if groups and first < groups[-1][1] + self.dead_ms:
                groups[-1][1] = max(groups[-1][1], last)
            else:
                groups.append([first, last])
        return groups

    def _into_passes(self, bib: str, first: int, last: int) -> bool:
        """Put a read, or a group of reads, into the bib's passes; True when it is a
        new pass. One less than the dead time from a pass joins it, merging all the
        passes it comes near, and makes nothing."""
        passes = self.passes.setdefault(bib, [])
        dead = self.dead_ms
        near = [p for p in passes if p[0] - dead < last and first < p[1] + dead]
        merged = [
            min([first, *(p[0] for p in near)]),
            max([last, *(p[1] for p in near)]),
        ]
        passes[:] = sorted([p for p in passes if p not in near] + [merged])
        return not near

    def to_json(self) -> dict:
        return {
            "version": STATE_VERSION,
            "processed_lines": self.processed_lines,
            "passes": self.passes,
            "pending": self.pending,
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
        timing.pending = {
            str(chip): [[int(a), int(b), int(n)] for a, b, n in runs]
            for chip, runs in data.get("pending", {}).items()
        }
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

    A crash leaves the old state or the new one, never a mix.
    """
    try:
        # This runs on the window's thread every second of a race: one try (a state
        # not saved is tried again a few seconds later) and no fsync (a state a
        # power cut left empty is rebuilt from the raw reads, crossings not twice).
        text = json.dumps(timing.to_json(), separators=(",", ":"))
        write_in_one_step(app_path(path), text, patience_s=0, sync=False)
        return True
    except OSError:
        return False
