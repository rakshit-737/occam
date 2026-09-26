import json

from occam.knowledge import AttackData, clean_text

from conftest import FIX

BUNDLE = json.loads((FIX / "mini_attack.json").read_text(encoding="utf-8"))


def data():
    return AttackData.from_bundle(BUNDLE)


def test_summary_counts_and_version():
    s = data().summary()
    assert s["version"] == "0.1"
    assert s["groups"] == 3 and s["software"] == 3 and s["campaigns"] == 1
    assert s["attributed_campaigns"] == 1


def test_revoked_and_deprecated_objects_are_dropped():
    b = json.loads(json.dumps(BUNDLE))
    for o in b["objects"]:
        if o["type"] == "attack-pattern":
            o["revoked"] = True
            break
    assert len(AttackData.from_bundle(b).techniques) == len(data().techniques) - 1


def test_actor_profiles_split_techniques_and_software():
    profiles = {p.id: p for p in data().actor_profiles()}
    ember = profiles["G0001"]
    assert ember.name == "Ember Spider"
    assert all(t.startswith("T") for t in ember.techniques)
    assert all(t.startswith("S") for t in ember.tools)
    assert "T1486" in ember.techniques


def test_usage_counts_drive_rarity():
    d = data()
    counts = d.group_usage_counts()
    assert counts["T1059.001"] == 3  # every group uses PowerShell
    kb = d.to_kb(common_frac=0.9, rare_max=1)
    assert kb.is_common("T1059.001")
    assert kb.is_rare("T1486") and not kb.is_rare("T1059.001")


def test_procedures_are_cleaned_training_examples():
    procs = data().procedures()
    assert procs and all(tid.startswith("T") for _, tid, _ in procs)
    assert not any("(Citation" in text for text, _, _ in procs)


def test_clean_text():
    assert clean_text("Uses [PowerShell](https://x) (Citation: Foo 2020) <code>cmd.exe</code>.") == "Uses PowerShell cmd.exe."
