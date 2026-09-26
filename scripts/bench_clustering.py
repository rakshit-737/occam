#!/usr/bin/env python
"""Campaign-clustering benchmark on real ATT&CK activity.

Events are (a) per-report slices of ATT&CK group usage -- the techniques and
software one public report attributes to one group -- and (b) ATT&CK campaign
objects (C00xx) that have an ``attributed-to`` group. Ground truth is the
group. Only groups with >= ``--min-events`` events are kept so every true
cluster has several members. ATT&CK carries no infrastructure, so this is a
capability-only (TTP + software) clustering test -- the hardest case.

Methods: Louvain community detection on an IDF-weighted Jaccard event graph
(``occam.graph``) vs the single-linkage union-find baseline, the latter shown
both at its default threshold and at its best threshold chosen *on the test
data* (an optimistic upper bound for the baseline).

Usage::

    python scripts/bench_clustering.py          # writes results/clustering.{json,md}
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from occam.graph import louvain_clusters, single_linkage_clusters  # noqa: E402
from occam.knowledge import AttackData  # noqa: E402
from occam.metrics import ari, nmi, purity  # noqa: E402

DATA = REPO.parent.parent / "datasets" / "occam"


def build_events(data: AttackData, min_items: int, min_events: int) -> tuple[dict, dict]:
    by_ref: dict[tuple[str, str], set[str]] = defaultdict(set)
    for u in data.uses:
        if u.source in data.groups:
            for r in u.references:
                by_ref[(u.source, r)].add(u.target)
    events, truth = {}, {}
    for (g, r), items in sorted(by_ref.items()):
        if len(items) >= min_items:
            eid = f"{g}|{r}"
            events[eid] = {"capability": sorted(items)}
            truth[eid] = g
    for cid, g in sorted(data.attributed_to.items()):
        items = data.usage(cid)
        if len(items) >= min_items:
            events[cid] = {"capability": sorted(items)}
            truth[cid] = g
    counts = Counter(truth.values())
    keep = {e for e, g in truth.items() if counts[g] >= min_events}
    return {e: events[e] for e in events if e in keep}, {e: truth[e] for e in truth if e in keep}


def score(truth: dict[str, str], labels: dict[str, int]) -> dict[str, float]:
    ids = sorted(truth)
    t, p = [truth[i] for i in ids], [labels[i] for i in ids]
    return {"purity": purity(t, p), "nmi": nmi(t, p), "ari": ari(t, p), "clusters": len(set(p))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--min-items", type=int, default=4)
    ap.add_argument("--min-events", type=int, default=4)
    ap.add_argument("--out", type=Path, default=REPO / "results")
    a = ap.parse_args(argv)
    t0 = time.time()
    data = AttackData.load(a.data / "enterprise-attack-19.2.json")
    events, truth = build_events(data, a.min_items, a.min_events)
    print(f"{len(events)} events from {len(set(truth.values()))} groups")

    # Hyper-parameters are tuned on DEV groups (even ATT&CK G-number) and
    # reported on disjoint TEST groups (odd G-number): no test label is seen.
    def split(parity: int) -> tuple[dict, dict]:
        keep = {e for e, g in truth.items() if int(g.lstrip("G")) % 2 == parity}
        return {e: events[e] for e in keep}, {e: truth[e] for e in keep}

    (dev_ev, dev_tr), (test_ev, test_tr) = split(0), split(1)
    lv_grid = [(k, r) for k in (3, 5, 10) for r in (1.0, 2.0, 3.0, 5.0, 8.0)]
    sl_grid = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    lv_dev = {p: score(dev_tr, louvain_clusters(dev_ev, resolution=p[1], knn=p[0]))["ari"] for p in lv_grid}
    sl_dev = {t: score(dev_tr, single_linkage_clusters(dev_ev, t))["ari"] for t in sl_grid}
    best_lv, best_sl = max(lv_dev, key=lv_dev.get), max(sl_dev, key=sl_dev.get)
    print(f"dev-selected: louvain knn={best_lv[0]} resolution={best_lv[1]}; single-linkage t={best_sl}")

    rows = {
        f"Louvain, IDF-weighted Jaccard kNN graph (k={best_lv[0]}, res={best_lv[1]}; dev-tuned)":
            score(test_tr, louvain_clusters(test_ev, resolution=best_lv[1], knn=best_lv[0])),
        "Louvain, dense graph (no kNN, res=1.0)": score(test_tr, louvain_clusters(test_ev, knn=None)),
        f"Single-linkage Jaccard (t={best_sl}; dev-tuned)": score(test_tr, single_linkage_clusters(test_ev, best_sl)),
        "Single-linkage Jaccard (default t=0.3)": score(test_tr, single_linkage_clusters(test_ev, 0.3)),
        "Trivial: one cluster per event": score(test_tr, {e: i for i, e in enumerate(sorted(test_ev))}),
    }

    out = {"attack_version": data.version, "events": len(events), "groups": len(set(truth.values())),
           "test_events": len(test_ev), "test_groups": len(set(test_tr.values())),
           "dev_events": len(dev_ev), "dev_groups": len(set(dev_tr.values())),
           "selected": {"louvain_knn": best_lv[0], "louvain_resolution": best_lv[1], "single_linkage_t": best_sl},
           "min_items": a.min_items, "min_events": a.min_events, "results": rows,
           "runtime_s": round(time.time() - t0, 1)}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "clustering.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = [f"### Campaign clustering on ATT&CK activity (test split: {out['test_events']} events from "
          f"{out['test_groups']} groups; capability-only)", "",
          f"Hyper-parameters chosen on {out['dev_events']} dev events from {out['dev_groups']} disjoint groups.", "",
          "| Method | Purity | NMI | ARI | #clusters |", "|---|---|---|---|---|"]
    for k, v in rows.items():
        md.append(f"| {k} | {v['purity']:.3f} | {v['nmi']:.3f} | {v['ari']:.3f} | {v['clusters']} |")
    text = "\n".join(md) + "\n"
    (a.out / "clustering.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
