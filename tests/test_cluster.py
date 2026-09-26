from occam.cluster import cluster, similarity
from occam.extract import extract

from conftest import FIX


def test_reports_cluster_into_campaigns():
    files = sorted((FIX / "reports").glob("*.txt"))
    results = [extract(f.read_text(), f.name) for f in files]
    camps = {tuple(c.members) for c in cluster(results)}
    assert ("r1_ember_retail.txt", "r2_ember_finance.txt") in camps
    assert ("r3_tide_energy.txt", "r4_tide_events.txt") in camps
    assert ("r5_quill_research.txt",) in camps


def test_similarity_bounds():
    assert similarity({}, {}) == 0.0
    assert similarity({"a": 1}, {"a": 1}) == 1.0
    assert similarity({"a": 1}, {"b": 1}) == 0.0
