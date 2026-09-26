from conftest import FIX

from occam.attack import convert_stix_bundle, load_bundled
from occam.extract import extract, navigator_layer


def test_bundled_kb_loads():
    kb = load_bundled()
    assert "T1485" in kb.techniques and kb.is_common("T1059.001")


def test_ttps_have_valid_source_spans():
    text = (FIX / "reports" / "r3_tide_energy.txt").read_text()
    r = extract(text, "r3")
    assert {"T1190", "T1021.002", "T1485", "T1490", "T1070.001"} <= r.technique_ids()
    for h in r.techniques + r.tools:
        assert text[h.span.start:h.span.end] == h.span.text
        assert h.span.text.lower() == h.matched.lower()


def test_defanged_iocs_are_refanged_and_spanned():
    text = "beacon to hxxps://evil-cdn[.]xyz/gate.php and 185.220.101.47, CVE-2099-0001"
    r = extract(text, "t")
    vals = {(i.type, i.value) for i in r.indicators}
    assert ("url", "https://evil-cdn.xyz/gate.php") in vals
    assert ("ipv4", "185.220.101.47") in vals
    assert ("cve", "CVE-2099-0001") in vals
    for i in r.indicators:
        assert text[i.span.start:i.span.end] == i.span.text


def test_no_substring_false_positive():
    assert "T1047" not in extract("the wmicroscope was fine", "t").technique_ids()


def test_navigator_layer():
    layer = navigator_layer(extract("ransomware encrypted files", "t"))
    assert layer["domain"] == "enterprise-attack"
    assert layer["techniques"][0]["techniqueID"] == "T1486"


def test_convert_stix_bundle():
    bundle = {"objects": [
        {"type": "attack-pattern", "name": "Data Destruction", "kill_chain_phases": [{"phase_name": "impact"}],
         "external_references": [{"source_name": "mitre-attack", "external_id": "T1485"}]},
        {"type": "attack-pattern", "name": "Old", "revoked": True,
         "external_references": [{"source_name": "mitre-attack", "external_id": "T9999"}]},
        {"type": "malware", "name": "FakeMal", "x_mitre_aliases": ["FakeMal"],
         "external_references": [{"source_name": "mitre-attack", "external_id": "S9999"}]},
    ]}
    out = convert_stix_bundle(bundle)
    assert [t["id"] for t in out["techniques"]] == ["T1485"]
    assert out["tools"][0]["id"] == "S9999"
    assert out["tools"][0]["keywords"] == ["FakeMal"]
    assert out["techniques"][0]["tactic"] == "impact"
