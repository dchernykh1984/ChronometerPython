"""data/sources.txt: defaults, round trip, connector settings."""

from __future__ import annotations

from app import sources_config as sc


def test_defaults_when_there_is_no_file(tmp_path):
    cfg = sc.load_sources(str(tmp_path / "sources.txt"))
    assert cfg["source"] == "hand"
    assert cfg["dead_time_s"] == "5"
    assert cfg["start_protocol"] == "data/start.txt"


def test_settings_round_trip_and_unknown_keys_stay(tmp_path):
    path = str(tmp_path / "sources.txt")
    cfg = sc.load_sources(path)
    cfg["source"] = "chips"
    cfg["later"] = "kept"
    sc.set_connector_settings(cfg, "replay", {"path": "r.txt", "speed": 10})
    assert sc.save_sources(cfg, path)
    again = sc.load_sources(path)
    assert again["source"] == "chips" and again["later"] == "kept"
    assert sc.connector_settings(again, "replay") == {"path": "r.txt", "speed": 10}


def test_a_bad_value_falls_back_to_defaults(tmp_path):
    path = tmp_path / "sources.txt"
    path.write_text("source=video\nsettings.dummy-beam={broken\n", encoding="utf-8")
    cfg = sc.load_sources(str(path))
    assert cfg["source"] == "hand"
    assert sc.connector_settings(cfg, "dummy-beam") == {"min_s": 5, "max_s": 20}
    assert sc.connector_settings(cfg, "nothing") == {}


def test_a_folder_that_cannot_be_written_is_reported(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert not sc.save_sources({"source": "hand"}, str(blocker / "sources.txt"))


def test_a_dead_time_that_is_not_a_whole_number_gives_the_default():
    assert sc.dead_time_s({"dead_time_s": "7"}) == 7
    for typo in ("2.5", "5s", ""):
        assert sc.dead_time_s({"dead_time_s": typo}) == 5
    assert sc.dead_time_s({}) == 5


def test_settings_are_written_in_one_step(tmp_path, monkeypatch):
    from app import results_file as rf

    path = tmp_path / "sources.txt"
    assert sc.save_sources({"source": "beam"}, str(path))

    def crash(*a):
        raise OSError("power cut")

    monkeypatch.setattr(rf.os, "replace", crash)  # dies before the new file is in place
    assert not sc.save_sources({"source": "chips"}, str(path))
    assert sc.load_sources(str(path))["source"] == "beam"
