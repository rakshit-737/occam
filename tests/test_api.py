import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from occam.api import COLLECTION_ID, app  # noqa: E402

client = TestClient(app)


def test_health_and_workbench():
    assert client.get("/health").json()["status"] == "ok"
    r = client.get("/")
    assert r.status_code == 200 and "OCCAM" in r.text


def test_ach_override_changes_matrix():
    base = client.post("/ach", json={"scenario": "clean_attribution"}).json()
    over = client.post("/ach", json={"scenario": "clean_attribution",
                                     "overrides": [{"evidence": "E1", "hypothesis": "H-QUILL", "rating": "II"}]}).json()
    assert over["matrix"]["E1"]["H-QUILL"] == "II"
    assert over["overridden"] == ["E1:H-QUILL"]
    assert base["confidence"] in {"low", "moderate", "high"}


def test_unknown_scenario_and_traversal_rejected():
    assert client.post("/ach", json={"scenario": "nope"}).status_code == 404
    assert client.post("/ach", json={"scenario": "../actors"}).status_code == 404


def test_extract_returns_navigator_layer():
    r = client.post("/extract", json={"text": "The ransomware encrypted files."}).json()
    assert r["navigator"]["domain"] == "enterprise-attack"


def test_taxii_publish_roundtrip():
    assert client.get("/taxii2/").json()["api_roots"]
    client.post("/ach", json={"scenario": "false_flag_games", "publish": True})
    objs = client.get(f"/taxii2/api/collections/{COLLECTION_ID}/objects/").json()["objects"]
    assert any(o["type"] == "note" for o in objs)
    assert client.get("/taxii2/api/collections/bogus/objects/").status_code == 404
