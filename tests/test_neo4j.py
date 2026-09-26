import pytest

from occam.neo4j import _lit, to_cypher


def test_cypher_export_is_deterministic_and_escaped():
    ev = {"r2": {"capability": ["T1059", "T1059"], "infrastructure": ["evil'.com"]},
          "r1": {"victim": ["energy"], "adversary": ["G0001"]}}
    out = to_cypher(ev, campaigns={"r1": "C1"})
    assert out == to_cypher(ev, campaigns={"r1": "C1"})
    assert "MERGE (e:Event {id: 'r1'}) SET e.campaign = 'C1';" in out
    assert out.index("'r1'") < out.index("'r2'")
    assert out.count("{value: 'T1059'}") == 1
    assert "evil\\'.com" in out
    assert ":ATTRIBUTED_TO" in out and ":TARGETS" in out


def test_literal_blocks_injection():
    s = _lit("x'}) DETACH DELETE n //\n")
    assert s.startswith("'") and s.endswith("'")
    assert "\'" in s and "\n" not in s


def test_unknown_facet_rejected():
    with pytest.raises(ValueError):
        to_cypher({"e": {"weird": ["x"]}})
