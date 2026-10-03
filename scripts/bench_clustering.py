#!/usr/bin/env python
"""Campaign-clustering benchmark on real ATT&CK activity.

Events are (a) per-report slices of ATT&CK group usage -- the techniques and
software one public report attributes to one group -- and (b) ATT&CK campaign
objects (C00xx) that have an ``attributed-to`` group. Ground truth is the
group. Only groups with >= ``--min-events`` events are kept so every true
cluster has several members. ATT&CK carries no infrastructure, so this is a
capability-only (TTP + software) clustering test -- the hardest case.

Methods: Louvain community detection on an IDF-weighted Jaccard event graph
(``occam.graph``), with and without the kNN sparsification, vs the
single-linkage union-find baseline. Every method's hyper-parameters are
chosen on DEV groups and reported on disjoint TEST groups. Louvain depends on
node order, so the selected configuration is also re-run on 10 random
permutations of the test events (mean, SD, range of ARI).

Intervals: the clustering of the test events is held fixed and each test
group is left out in turn (group jackknife); the 95% interval is the estimate
+- 1.96 jackknife standard errors. This measures how much the score depends on
which groups happen to be in the test set, not how the clustering itself would
change; the input-order spread covers the latter. The kNN-minus-dense ARI
difference is jackknifed the same way (paired).

Usage::

    python scripts/bench_clustering.py          # writes results/clustering.{json,md}
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from _benchutil import provenance, source_line  # noqa: E402

from occam.graph import louvain_clusters, single_linkage_clusters  # noqa: E402
from occam.knowledge import AttackData  # noqa: E402
from occam.metrics import ari, nmi, purity  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))


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


def jackknife_scores(truth: dict[str, str], labels: dict[str, dict[str, int]]):
    """Leave-one-test-group-out jackknife of each method's scores with its
    clustering held fixed: 95% interval = estimate +- 1.96 jackknife SE.
    (A with-replacement bootstrap is biased for pair-counting scores such as
    ARI, because a resampled event pairs with its own copy.)"""
    groups = sorted(set(truth.values()))
    ids = sorted(truth)
    G = len(groups)
    reps: dict[str, dict[str, list[float]]] = {m: {"ari": [], "nmi": [], "purity": []} for m in labels}
    for g in groups:
        keep = [e for e in ids if truth[e] != g]
        t = [truth[e] for e in keep]
        for m, lab in labels.items():
            p = [lab[e] for e in keep]
            reps[m]["ari"].append(ari(t, p))
            reps[m]["nmi"].append(nmi(t, p))
            reps[m]["purity"].append(purity(t, p))

    def se(v: list[float]) -> float:
        mu = sum(v) / len(v)
        return math.sqrt((G - 1) / G * sum((x - mu) ** 2 for x in v))

    t_all = [truth[e] for e in ids]
    full = {m: {"ari": ari(t_all, [lab[e] for e in ids]), "nmi": nmi(t_all, [lab[e] for e in ids]),
                "purity": purity(t_all, [lab[e] for e in ids])} for m, lab in labels.items()}
    ci = {m: {k: (full[m][k] - 1.96 * se(v), full[m][k] + 1.96 * se(v)) for k, v in d.items()} for m, d in reps.items()}
    return ci, reps, full


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--min-items", type=int, default=4)
    ap.add_argument("--min-events", type=int, default=4)
    ap.add_argument("--out", type=Path, default=REPO / "results")
    a = ap.parse_args(argv)
    t0 = time.time()
    attack = a.data / "enterprise-attack-19.2.json"
    prov = provenance([attack], argv)
    data = AttackData.load(attack)
    events, truth = build_events(data, a.min_items, a.min_events)
    print(f"{len(events)} events from {len(set(truth.values()))} groups")

    # Hyper-parameters are tuned on DEV groups (even ATT&CK G-number) and
    # reported on disjoint TEST groups (odd G-number): no test label is seen.
    def split(parity: int) -> tuple[dict, dict]:
        # list, not set: dict (= graph node) order must not depend on PYTHONHASHSEED
        keep = [e for e, g in truth.items() if int(g.lstrip("G")) % 2 == parity]
        return {e: events[e] for e in keep}, {e: truth[e] for e in keep}

    (dev_ev, dev_tr), (test_ev, test_tr) = split(0), split(1)
    lv_grid = [(k, r) for k in (3, 5, 10) for r in (1.0, 2.0, 3.0, 5.0, 8.0)]
    dense_grid = [1.0, 2.0, 3.0, 5.0, 8.0]
    sl_grid = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    lv_dev = {p: score(dev_tr, louvain_clusters(dev_ev, resolution=p[1], knn=p[0]))["ari"] for p in lv_grid}
    sl_dev = {t: score(dev_tr, single_linkage_clusters(dev_ev, t))["ari"] for t in sl_grid}
    dense_dev = {r: score(dev_tr, louvain_clusters(dev_ev, resolution=r, knn=None))["ari"] for r in dense_grid}
    best_lv, best_sl = max(lv_dev, key=lv_dev.get), max(sl_dev, key=sl_dev.get)
    best_dense = max(dense_dev, key=dense_dev.get)
    print(f"dev ARI: best kNN {lv_dev[best_lv]:.3f}, best dense {dense_dev[best_dense]:.3f} (res={best_dense})")
    print(f"dev-selected: louvain knn={best_lv[0]} resolution={best_lv[1]}; single-linkage t={best_sl}")

    knn_name = f"Louvain, IDF-weighted Jaccard kNN graph (k={best_lv[0]}, res={best_lv[1]}; dev-tuned)"
    dense_name = f"Louvain, dense graph (no kNN, res={best_dense}; dev-tuned)"
    labels = {
        knn_name: louvain_clusters(test_ev, resolution=best_lv[1], knn=best_lv[0]),
        dense_name: louvain_clusters(test_ev, resolution=best_dense, knn=None),
        "Louvain, dense graph (no kNN, default res=1.0)": louvain_clusters(test_ev, knn=None),
        f"Single-linkage Jaccard (t={best_sl}; dev-tuned{' = default' if best_sl == 0.3 else ''})":
            single_linkage_clusters(test_ev, best_sl),
        "Trivial: one cluster per event": {e: i for i, e in enumerate(sorted(test_ev))},
    }
    if best_sl != 0.3:
        labels["Single-linkage Jaccard (default t=0.3)"] = single_linkage_clusters(test_ev, 0.3)
    rows = {k: score(test_tr, lab) for k, lab in labels.items()}
    ci95, reps, full = jackknife_scores(test_tr, labels)
    for k in rows:
        rows[k]["ci95"] = ci95[k]
    diff = [x - y for x, y in zip(reps[knn_name]["ari"], reps[dense_name]["ari"])]
    G, mu = len(diff), sum(diff) / len(diff)
    se_d = math.sqrt((G - 1) / G * sum((x - mu) ** 2 for x in diff))
    est = full[knn_name]["ari"] - full[dense_name]["ari"]
    paired_knn_minus_dense = (est - 1.96 * se_d, est + 1.96 * se_d)
    perm = []
    for sd in range(10):
        keys = list(test_ev)
        random.Random(sd).shuffle(keys)
        perm.append(score(test_tr, louvain_clusters({k: test_ev[k] for k in keys}, resolution=best_lv[1], knn=best_lv[0]))["ari"])
    order_spread = {"seeds": 10, "mean": statistics.fmean(perm), "sd": statistics.stdev(perm), "min": min(perm), "max": max(perm)}

    out = {"attack_version": data.version, "events": len(events), "groups": len(set(truth.values())),
           "test_events": len(test_ev), "test_groups": len(set(test_tr.values())),
           "dev_events": len(dev_ev), "dev_groups": len(set(dev_tr.values())),
           "selected": {"louvain_knn": best_lv[0], "louvain_resolution": best_lv[1], "single_linkage_t": best_sl},
           "min_items": a.min_items, "min_events": a.min_events, "results": rows,
           "dev_ari": {"knn_best": lv_dev[best_lv], "dense_best": dense_dev[best_dense]}, "kNN_order_spread": order_spread,
           "ari_paired_knn_minus_dense": paired_knn_minus_dense, "runtime_s": round(time.time() - t0, 1),
           "provenance": prov}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "clustering.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    text = render(out)
    (a.out / "clustering.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


def render(out: dict) -> str:
    md = [f"### Campaign clustering on ATT&CK activity (test split: {out['test_events']} events from "
          f"{out['test_groups']} groups; capability-only)", "",
          f"Hyper-parameters chosen on {out['dev_events']} dev events from {out['dev_groups']} disjoint groups "
          f"(dev ARI: kNN {out['dev_ari']['knn_best']:.3f}, dense {out['dev_ari']['dense_best']:.3f}). Brackets: 95% "
          "leave-one-group-out jackknife interval with each clustering held fixed (sampling variation of the test set "
          "only; estimate +- 1.96 SE).", "",
          source_line(out.get("provenance")), "",
          "| Method | Purity [95% CI] | NMI [95% CI] | ARI [95% CI] | #clusters |", "|---|---|---|---|---|"]
    for k, v in out["results"].items():
        c = v["ci95"]
        md.append(f"| {k} | {v['purity']:.3f} [{c['purity'][0]:.2f}-{c['purity'][1]:.2f}] | "
                  f"{v['nmi']:.3f} [{c['nmi'][0]:.2f}-{c['nmi'][1]:.2f}] | {v['ari']:.3f} [{c['ari'][0]:.2f}-{c['ari'][1]:.2f}] | "
                  f"{v['clusters']} |")
    sp, pd = out["kNN_order_spread"], out["ari_paired_knn_minus_dense"]
    md += ["", f"ARI, kNN minus dense graph (paired jackknife, 95%): [{pd[0]:+.3f}, {pd[1]:+.3f}]. Louvain depends on "
           f"input order: the selected kNN configuration on {sp['seeds']} random permutations of the test events gives "
           f"ARI {sp['mean']:.3f} ± {sp['sd']:.3f} (sample SD; range {sp['min']:.3f}-{sp['max']:.3f})."]
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    sys.exit(main())
