"""The chip report: share of each bib's crossings every chip was read in."""

from __future__ import annotations

from app.chip_report import chip_report
from app.chips import ChipMap
from app.models import scale_time

MAP = ChipMap(
    bib_of={"A": "15", "B": "15", "C": "16", "D": "9", "E": "X1"},
    conflicts={"G": ["15", "16"]},
)


def test_story_6_counts_the_crossings_each_chip_was_read_in():
    # The reads of Story 1, one out of order, plus an unknown chip and a conflict.
    reads = [("A", 0), ("B", 300), ("A", 9000), ("A", 2000)]
    reads += [("X", 1000), ("X", 4000), ("G", 500)]
    assert chip_report(reads, MAP, 5000) == [
        "Chip report: 7 reads, dead time 5 s",
        "",
        "Chips read:",
        "bib 15: chip A read in 2 of 2 crossings, 3 reads",
        "bib 15: chip B read in 1 of 2 crossings, 1 read",
        "",
        "Chips never read:",
        "bib 9: chip D",
        "bib 16: chip C",
        "bib X1: chip E",
        "",
        "Unknown chips:",
        f"X: 2 reads, first {scale_time(1000)}, last {scale_time(4000)}",
        "",
        "Chips on two bibs, not used:",
        "G on bibs 15, 16: 1 read",
    ]


def test_a_read_exactly_the_dead_time_after_the_last_starts_a_new_crossing():
    lines = chip_report([("A", 0), ("B", 5000)], MAP, 5000)
    assert "bib 15: chip A read in 1 of 2 crossings, 1 read" in lines
    assert "bib 15: chip B read in 1 of 2 crossings, 1 read" in lines


def test_an_empty_section_says_none():
    assert chip_report([], ChipMap(), 3000) == [
        "Chip report: 0 reads, dead time 3 s",
        "",
        "Chips read:",
        "none",
        "",
        "Chips never read:",
        "none",
        "",
        "Unknown chips:",
        "none",
        "",
        "Chips on two bibs, not used:",
        "none",
    ]


def test_a_bib_that_only_looks_like_a_number_sorts_after_the_numbers():
    chip_map = ChipMap(bib_of={"A": "1\u00b2", "B": "10"})
    lines = chip_report([], chip_map, 5000)
    assert lines.index("bib 10: chip B") < lines.index("bib 1\u00b2: chip A")
