import json

import pytest

from occam.ach import ACHEngine
from occam.models import Consistency, Evidence, EvidenceKind
from occam.scenario import load_scenario
from occam.stix import export

from conftest import FIX

RANK = {"low": 0, "moderate": 1, "high": 2}


def run(name):
    q, actors, ev, exp = load_scenario(FIX / "scenarios" / f"{name}.json")
    return ACHEngine(actors, ev, q), exp


def test_clean_attribution_high_confidence():
    eng, exp = run("clean_attribution")
    a = eng.assess()
    assert a.leading.hypothesis.id == exp["leading"]
    assert a.confidence == exp["confidence"]
    assert a.false_flag_indicators == []


def test_false_flag_does_not_name_planted_actor():
    eng, exp = run("false_flag_games")
    a = eng.assess()
    assert a.leading.hypothesis.id != exp["not_leading"]
    assert RANK[a.confidence] <= RANK[exp["max_confidence"]]
    assert a.false_flag_indicators
    assert any(h.hypothesis.kind == "false_flag" for h in a.ranking)


def test_thin_evidence_low_confidence_and_conservative():
    eng, _ = run("thin_evidence")
    a = eng.assess()
    assert a.confidence == "low"
    assert a.leading.hypothesis.kind == "unknown"


def test_mandatory_unknown_hypothesis_present():
    eng, _ = run("clean_attribution")
    assert any(h.kind == "unknown" for h in eng.hypotheses)


def test_non_diagnostic_evidence_has_zero_weight():
    eng, _ = run("clean_attribution")
    assert eng.assess().diagnostic_weights["E7"] == 0  # common PowerShell


def test_ranking_uses_inconsistency_not_support():
    eng, _ = run("clean_attribution")
    incs = [s.inconsistency for s in eng.assess().ranking]
    assert incs == sorted(incs, reverse=True)


def test_analyst_override_updates_result():
    eng, _ = run("clean_attribution")
    before = eng.assess()
    for eid in ("E1", "E2", "E3"):
        eng.override(eid, "H-QUILL", "II")
    after = eng.assess()
    assert after.matrix["E1"]["H-QUILL"] is Consistency.II
    assert after.leading.hypothesis.id != before.leading.hypothesis.id


def test_override_validation():
    eng, _ = run("clean_attribution")
    with pytest.raises(KeyError):
        eng.override("E99", "H-QUILL", "I")
    with pytest.raises(ValueError):
        eng.override("E1", "H-QUILL", "maybe")


def test_spoofable_only_evidence_never_high():
    _, actors, _, _ = load_scenario(FIX / "scenarios" / "clean_attribution.json")
    ev = [Evidence(f"E{i}", "planted marker", EvidenceKind.CODE_OVERLAP, points_to=["EMBER"], reliability="A", credibility=1)
          for i in range(6)]
    assert ACHEngine(actors, ev).assess().confidence == "low"


def test_bad_inputs_rejected():
    _, actors, _, _ = load_scenario(FIX / "scenarios" / "clean_attribution.json")
    with pytest.raises(ValueError):
        ACHEngine(actors, []).assess()
    with pytest.raises(ValueError):
        Evidence.from_dict({"id": "x", "description": "d", "kind": "ttp", "reliability": "Z"})
    e = Evidence("E1", "d", EvidenceKind.TTP, "T1485")
    with pytest.raises(ValueError):
        ACHEngine(actors, [e, e])


def test_stix_export_carries_confidence():
    eng, _ = run("false_flag_games")
    b = export(assessment=eng.assess())
    note = [o for o in b["objects"] if o["type"] == "note"][0]
    assert note["confidence"] <= 50 and "false flag" in note["abstract"].lower()


def test_assessment_json_serializable():
    eng, _ = run("false_flag_games")
    json.dumps(eng.assess().to_dict())
