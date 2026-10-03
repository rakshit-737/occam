#!/usr/bin/env python
"""Sensitivity of ACH to its hand-set cell-rule thresholds.

ACH rates a technique as non-diagnostic when at least ``common_frac`` of all
ATT&CK groups use it, and as strongly diagnostic (CC on a match) when at most
``rare_max`` groups use it. The shipped values (30%, 3 groups) were set by
hand. This script reruns plain ACH on the 274 leave-one-report-out incidents
of ``bench_falseflag.py`` (same incidents, framing seed and markers) over a
grid of both thresholds, and asks two questions:

* how much do the headline rates move across the grid (in-sample table)?
* if the thresholds were *chosen* on one half of the groups (by the mean
  accuracy over the five settings) and applied to the other half, would the
  result differ from the hand-set values (cross-fitted row)?

Intervals: group-cluster bootstrap 95% CI.

Usage::

    python scripts/bench_sensitivity.py            # ~1 min on a GitHub runner; results/sensitivity.{json,md}
    python scripts/bench_sensitivity.py --limit 20 # smoke run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from _benchutil import provenance, source_line  # noqa: E402
from bench_falseflag import cluster_boot, mean, paired, rec  # noqa: E402

from occam.attribution import ACHAttributor  # noqa: E402
from occam.evaluation import ALL_SETTINGS, HoldoutWorld, _fold, evaluate, incidents  # noqa: E402
from occam.knowledge import AttackData  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))
COMMON = (0.2, 0.3, 0.4)
RARE = (2, 3, 5)
SHIPPED = "c0.3-r3"
COLS = [("closed", "accuracy", "Closed correct"), ("open", "accuracy", "Open correct decline"),
        ("false_flag", "accuracy", "False flag correct"), ("false_flag", "framed", "False flag names framed"),
        ("authentic", "detected", "Authentic: calls it a frame"), ("mimicry", "accuracy", "Mimicry correct"),
        ("mimicry", "framed", "Mimicry names framed")]


def objective(per: dict[str, list[dict]], fold_out: int) -> float:
    """Mean accuracy over the five settings on the groups NOT in ``fold_out``."""
    return sum(mean([r for r in per[s] if _fold(r["group"]) != fold_out], "accuracy") for s in ALL_SETTINGS) / len(ALL_SETTINGS)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--markers", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=REPO / "results")
    a = ap.parse_args(argv)
    t0 = time.time()
    attack = a.data / "enterprise-attack-19.2.json"
    prov = provenance([attack], argv)
    data = AttackData.load(attack)
    incs = incidents(data, min_items=4, max_per_group=3)
    recs: dict[str, dict[str, list[dict]]] = {}
    for c in COMMON:
        for r in RARE:
            hw = HoldoutWorld.build(data)
            hw.base_kb = data.to_kb(common_frac=c, rare_max=r)
            res = evaluate(data, {"ach": ACHAttributor}, settings=ALL_SETTINGS, n_markers=a.markers, seed=a.seed,
                           limit=a.limit, incs=incs, hw=hw)
            recs[f"c{c}-r{r}"] = {s: [rec(o) for o in oc] for s, oc in res["ach"].items()}
            print(f"  common_frac={c} rare_max={r} done ({time.time() - t0:.0f}s)", flush=True)
    # cross-fitted choice: each fold uses the configuration that is best on the other fold
    chosen = {f: max(recs, key=lambda k, f=f: objective(recs[k], f)) for f in (0, 1)}
    recs["crossfit"] = {s: [r for f in (0, 1) for r in recs[chosen[f]][s] if _fold(r["group"]) == f]
                        for s in ALL_SETTINGS}
    out: dict = {"attack_version": data.version, "n_incidents": len(recs[SHIPPED]["closed"]),
                 "n_groups": len({r["group"] for r in recs[SHIPPED]["closed"]}), "markers": a.markers, "seed": a.seed,
                 "grid": {"common_frac": list(COMMON), "rare_max": list(RARE)}, "shipped": SHIPPED,
                 "crossfit_chosen": chosen, "summary": {}, "ci95": {}, "paired_vs_shipped": {}}
    for s in ALL_SETTINGS:
        by_m = {m: recs[m][s] for m in recs}
        out["summary"][s] = {m: {k: mean(rs, k) for k in ("accuracy", "framed", "named_true", "detected")}
                             for m, rs in by_m.items()}
        out["ci95"][s], out["paired_vs_shipped"][s] = {}, {}
        for k in ("accuracy", "framed", "detected"):
            ci, draws = cluster_boot(by_m, k)
            out["ci95"][s][k] = ci
            out["paired_vs_shipped"][s][k] = {m: paired(draws, m, SHIPPED) for m in by_m}
    out["runtime_s"] = round(time.time() - t0, 1)
    out["provenance"] = prov
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "sensitivity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = render(out)
    (a.out / "sensitivity.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def render(o: dict) -> str:
    S = o["summary"]
    L = [f"### Sensitivity of ACH to its cell-rule thresholds (ATT&CK v{o['attack_version']})", "",
         f"{o['n_incidents']} held-out incidents from {o['n_groups']} groups, {o['markers']} markers. `cX-rY`: a technique "
         "used by at least X of all groups is non-diagnostic, one used by at most Y groups is rare (CC on a match). "
         f"Shipped: `{o['shipped']}` (hand-set). *Cross-fitted*: each group fold uses the configuration with the best mean "
         f"accuracy over the five settings on the other fold (chosen: {o['crossfit_chosen']}).", "",
         source_line(o.get("provenance")), "",
         "| Thresholds | " + " | ".join(c[2] for c in COLS) + " |", "|---" * (len(COLS) + 1) + "|"]
    for m in S["closed"]:
        label = {"crossfit": "cross-fitted choice", o["shipped"]: f"{o['shipped']} (shipped)"}.get(m, m)
        L.append(f"| {label} | " + " | ".join(f"{S[s][m][k]:.3f}" for s, k, _ in COLS) + " |")
    P = o["paired_vs_shipped"]
    L += ["", "Paired difference, configuration minus shipped (95% cluster-bootstrap interval):", "",
          "| Thresholds | " + " | ".join(c[2] for c in COLS) + " |", "|---" * (len(COLS) + 1) + "|"]
    for m in S["closed"]:
        if m == o["shipped"]:
            continue
        label = "cross-fitted choice" if m == "crossfit" else m
        L.append(f"| {label} | " + " | ".join(f"[{P[s][k][m][0]:+.3f}, {P[s][k][m][1]:+.3f}]" for s, k, _ in COLS) + " |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
