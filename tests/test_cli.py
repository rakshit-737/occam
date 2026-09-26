import json

from conftest import FIX

from occam.cli import main


def test_demo_runs(capsys):
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "CAMPAIGN-01" in out and "CONFIDENCE" in out


def test_ach_json_and_override(capsys):
    assert main(["ach", str(FIX / "scenarios" / "clean_attribution.json"), "--json", "--override", "E1:H-QUILL=II"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["matrix"]["E1"]["H-QUILL"] == "II"


def test_extract_navigator(capsys):
    assert main(["extract", str(FIX / "reports" / "r1_ember_retail.txt"), "--navigator"]) == 0
    assert "T1486" in capsys.readouterr().out


def test_bad_override_is_clean_error():
    assert main(["ach", str(FIX / "scenarios" / "clean_attribution.json"), "--override", "E1:H-NOPE=I"]) == 2
