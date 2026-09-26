import json

from conftest import FIX

from occam.attribution import ACHAttributor, SimilarityAttributor, evidence_from_items, planted_markers
from occam.evaluation import crossfit_calibrate, evaluate, incidents, summarize
from occam.knowledge import AttackData

DATA = AttackData.from_bundle(json.loads((FIX / "mini_attack.json").read_text(encoding="utf-8")))


def world():
    return DATA.actor_profiles(), DATA.to_kb(common_frac=0.9, rare_max=1)


def test_similarity_names_matching_group():
    profiles, kb = world()
    ev = evidence_from_items(["T1486", "T1566.001", "S0001"], kb)
    a = SimilarityAttributor(profiles, kb).attribute(ev)
    assert a.leading == "G0001" and 0 < a.probability <= 1
    assert a.ranked_actors[0] == "G0001"


def test_similarity_is_fooled_by_planted_markers():
    profiles, kb = world()
    ev = evidence_from_items(["T1486"], kb) + planted_markers("G0002", 6)
    assert SimilarityAttributor(profiles, kb).attribute(ev).leading == "G0002"


def test_ach_resists_planted_markers():
    profiles, kb = world()
    ev = evidence_from_items(["T1486", "T1566.001", "S0001"], kb) + planted_markers("G0002", 3)
    a = ACHAttributor(profiles, kb).attribute(ev)
    assert a.leading != "G0002"
    assert a.confidence != "high"


def test_incidents_and_evaluation_protocol():
    incs = incidents(DATA, min_items=2, min_profile=1)
    assert incs and all(len(i.items) >= 2 for i in incs)
    res = evaluate(DATA, {"sim": SimilarityAttributor, "ach": ACHAttributor}, min_items=2, max_per_group=None)
    assert set(res) == {"sim", "ach"}
    for per in res.values():
        assert set(per) == {"closed", "open", "false_flag"}
        # in the open world the true group has been removed and cannot be named
        assert not any(o.attribution.leading == o.incident.group for o in per["open"])
    s = summarize(res["sim"]["closed"])
    assert 0 <= s["brier"] <= 1 and s["n"] == len(res["sim"]["closed"])
    cal = crossfit_calibrate(res["ach"]["closed"])
    assert len(cal) == len(res["ach"]["closed"]) and all(0 < p < 1 for p in cal)


def test_ach_shortlist_keeps_framed_actor():
    profiles, kb = world()
    ev = evidence_from_items(["T1486", "T1566.001", "S0001"], kb) + planted_markers("G0003", 2)
    att = ACHAttributor(profiles, kb, shortlist=1)
    ids = {p.id for p in att.candidates(ev)}
    assert ids == {"G0001", "G0003"}  # top-1 by similarity + the actor the markers frame
    assert att.attribute(ev).leading != "G0003"
