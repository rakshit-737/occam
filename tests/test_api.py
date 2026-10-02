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


def test_hardening_limits_and_errors():
    # DNS rebinding: a foreign Host header is refused
    assert client.get("/health", headers={"Host": "attacker.example"}).status_code == 400
    # oversize body and oversize fields
    assert client.post("/extract", content=b"x" * 1_000_001, headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post("/extract", json={"text": "a", "source_id": "s" * 300}).status_code == 422
    # malformed inline actors / unknown override ids are client errors, not 500s
    assert client.post("/ach", json={"actors": [{"bogus": 1}], "evidence": []}).status_code == 422
    r = client.post("/stix", json={"scenario": "clean_attribution",
                                   "overrides": [{"evidence": "E99", "hypothesis": "H-QUILL", "rating": "II"}]})
    assert r.status_code == 422
    assert client.get("/docs").status_code == 404
    assert client.get("/health").headers["X-Content-Type-Options"] == "nosniff"
