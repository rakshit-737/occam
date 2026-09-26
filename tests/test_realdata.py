"""Tests against the downloaded real datasets (skipped when absent, e.g. in CI).

Run ``python scripts/download_data.py`` first, or point ``OCCAM_DATA`` at the
data directory.
"""
import json
import os
from pathlib import Path

import pytest

from conftest import ROOT

DATA = Path(os.environ.get("OCCAM_DATA", ROOT.parent.parent / "datasets" / "occam"))
ATTACK = DATA / "enterprise-attack-19.2.json"

pytestmark = [
    pytest.mark.realdata,
    pytest.mark.skipif(not ATTACK.exists(), reason="real ATT&CK bundle not downloaded"),
]


@pytest.fixture(scope="module")
def attack():
    from occam.knowledge import AttackData

    return AttackData.load(ATTACK)


def test_attack_bundle_counts(attack):
    s = attack.summary()
    assert s["version"] == "19.2"
    assert s["groups"] > 150 and s["software"] > 700 and s["techniques"] > 600
    assert s["procedure_examples"] > 10_000


def test_real_profiles_and_rarity(attack):
    profiles = {p.id: p for p in attack.actor_profiles()}
    assert "G0007" in profiles  # APT28
    kb = attack.to_kb()
    assert kb.is_common("T1105")  # Ingress Tool Transfer: used by a large share of groups
    assert any(kb.is_rare(t) for t in profiles["G0007"].techniques)


def test_leave_one_report_out_hides_the_incident(attack):
    from occam.evaluation import HoldoutWorld, incidents

    inc = incidents(attack, max_per_group=1)[0]
    profiles, _ = HoldoutWorld.build(attack).world(inc)
    held = next(p for p in profiles if p.id == inc.group)
    only_this_report = {
        u.target for u in attack.uses if u.source == inc.group and set(u.references) == {inc.reference}
    }
    assert not (only_this_report & set(held.techniques + held.tools))


def test_stix2_validates_real_group_export(attack):
    pytest.importorskip("stix2")
    from occam.ach import ACHEngine
    from occam.attribution import evidence_from_items, planted_markers
    from occam.stix import export, validate

    kb = attack.to_kb()
    profiles = [p for p in attack.actor_profiles() if p.id in {"G0007", "G0016", "G0032"}]
    ev = evidence_from_items(profiles[0].techniques[:6], kb) + planted_markers("G0032", 2)
    bundle = export(assessment=ACHEngine(profiles, ev, kb=kb).assess())
    assert validate(bundle) == len(bundle["objects"])


@pytest.mark.skipif(not (DATA / "tram" / "multi_label.json").exists(), reason="TRAM2 not downloaded")
def test_tram_label_space():
    rows = json.loads((DATA / "tram" / "multi_label.json").read_text(encoding="utf-8"))
    labels = {x for r in rows for x in r["labels"]}
    assert len(labels) == 50 and len({r["doc_title"] for r in rows}) == 151
