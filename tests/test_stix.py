import pytest

from occam.ach import ACHEngine
from occam.extract import extract
from occam.scenario import load_scenario
from occam.stix import export, validate

from conftest import DEMO

stix2 = pytest.importorskip("stix2")


@pytest.mark.parametrize("name", ["clean_attribution", "false_flag_games", "thin_evidence"])
def test_assessment_bundle_is_valid_stix21(name):
    q, actors, ev, _ = load_scenario(DEMO / "scenarios" / f"{name}.json")
    bundle = export(assessment=ACHEngine(actors, ev, q).assess())
    assert validate(bundle) == len(bundle["objects"])


def test_extraction_bundle_is_valid_stix21():
    text = (DEMO / "reports" / "r3_tide_energy.txt").read_text()
    bundle = export(extraction=extract(text, "r3"))
    assert validate(bundle) >= 1


def test_quote_in_indicator_is_escaped():
    bundle = export(extraction=extract("callback to hxxp://a[.]example/x'y and 10.0.0.1", "t"))
    validate(bundle)


@pytest.mark.parametrize("with_extraction", [False, True])
def test_every_reference_resolves_inside_the_bundle(with_extraction):
    q, actors, ev, _ = load_scenario(DEMO / "scenarios" / "false_flag_games.json")
    ext = extract((DEMO / "reports" / "r3_tide_energy.txt").read_text(), "r3") if with_extraction else None
    bundle = export(extraction=ext, assessment=ACHEngine(actors, ev, q).assess())
    ids = {o["id"] for o in bundle["objects"]}
    refs = {r for o in bundle["objects"] for r in o.get("object_refs", [])}
    assert refs and refs <= ids
    assert validate(bundle) == len(bundle["objects"])
