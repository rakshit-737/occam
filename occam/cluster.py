"""Campaign clustering: group extraction results by shared TTPs / tools / infra.

Baseline is weighted-Jaccard similarity + single-linkage (union-find) over a
threshold. Common techniques are ignored since they carry no signal. Graph
community detection (Louvain) is a TODO once a real graph store exists.
"""
from __future__ import annotations

from dataclasses import dataclass

from .attack import AttackKB, load_bundled
from .models import ExtractionResult

FEATURE_WEIGHTS = {"ttp": 1.0, "tool": 2.0, "ioc": 3.0}


def features(r: ExtractionResult, kb: AttackKB) -> dict[str, float]:
    f: dict[str, float] = {}
    for t in r.techniques:
        if not kb.is_common(t.technique_id):
            f[f"ttp:{t.technique_id}"] = FEATURE_WEIGHTS["ttp"]
    for t in r.tools:
        f[t.technique_id] = FEATURE_WEIGHTS["tool"]
    for i in r.indicators:
        if i.type in ("ipv4", "domain", "sha256", "md5", "url"):
            f[f"ioc:{i.value.lower()}"] = FEATURE_WEIGHTS["ioc"]
    return f


def similarity(a: dict[str, float], b: dict[str, float]) -> float:
    keys = a.keys() | b.keys()
    if not keys:
        return 0.0
    num = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    den = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return num / den if den else 0.0


@dataclass
class Campaign:
    id: str
    members: list[str]
    shared_features: list[str]


def cluster(results: list[ExtractionResult], threshold: float = 0.3, kb: AttackKB | None = None) -> list[Campaign]:
    kb = kb or load_bundled()
    feats = [features(r, kb) for r in results]
    parent = list(range(len(results)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            if similarity(feats[i], feats[j]) >= threshold:
                parent[find(i)] = find(j)

    groups: dict[int, list[int]] = {}
    for i in range(len(results)):
        groups.setdefault(find(i), []).append(i)
    out = []
    for n, idx in enumerate(sorted(groups.values(), key=lambda g: (-len(g), g[0])), 1):
        shared = set(feats[idx[0]])
        for i in idx[1:]:
            shared &= set(feats[i])
        out.append(Campaign(f"CAMPAIGN-{n:02d}", sorted(results[i].source_id for i in idx), sorted(shared) if len(idx) > 1 else []))
    return out
