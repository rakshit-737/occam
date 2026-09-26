import pytest

from occam.metrics import purity

nx = pytest.importorskip("networkx")
from occam.graph import build_diamond_graph, louvain_clusters, single_linkage_clusters, weighted_jaccard  # noqa: E402

EVENTS = {
    "a1": {"capability": ["T1486", "T1566.001", "S0001"], "infrastructure": ["1.2.3.4"], "victim": ["retail"]},
    "a2": {"capability": ["T1486", "S0001", "T1041"], "infrastructure": ["1.2.3.4"], "victim": ["finance"]},
    "a3": {"capability": ["T1486", "T1566.001", "S0001", "T1041"], "infrastructure": [], "victim": ["retail"]},
    "b1": {"capability": ["T1485", "T1490", "S0003"], "infrastructure": ["evil.example"], "victim": ["energy"]},
    "b2": {"capability": ["T1485", "T1021.002", "S0003"], "infrastructure": ["evil.example"], "victim": ["energy"]},
    "b3": {"capability": ["T1490", "T1021.002", "S0003", "T1485"], "infrastructure": [], "victim": ["energy"]},
}
TRUTH = {"a1": "A", "a2": "A", "a3": "A", "b1": "B", "b2": "B", "b3": "B"}


def test_diamond_graph_schema():
    g = build_diamond_graph(EVENTS)
    kinds = {d["kind"] for _, d in g.nodes(data=True)}
    assert {"event", "capability", "infrastructure", "victim"} <= kinds
    assert g.has_edge("a1", "infrastructure:1.2.3.4")


def test_louvain_recovers_campaigns():
    lab = louvain_clusters(EVENTS)
    ids = list(EVENTS)
    assert purity([TRUTH[i] for i in ids], [lab[i] for i in ids]) == 1.0
    assert lab["a1"] != lab["b1"]


def test_single_linkage_baseline_and_similarity():
    lab = single_linkage_clusters(EVENTS, threshold=0.2)
    assert lab["a1"] == lab["a2"] and lab["b1"] == lab["b2"]
    assert weighted_jaccard({"x": 1.0}, {"x": 1.0}) == 1.0
    assert weighted_jaccard({}, {}) == 0.0


_DETERMINISM_SCRIPT = """
import json, random
from occam.graph import louvain_clusters
rng = random.Random(3)
pool = [f"T{1000 + i}" for i in range(60)]
events = {f"e{i:03d}": {"capability": rng.sample(pool, 6)} for i in range(120)}
print(json.dumps(louvain_clusters(events, resolution=3.0, knn=5), sort_keys=True))
"""


def test_louvain_independent_of_hash_seed():
    # Regression: set iteration over str ids made benchmark results vary with PYTHONHASHSEED.
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    outs = set()
    for seed in ("0", "1", "123"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(root)}
        outs.add(subprocess.run([sys.executable, "-c", _DETERMINISM_SCRIPT], env=env, check=True,
                                capture_output=True, text=True).stdout)
    assert len(outs) == 1
