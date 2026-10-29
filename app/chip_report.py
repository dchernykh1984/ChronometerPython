"""The chip report (spec Story 6): how well each rider's chips were read.

Made from the raw reads with the pass rule the timing uses, so its crossings are
the passes the chips made, whatever the judge has edited in the results since.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from app.chips import ChipMap, ChipTiming
from app.models import scale_time


def chip_report(
    reads: list[tuple[str, int]], chip_map: ChipMap, dead_ms: int
) -> list[str]:
    """Report lines for reads given as (chip, ms), in any order."""
    timing = ChipTiming(dead_ms)
    timing.set_map(chip_map)
    for chip, at in sorted(reads, key=lambda read: read[1]):
        timing.on_read(chip, at)
    reads_of = Counter(chip for chip, _ in reads)
    passes_in: defaultdict[str, set[int]] = defaultdict(set)
    for chip, at in reads:
        if (bib := chip_map.bib_of.get(chip)) is not None:
            passes = timing.passes[bib]
            passes_in[chip].add(
                next(i for i, (first, last) in enumerate(passes) if first <= at <= last)
            )
    chips_of: defaultdict[str, list[str]] = defaultdict(list)
    for chip, bib in chip_map.bib_of.items():
        chips_of[bib].append(chip)
    read: list[str] = []
    never: list[str] = []
    for bib in sorted(chips_of, key=_bib_order):
        crossings = len(timing.passes.get(bib, []))
        for chip in sorted(chips_of[bib]):
            if reads_of[chip]:
                read.append(
                    f"bib {bib}: chip {chip} read in {len(passes_in[chip])} of "
                    f"{crossings} crossings, {_reads(reads_of[chip])}"
                )
            else:
                never.append(f"bib {bib}: chip {chip}")
    unknown = [
        f"{chip}: {_reads(count)}, first {scale_time(first)}, last {scale_time(last)}"
        for chip, (first, last, count) in sorted(timing.unknown().items())
    ]
    twice = [
        f"{chip} on bibs {', '.join(bibs)}: {_reads(reads_of[chip])}"
        for chip, bibs in sorted(chip_map.conflicts.items())
    ]
    return [
        f"Chip report: {_reads(len(reads))}, dead time {dead_ms / 1000:g} s",
        *_section("Chips read", read),
        *_section("Chips never read", never),
        *_section("Unknown chips", unknown),
        *_section("Chips on two bibs, not used", twice),
    ]


def _bib_order(bib: str) -> tuple[int, int, str]:
    """Numeric bibs in number order, then the rest."""
    # isdecimal, not isdigit: a superscript two is a digit int() refuses.
    return (0, int(bib), "") if bib.isdecimal() else (1, 0, bib)


def _reads(count: int) -> str:
    return f"{count} read" if count == 1 else f"{count} reads"


def _section(title: str, lines: list[str]) -> list[str]:
    return ["", f"{title}:", *(lines or ["none"])]
