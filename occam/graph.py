"""Diamond-model knowledge graph + community-detection campaign clustering.

Graph schema (networkx ``MultiDiGraph``-compatible, stored as a ``Graph``):

* ``event``          -- a report / campaign / incident (the Diamond *event*)
* ``adversary``      -- an attributed actor (only when known)
* ``capability``     -- an ATT&CK technique or software
* ``infrastructure`` -- IP / domain / URL / hash indicators
* ``victim``         -- sector / victimology tag

Clustering projects events onto an event-event similarity graph (IDF-weighted
Jaccard over capabilities + infrastructure; infrastructure weighted higher)
and runs Louvain community detection. The single-linkage union-find clusterer
in :mod:`occam.cluster` is kept as the baseline.

Requires the optional ``graph`` extra (networkx).
"""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping

INFRA_WEIGHT = 3.0


def build_diamond_graph(events: Mapping[str, dict[str, Iterable[str]]]):
    """events: {event_id: {"capability": [...], "infrastructure": [...], "victim": [...], "adversary": [...]}}"""
    import networkx as nx

    g = nx.Graph()
    for ev, facets in events.items():
        g.add_node(ev, kind="event")
        for kind, values in facets.items():
            for v in values:
                node = f"{kind}:{v}"
                g.add_node(node, kind=kind, value=v)
                g.add_edge(ev, node, kind=kind)
    return g


def _weights(events: Mapping[str, dict[str, Iterable[str]]]) -> dict[str, dict[str, float]]:
    df: Counter[str] = Counter()
    feats: dict[str, set[str]] = {}
    for ev, facets in events.items():
        f = {f"{k}:{v}" for k in ("capability", "infrastructure") for v in facets.get(k, [])}
        feats[ev] = f
        df.update(f)
    n = len(events) or 1
    out = {}
    for ev, f in feats.items():
        out[ev] = {
            x: math.log((1 + n) / (1 + df[x])) * (INFRA_WEIGHT if x.startswith("infrastructure:") else 1.0)
            for x in f
            if df[x] < n  # a feature present in every event carries no signal
        }
    return out


def weighted_jaccard(a: dict[str, float], b: dict[str, float]) -> float:
    keys = a.keys() | b.keys()
    num = sum(min(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    den = sum(max(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    return num / den if den else 0.0


def similarity_graph(events: Mapping[str, dict[str, Iterable[str]]], min_sim: float = 0.05):
    import networkx as nx

    w = _weights(events)
    ids = list(events)
    g = nx.Graph()
    g.add_nodes_from(ids)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            s = weighted_jaccard(w[a], w[b])
            if s >= min_sim:
                g.add_edge(a, b, weight=s)
    return g


def louvain_clusters(events: Mapping[str, dict[str, Iterable[str]]], resolution: float = 1.0,
                     min_sim: float = 0.05, seed: int = 0) -> dict[str, int]:
    """event id -> community index."""
    from networkx.algorithms.community import louvain_communities

    g = similarity_graph(events, min_sim)
    comms = louvain_communities(g, weight="weight", resolution=resolution, seed=seed)
    out: dict[str, int] = {}
    for i, c in enumerate(sorted(comms, key=lambda c: (-len(c), sorted(c)[0]))):
        for ev in c:
            out[ev] = i
    return out


def single_linkage_clusters(events: Mapping[str, dict[str, Iterable[str]]], threshold: float = 0.3) -> dict[str, int]:
    """Baseline: unweighted Jaccard + union-find over a threshold (as occam.cluster)."""
    ids = list(events)
    feats = {e: {f"{k}:{v}" for k in ("capability", "infrastructure") for v in events[e].get(k, [])} for e in ids}
    parent = {e: e for e in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            u = feats[a] | feats[b]
            if u and len(feats[a] & feats[b]) / len(u) >= threshold:
                parent[find(a)] = find(b)
    roots: dict[str, int] = {}
    return {e: roots.setdefault(find(e), len(roots)) for e in ids}
