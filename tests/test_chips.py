"""Chips: the start protocol's field 11 bound to bibs, as every reader does."""

from __future__ import annotations

from app import chips


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
