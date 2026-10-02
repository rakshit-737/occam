import json

from occam.cli import main

from conftest import DEMO, FIX


def test_demo_runs(capsys):
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "CAMPAIGN-01" in out and "CONFIDENCE" in out


def test_ach_json_and_override(capsys):
    assert main(["ach", str(DEMO / "scenarios" / "clean_attribution.json"), "--json", "--override", "E1:H-QUILL=II"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["matrix"]["E1"]["H-QUILL"] == "II"


def test_extract_navigator(capsys):
    assert main(["extract", str(DEMO / "reports" / "r1_ember_retail.txt"), "--navigator"]) == 0
    assert "T1486" in capsys.readouterr().out


def test_bad_override_is_clean_error():
    assert main(["ach", str(DEMO / "scenarios" / "clean_attribution.json"), "--override", "E1:H-NOPE=I"]) == 2


def test_attribute_against_attack_bundle(capsys, tmp_path):
    rep = tmp_path / "r.txt"
    rep.write_text("The actor used EmberLock ransomware and encrypted files after spearphishing attachment lures.")
    assert main(["attribute", str(rep), "--attack", str(FIX / "mini_attack.json"), "--shortlist", "2"]) == 0
    out = capsys.readouterr().out
    assert "CONFIDENCE" in out and "<- " in out


def test_train_classifier_and_use_it(capsys, tmp_path):
    import pytest

    pytest.importorskip("sklearn")
    model = tmp_path / "m.pkl"
    assert main(["train-classifier", "--attack", str(FIX / "mini_attack.json"), "--threshold", "0.3", "--out", str(model)]) == 0
    rep = tmp_path / "r.txt"
    rep.write_text("Victim files were encrypted by the ransomware and a note was dropped.")
    capsys.readouterr()
    assert main(["extract", str(rep), "--classifier", str(model)]) == 0
    assert '"technique_id"' in capsys.readouterr().out
