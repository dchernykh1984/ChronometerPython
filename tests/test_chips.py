"""Chips: the start protocol's field 11 bound to bibs, as every reader does."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from app import chips
from app import results_file as rf

# The cases ChronometerAndroid runs too: one rule on both platforms.
VECTORS = json.loads(
    (
        Path(__file__).parents[1]
        / "specs/001-event-sources/contracts/chip-pass-vectors.json"
    ).read_text(encoding="utf-8")
)


def _line(bib: str, chip_field: str, stages: str = "1") -> str:
    return f"{bib}#Rider#M40#3#{stages}#1990#T#C##0 00:00:00.000#r1#{chip_field}#"


def test_ids_are_compared_upper_case_letters_and_digits_only():
    assert chips.normalise_chip(" e280-1170 0000.020a ") == "E28011700000020A"
    assert chips.normalise_chip(chr(0x415) + "1") == "1"  # readers drop non-ASCII


def test_a_line_binds_every_chip_to_its_bib():
    assert chips.chip_bindings(_line("15", "a1,A2")) == [("A1", "15"), ("A2", "15")]
    assert chips.chip_bindings(_line("15", "A1;B1")) == [("A1", "15"), ("B1", "15")]


def test_a_relay_binds_each_rider_to_their_stage_bib():
    assert chips.chip_bindings(_line("21", "A1,A2;B1;;D1", stages="3")) == [
        ("A1", "21"),
        ("A2", "21"),
        ("B1", "22"),
    ]
    # Stages need a numeric bib, as on the site: otherwise one bib for all.
    assert chips.chip_bindings(_line("T21", "A1;B1", stages="3")) == [
        ("A1", "T21"),
        ("B1", "T21"),
    ]


def test_lines_without_a_bib_or_a_chip_field_bind_nothing():
    assert chips.chip_bindings(_line("", "A1")) == []
    assert chips.chip_bindings(_line("NOT_PAID", "A1")) == []
    assert chips.chip_bindings("15#Rider#M40#3#1#1990#T#C##0 00:00:00.000#r1#") == []


def test_the_map_reports_a_chip_on_two_bibs_and_maps_it_to_neither():
    chip_map = chips.build_chip_map(
        [_line("15", "A1,X9"), _line("16", "B1,x9"), _line("15", "A1")]
    )
    assert chip_map.bib_of == {"A1": "15", "B1": "16"}
    assert chip_map.conflicts == {"X9": ["15", "16"]}
    assert chip_map.bibs == 2


def test_a_missing_start_protocol_is_told_from_an_empty_one(tmp_path):
    assert chips.read_start_protocol(str(tmp_path / "start.txt")) is None
    assert chips.read_start_protocol("") is None
    (tmp_path / "start.txt").write_text("", encoding="utf-8")
    assert chips.read_start_protocol(str(tmp_path / "start.txt")) == []


# -- the Chips tab ---------------------------------------------------------------


def test_the_chips_tab_shows_the_map_and_its_conflicts(win, tmp_path):
    start = tmp_path / "start.txt"
    start.write_text(
        _line("15", "A1,A2") + "\n" + _line("16", "B1,A1") + "\n", encoding="utf-8"
    )
    win._edit_start_protocol.setText(str(start))
    win._on_start_protocol_path()
    assert win._sources["start_protocol"] == str(start)
    assert win._chip_map.bib_of == {"A2": "15", "B1": "16"}
    assert "2 chips of 2 bibs" in win._lbl_chip_map.text()
    assert "1 on two bibs" in win._lbl_chip_map.text()
    assert win._list_conflicts.item(0).text() == "A1: bibs 15, 16"


def test_without_a_start_protocol_file_the_tab_says_so(win, tmp_path):
    win._edit_start_protocol.setText(str(tmp_path / "none.txt"))
    win._on_start_protocol_path()
    assert win._chip_map.bib_of == {}
    assert win._lbl_chip_map.text().startswith("No start protocol file")


# -- reads to crossings: the shared cases --------------------------------------------


def run_case(case: dict) -> list[list]:
    timing = chips.ChipTiming(case.get("dead_time_ms", VECTORS["default_dead_time_ms"]))
    timing.chip_map = chips.ChipMap(bib_of=dict(case["map"]))
    made: list[tuple[str, int]] = []
    for event in case["events"]:
        if "read" in event:
            made += timing.on_read(*event["read"])
        elif "dead_time_ms" in event:
            timing.dead_ms = event["dead_time_ms"]
        elif "map" in event:
            made += timing.set_map(chips.ChipMap(bib_of=dict(event["map"])))
    return [[bib, at] for bib, at in made]


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: c["name"])
def test_reads_become_crossings_as_the_shared_cases_say(case):
    assert run_case(case) == case["crossings"]


def test_a_read_of_an_unknown_chip_waits():
    timing = chips.ChipTiming()
    assert timing.on_read("X", 0) == []
    assert timing.pending == {"X": [[0, 0, 1]]}


def test_the_state_survives_a_restart(tmp_path):
    timing = chips.ChipTiming()
    timing.chip_map = chips.ChipMap(bib_of={"A": "15"})
    timing.on_read("A", 0)
    timing.on_read("X", 1)
    timing.unwritten.append("15#1 0:0:0.000#nextLap#")
    timing.processed_lines = 2
    path = str(tmp_path / "results.chip_state.json")
    assert chips.save_chip_state(path, timing)
    again = chips.load_chip_state(path, 7000)
    assert again.dead_ms == 7000
    assert again.passes == {"15": [[0, 0]]}
    assert again.pending == {"X": [[1, 1, 1]]}
    assert again.unwritten == ["15#1 0:0:0.000#nextLap#"]
    assert again.processed_lines == 2
    again.chip_map = chips.ChipMap(bib_of={"A": "15"})
    assert again.on_read("A", 3000) == []  # same pass as before the restart


def test_a_missing_or_broken_state_is_none(tmp_path):
    assert chips.load_chip_state(str(tmp_path / "none.json"), 5000) is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert chips.load_chip_state(str(broken), 5000) is None
    old = tmp_path / "old.json"
    old.write_text('{"version": 99, "passes": {"15": [[0, 0]]}}', encoding="utf-8")
    assert chips.load_chip_state(str(old), 5000) is None
    assert not chips.save_chip_state(
        str(tmp_path / "no" / "dir" / "s.json"), chips.ChipTiming()
    )


def test_a_lost_state_comes_back_from_the_raw_reads_without_crossings():
    raw = ["A#1 0:0:0.000#", "x#1 0:0:0.100#", "A#1 0:0:2.000#", "A#1 0:0:9.000#", "?"]
    timing = chips.rebuilt_timing(raw, chips.ChipMap(bib_of={"A": "15"}), 5000)
    day = 86_400_000
    assert timing.passes == {"15": [[day, day + 2000], [day + 9000, day + 9000]]}
    assert timing.pending == {"X": [[day + 100, day + 100, 1]]}
    assert timing.unwritten == []
    assert timing.processed_lines == 5
    assert timing.on_read("A", day + 3000) == []  # still the first pass


def test_the_state_is_on_disk_before_it_replaces_the_old_one(tmp_path, monkeypatch):
    synced: list[int] = []
    monkeypatch.setattr(rf.os, "fsync", synced.append)
    assert chips.save_chip_state(str(tmp_path / "s.json"), chips.ChipTiming())
    assert len(synced) == 1


def test_a_state_save_held_up_by_a_reader_never_waits_on_the_window(
    tmp_path, monkeypatch
):
    slept: list[float] = []

    def busy(source, target):
        raise PermissionError("sharing violation")

    monkeypatch.setattr(rf.os, "replace", busy)
    monkeypatch.setattr(rf.time, "sleep", slept.append)
    assert not chips.save_chip_state(str(tmp_path / "s.json"), chips.ChipTiming())
    assert slept == []  # given up at once; the window tries again a bit later
    assert not (tmp_path / "s.json.tmp").exists()


def test_raw_reads_lines_give_chip_and_time():
    assert chips.raw_read("e280#1 0:0:1.500#dev#1#-60#r#") == ("E280", 86_401_500)
    assert chips.raw_read("A#1 0:0:1.500##") == ("A", 86_401_500)
    assert chips.raw_read("A#not a time#") is None
    assert chips.raw_read("#1 0:0:1.500#") is None
    assert chips.raw_read("") is None


def test_unknown_chips_are_listed_with_first_and_last_read_and_count():
    timing = chips.ChipTiming()
    timing.chip_map = chips.ChipMap(conflicts={"Y": ["15", "16"]})
    for chip, at in (("X", 5), ("Y", 6), ("X", 1), ("X", 9)):
        timing.on_read(chip, at)
    assert timing.unknown() == {"X": (1, 9, 3)}
    made = timing.set_map(
        chips.ChipMap(bib_of={"X": "22"}, conflicts={"Y": ["15", "16"]})
    )
    assert made == [("22", 1)]
    assert timing.unknown() == {}
    assert timing.pending == {"Y": [[6, 6, 1]]}


def test_a_chip_left_by_the_antenna_is_one_run_not_every_read():
    timing = chips.ChipTiming(5000)
    for at in range(0, 3_600_000, 20):  # an hour, 50 reads a second
        timing.on_read("X", at)
    assert timing.pending == {"X": [[0, 3_599_980, 180_000]]}
    assert timing.unknown() == {"X": (0, 3_599_980, 180_000)}


def _fr010(old: list[list[int]], dead: int, reads: list[int]):
    """FR-010 from scratch: all the bib's reads less than the dead time apart are one
    pass, and only a pass with no crossing in it yet gets one, at its first read."""
    items = sorted([(a, b, True) for a, b in old] + [(t, t, False) for t in reads])
    groups: list[list] = []
    for first, last, crossed in items:
        if groups and first < groups[-1][1] + dead:
            group = groups[-1]
            group[1], group[2] = max(group[1], last), group[2] or crossed
        else:
            groups.append([first, last, crossed])
    made = [first for first, _, crossed in groups if not crossed]
    return made, [[first, last] for first, last, _ in groups]


def test_waiting_reads_bind_as_fr_010_says():
    rnd = random.Random(49)  # noqa: S311 - test data, not security
    for _ in range(500):
        timing = chips.ChipTiming(5000)
        timing.chip_map = chips.ChipMap(bib_of={"A": "15"})
        for at in sorted(rnd.sample(range(0, 120_000, 500), rnd.randrange(0, 8))):
            timing.on_read("A", at)
        before = [list(p) for p in timing.passes.get("15", [])]
        late = [rnd.randrange(0, 120_000, 250) for _ in range(rnd.randrange(1, 25))]
        for at in late:  # in the order they came, not in time order
            timing.on_read("X", at)
        made = timing.set_map(chips.ChipMap(bib_of={"A": "15", "X": "15"}))
        expected, passes = _fr010(before, 5000, late)
        assert made == [("15", at) for at in expected]
        assert timing.passes["15"] == passes
