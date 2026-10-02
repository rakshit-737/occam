"""Campaign / temporal protocols, the authentic-marker and mimicry settings
and the ACH ablation switches, on the tiny CI fixture bundle."""
import json

import pytest

from occam.ach import ACHEngine
from occam.attribution import ACHAttributor, IDFCoverageAttributor, SimilarityAttributor, evidence_from_items, planted_markers
from occam.evaluation import (
    ALL_SETTINGS,
    HoldoutWorld,
    Incident,
    StaticWorld,
    campaign_incidents,
    evaluate,
    mimicry_items,
    temporal_incidents,
)
from occam.knowledge import AttackData

from conftest import FIX

BUNDLE = json.loads((FIX / "mini_attack.json").read_text(encoding="utf-8"))
DATA = AttackData.from_bundle(BUNDLE)


def test_campaign_incident_is_created():
    incs = campaign_incidents(DATA, min_items=2, min_profile=1)
    assert len(incs) == 1
    inc = incs[0]
    assert inc.kind == "campaign" and inc.group == "G0002"
    assert inc.ref_set == {"R7"}


def test_campaign_holdout_removes_items_cited_only_by_campaign_refs():
    hw = HoldoutWorld.build(DATA)
    g = "G0002"
    base = set(hw.base_profiles[g].techniques) | set(hw.base_profiles[g].tools)
    # a fake campaign whose refs cover R3: every item cited only by R3 must go
    inc = Incident(g, "C-test", ["T1"], ("R3",), kind="campaign")
    profiles, _ = hw.world(inc)
    after = next(p for p in profiles if p.id == g)
    kept = set(after.techniques) | set(after.tools)
    only_r3 = {x for x, r in hw._support[g].items() if r <= {"R3"}}
    assert only_r3 and not (kept & only_r3)
    assert kept == base - only_r3


def test_report_incident_ref_set_defaults_to_reference():
    assert Incident("G1", "R1", ["T1"]).ref_set == {"R1"}


def test_temporal_incidents_only_new():
    old_b = json.loads(json.dumps(BUNDLE))
    # the "old" release lacks the campaign and every R5-cited relationship
    camp_ids = {o["id"] for o in old_b["objects"] if o["type"] == "campaign"}
    old_b["objects"] = [o for o in old_b["objects"]
                        if o["id"] not in camp_ids
                        and not (o["type"] == "relationship" and (o.get("source_ref") in camp_ids
                                 or any(r.get("source_name") == "R5" for r in o.get("external_references", []))))]
    old = AttackData.from_bundle(old_b)
    incs = temporal_incidents(old, DATA, min_items=2, min_profile=1)
    assert incs
    for i in incs:
        assert i.reference not in old.campaigns
        if i.kind == "report":
            assert i.reference == "R5"


def test_static_world_drop_group():
    sw = StaticWorld.build(DATA)
    inc = Incident("G0001", "R1", ["T1486"])
    with_g, _ = sw.world(inc)
    without, _ = sw.world(inc, drop_group=True)
    assert "G0001" in {p.id for p in with_g} and "G0001" not in {p.id for p in without}


def test_all_settings_run_and_are_scored():
    res = evaluate(DATA, {"sim": SimilarityAttributor, "ach": ACHAttributor, "cov": IDFCoverageAttributor},
                   settings=ALL_SETTINGS, min_items=2, max_per_group=None, n_markers=2)
    for per in res.values():
        for o in per["authentic"]:
            assert o.marker_target == o.incident.group
            assert o.correct == (o.attribution.leading == o.incident.group)
        for o in per["mimicry"] + per["false_flag"]:
            assert o.marker_target and o.marker_target != o.incident.group
    # the marker-trusting baseline always follows authentic markers to the true group
    assert all(o.correct for o in res["sim"]["authentic"])


def test_mimicry_items_are_rarest_new_items_of_framed_group():
    profiles, kb = DATA.actor_profiles(), DATA.to_kb()
    got = mimicry_items(profiles, kb, "G0002", ["T1486"], 2)
    prof = next(p for p in profiles if p.id == "G0002")
    assert len(got) == 2 and set(got) <= set(prof.techniques) | set(prof.tools)


def test_ablation_switches():
    profiles, kb = DATA.actor_profiles(), DATA.to_kb(common_frac=0.9, rare_max=1)
    ev = evidence_from_items(["T1486", "T1566.001", "S0001"], kb) + planted_markers("G0002", 3)
    full = ACHEngine(profiles, ev, kb=kb, sensitivity=False)
    kinds = {h.kind for h in full.hypotheses}
    assert {"false_flag", "unknown"} <= kinds
    no_ff = ACHEngine(profiles, ev, kb=kb, sensitivity=False, false_flag_hypotheses=False, unknown_hypothesis=False)
    assert {h.kind for h in no_ff.hypotheses} == {"actor"}
    a = ACHEngine(profiles, ev, kb=kb, sensitivity=False, confidence_caps=False).assess()
    assert not any("Capped" in r for r in a.rationale)
    with pytest.raises(ValueError):
        ACHEngine(profiles[:1], ev[:1], kb=kb, false_flag_hypotheses=False, unknown_hypothesis=False)


def test_similarity_hard_score_ignores_markers():
    profiles, kb = DATA.actor_profiles(), DATA.to_kb()
    ev = evidence_from_items(["T1486"], kb)
    s = SimilarityAttributor(profiles, kb)
    assert s.attribute(ev).hard_score == pytest.approx(s.attribute(ev + planted_markers("G0002", 5)).hard_score)
