#!/usr/bin/env python
"""False-flag robustness benchmark: what does ACH actually add?

Runs on the same 274 leave-one-report-out ATT&CK incidents as
``bench_attribution.py`` (see :mod:`occam.evaluation`) in five settings:

* ``closed`` / ``open``      -- true group present / absent;
* ``false_flag``             -- 3 spoofable markers frame a random other group;
* ``authentic``              -- the same markers point at the TRUE group (control:
                                how often is a genuine overlap called a frame-up?);
* ``mimicry``                -- the adversary copies 3 of the framed group's rarest
                                techniques/software as ordinary hard evidence.

Methods:

* the marker-trusting TTP-similarity baseline and a sweep of its marker boost
  (0 = ignores spoofable evidence), a plain IDF-coverage baseline;
* two *marker-aware* baselines derived from the boost-0 similarity run:
  ``abstain`` (decline when the best hard-evidence cosine < tau) and
  ``gate`` ("framed" when the marker target is not in the hard-evidence top-k,
  otherwise trust the markers); tau and k are cross-fitted over a 2-fold
  split by group (each fold's value is tuned on the other fold);
* OCCAM ACH and one-at-a-time ablations of each mechanism.

All intervals are group-cluster bootstrap 95% CIs (incidents of one group are
resampled together); paired differences use the same resamples.

Usage::

    python scripts/bench_falseflag.py            # ~40 min, writes results/falseflag.{json,md}
    python scripts/bench_falseflag.py --limit 30 # smoke run
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from functools import partial
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from occam.attribution import ACHAttributor, IDFCoverageAttributor, SimilarityAttributor  # noqa: E402
from occam.calibration import GradeCalibrator  # noqa: E402
from occam.evaluation import ALL_SETTINGS, _fold, crossfit_calibrate, evaluate, incidents  # noqa: E402
from occam.knowledge import AttackData  # noqa: E402
from occam.metrics import brier  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))

FACTORIES = {
    "similarity": SimilarityAttributor,
    "sim-boost-0.05": partial(SimilarityAttributor, marker_boost=0.05),
    "sim-boost-0.3": partial(SimilarityAttributor, marker_boost=0.3),
    "sim-boost-0": partial(SimilarityAttributor, marker_boost=0.0),
    "coverage": IDFCoverageAttributor,
    "ach": ACHAttributor,
    "ach-no-ff": partial(ACHAttributor, false_flag_hypotheses=False),
    "ach-no-unknown": partial(ACHAttributor, unknown_hypothesis=False),
    "ach-no-discount": partial(ACHAttributor, spoofable_discount=1.0),
    "ach-no-caps": partial(ACHAttributor, confidence_caps=False),
    "ach-no-diag": partial(ACHAttributor, diagnosticity=False),
    "ach-none": partial(ACHAttributor, false_flag_hypotheses=False, spoofable_discount=1.0, confidence_caps=False),
    "ach-balanced": partial(ACHAttributor, ranking_rule="balanced"),
}
NAMES = {
    "similarity": "TTP-similarity, marker boost 0.15 (shipped baseline)",
    "sim-boost-0.05": "TTP-similarity, marker boost 0.05",
    "sim-boost-0.3": "TTP-similarity, marker boost 0.3",
    "sim-boost-0": "TTP-similarity, ignores spoofable rows",
    "coverage": "IDF coverage, ignores spoofable rows",
    "abstain": "Similarity + decline if cosine < tau (tau cross-fitted)",
    "gate": "Similarity + consistency gate (k cross-fitted)",
    "ach": "OCCAM ACH (full)",
    "ach-no-ff": "ACH without false-flag hypotheses",
    "ach-no-unknown": "ACH without unknown-actor hypothesis",
    "ach-no-discount": "ACH without spoofable x0.5 discount",
    "ach-no-caps": "ACH without confidence caps",
    "ach-no-diag": "ACH without diagnosticity weighting",
    "ach-none": "ACH without FF hypotheses, discount and caps",
    "ach-balanced": "ACH, support-aware ranking",
}
METRICS = ("accuracy", "named_true", "framed", "detected", "declined")
TAUS = [round(0.10 + 0.02 * i, 2) for i in range(21)]
KS = [1, 2, 3, 5, 8, 10, 15, 20, 30, 40, 60]


def rec(o, leading=..., flagged=..., prob=None) -> dict:
    """Flatten an Outcome (optionally with a post-hoc decision) to a record."""
    a = o.attribution
    lead = a.leading if leading is ... else leading
    flag = a.flagged if flagged is ... else flagged
    s, g, t = o.setting, o.incident.group, o.marker_target
    detected = flag is not None and flag == t
    if s == "open":
        ok = lead is None
    elif s == "authentic":
        ok = lead == g
    else:
        ok = lead == g or (s in ("false_flag", "mimicry") and detected)
    return {"group": g, "setting": s, "accuracy": float(ok), "named_true": float(lead == g),
            "framed": float(s in ("false_flag", "mimicry") and lead is not None and lead == t),
            "detected": float(detected), "declined": float(lead is None and flag is None),
            "prob": a.probability if prob is None else prob, "grade": a.confidence}


def abstain(o, tau: float) -> dict:
    a = o.attribution
    return rec(o, leading=None if a.hard_score < tau else a.ranked_actors[0], flagged=None)


def gate(o, k: int) -> dict:
    a = o.attribution
    t = o.marker_target if o.setting in ("false_flag", "authentic") else None  # mimicry has no visible markers
    if t is None:
        return rec(o, leading=a.ranked_actors[0], flagged=None)
    if t in a.ranked_actors[:k]:
        return rec(o, leading=t, flagged=None)
    return rec(o, leading=a.ranked_actors[0], flagged=t)


def mean(rs: list[dict], k: str) -> float:
    return sum(r[k] for r in rs) / len(rs) if rs else 0.0


def crossfit(base: dict[str, list], fn, grid, objective) -> tuple[dict[str, list[dict]], dict[int, object]]:
    """Choose a parameter on one group fold, apply it on the other."""
    chosen = {}
    for f in (0, 1):
        def score(v, f=f):
            return objective({s: [fn(o, v) for o in oc if _fold(o.incident.group) != f] for s, oc in base.items()})
        chosen[f] = max(grid, key=score)
    out = {s: [fn(o, chosen[_fold(o.incident.group)]) for o in oc] for s, oc in base.items()}
    return out, chosen


def cluster_boot(recs_by_method: dict[str, list[dict]], key: str, n: int = 1000, seed: int = 0) -> dict[str, tuple[float, float]]:
    """Group-cluster bootstrap CI of the mean of ``key`` for every method (same resamples)."""
    groups = sorted({r["group"] for rs in recs_by_method.values() for r in rs})
    rng = random.Random(seed)
    idx = {m: {} for m in recs_by_method}
    for m, rs in recs_by_method.items():
        for r in rs:
            idx[m].setdefault(r["group"], []).append(r[key])
    draws = {m: [] for m in recs_by_method}
    for _ in range(n):
        sample = [groups[rng.randrange(len(groups))] for _ in groups]
        for m in recs_by_method:
            vals = [v for g in sample for v in idx[m].get(g, ())]
            draws[m].append(sum(vals) / len(vals) if vals else 0.0)
    return {m: (sorted(d)[int(0.025 * n)], sorted(d)[int(0.975 * n) - 1]) for m, d in draws.items()}, draws


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--markers", type=int, default=3)
    ap.add_argument("--sweep", default="1,6", help="extra marker counts for false_flag/authentic/mimicry ('' to skip)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=REPO / "results")
    a = ap.parse_args(argv)
    t0 = time.time()
    data = AttackData.load(a.data / "enterprise-attack-19.2.json")
    incs = incidents(data, min_items=4, max_per_group=3)

    def progress(i: int, n: int) -> None:
        if i % 25 == 0 or i == n:
            print(f"  {i}/{n} incidents ({time.time() - t0:.0f}s)", flush=True)

    res = evaluate(data, FACTORIES, settings=ALL_SETTINGS, n_markers=a.markers, seed=a.seed, limit=a.limit,
                   incs=incs, progress=progress)
    recs: dict[str, dict[str, list[dict]]] = {m: {s: [rec(o) for o in oc] for s, oc in per.items()} for m, per in res.items()}
    base = res["sim-boost-0"]
    recs["abstain"], tau = crossfit(base, abstain, TAUS,
                                    lambda r: (mean(r["closed"], "accuracy") + mean(r["open"], "accuracy")) / 2)
    recs["gate"], kk = crossfit(base, gate, KS,
                                lambda r: (mean(r["false_flag"], "accuracy") + mean(r["authentic"], "accuracy")) / 2)

    # calibration: pooled over closed/open/false_flag, cross-fitted by group (setting-agnostic)
    pooled_brier = {}
    for m, per in res.items():
        pool = [o for s in ("closed", "open", "false_flag") for o in per[s]]
        if m.startswith("ach"):
            cal = {}
            for f in (0, 1):
                tr = [o for o in pool if _fold(o.incident.group) != f]
                cal[f] = GradeCalibrator().fit([o.attribution.confidence for o in tr], [o.correct for o in tr])
            p = [cal[_fold(o.incident.group)][o.attribution.confidence] for o in pool]
        else:
            p = crossfit_calibrate(pool)
        y = [o.correct for o in pool]
        pooled_brier[m] = {"pooled": brier(p, y)}
        for s in ("closed", "open", "false_flag"):
            sel = [i for i, o in enumerate(pool) if o.setting == s]
            pooled_brier[m][s] = brier([p[i] for i in sel], [y[i] for i in sel])

    out: dict = {"attack_version": data.version, "n_incidents": len(res["ach"]["closed"]),
                 "n_groups": len({o.incident.group for o in res["ach"]["closed"]}), "markers": a.markers,
                 "seed": a.seed, "tau": tau, "k": kk, "summary": {}, "ci95": {}, "paired_vs_ach": {},
                 "brier_pooled_calibration": pooled_brier, "brier_raw": {}}
    for s in ALL_SETTINGS:
        by_m = {m: recs[m][s] for m in recs}
        out["summary"][s] = {m: {k: mean(rs, k) for k in METRICS} for m, rs in by_m.items()}
        out["ci95"][s], out["paired_vs_ach"][s] = {}, {}
        for k in ("accuracy", "framed", "named_true", "detected"):
            ci, draws = cluster_boot(by_m, k)
            out["ci95"][s][k] = ci
            for m in by_m:
                d = sorted(x - y for x, y in zip(draws["ach"], draws[m]))
                out["paired_vs_ach"][s].setdefault(m, {})[k] = (d[25], d[974])
        out["brier_raw"][s] = {m: brier([r["prob"] for r in recs[m][s]], [r["accuracy"] for r in recs[m][s]])
                               for m in FACTORIES}

    sweep = {}
    for nm in [int(x) for x in a.sweep.split(",") if x.strip()]:
        sub = {m: FACTORIES[m] for m in ("similarity", "sim-boost-0", "coverage", "ach", "ach-no-ff")}
        r2 = evaluate(data, sub, settings=("false_flag", "authentic", "mimicry"), n_markers=nm, seed=a.seed,
                      limit=a.limit, incs=incs)
        rr = {m: {s: [rec(o) for o in oc] for s, oc in per.items()} for m, per in r2.items()}
        rr["gate"] = {s: [gate(o, kk[_fold(o.incident.group)]) for o in oc] for s, oc in r2["sim-boost-0"].items()}
        sweep[nm] = {s: {m: {k: mean(rr[m][s], k) for k in METRICS} for m in rr} for s in ("false_flag", "authentic", "mimicry")}
        print(f"  sweep n_markers={nm} done ({time.time() - t0:.0f}s)", flush=True)
    out["marker_sweep"] = sweep
    out["runtime_s"] = round(time.time() - t0, 1)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "falseflag.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = render(out)
    (a.out / "falseflag.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def _ci(o, s, m, k):
    lo, hi = o["ci95"][s][k][m]
    return f"{o['summary'][s][m][k]:.3f} [{lo:.2f}-{hi:.2f}]"


def render(o: dict) -> str:
    L = [f"### False-flag robustness: baselines, controls and ablations (ATT&CK v{o['attack_version']})", "",
         f"{o['n_incidents']} held-out incidents from {o['n_groups']} groups, {o['markers']} markers per incident. "
         "Brackets: group-cluster bootstrap 95% CI. "
         f"Cross-fitted parameters: tau = {o['tau']}, k = {o['k']} (per group fold).", ""]
    main_m = ["similarity", "sim-boost-0.05", "sim-boost-0", "coverage", "abstain", "gate", "ach"]
    L += ["#### Planted markers (false_flag) vs authentic markers (control) vs TTP mimicry", "",
          "| Method | False flag: correct | False flag: names framed | Authentic: names true | Authentic: calls it a frame "
          "| Mimicry: correct | Mimicry: names framed |", "|---|---|---|---|---|---|---|"]
    for m in main_m:
        L.append(f"| {NAMES[m]} | {_ci(o, 'false_flag', m, 'accuracy')} | {_ci(o, 'false_flag', m, 'framed')} | "
                 f"{_ci(o, 'authentic', m, 'named_true')} | {_ci(o, 'authentic', m, 'detected')} | "
                 f"{_ci(o, 'mimicry', m, 'accuracy')} | {_ci(o, 'mimicry', m, 'framed')} |")
    L += ["", "#### Closed and open world (abstention)", "",
          "| Method | Closed: correct | Closed: declines | Open: correct decline | Brier, pooled calibration |",
          "|---|---|---|---|---|"]
    for m in main_m:
        pb = o["brier_pooled_calibration"].get(m, {}).get("pooled")
        L.append(f"| {NAMES[m]} | {_ci(o, 'closed', m, 'accuracy')} | {o['summary']['closed'][m]['declined']:.3f} | "
                 f"{_ci(o, 'open', m, 'accuracy')} | {'' if pb is None else f'{pb:.3f}'} |")
    L += ["", "#### Ablations of ACH (each row removes one mechanism)", "",
          "| Variant | Closed correct | Open correct | False flag correct | names framed | names true "
          "| Authentic: names true | Authentic: calls frame | Mimicry: names framed |", "|---|---|---|---|---|---|---|---|---|"]
    for m in [x for x in o["summary"]["closed"] if x.startswith("ach")]:
        S = o["summary"]
        L.append(f"| {NAMES[m]} | {S['closed'][m]['accuracy']:.3f} | {S['open'][m]['accuracy']:.3f} | "
                 f"{S['false_flag'][m]['accuracy']:.3f} | {S['false_flag'][m]['framed']:.3f} | {S['false_flag'][m]['named_true']:.3f} | "
                 f"{S['authentic'][m]['named_true']:.3f} | {S['authentic'][m]['detected']:.3f} | {S['mimicry'][m]['framed']:.3f} |")
    L += ["", "#### Paired difference ACH minus method, 95% cluster-bootstrap interval", "",
          "| Method | False flag: names framed | Authentic: names true | Mimicry: names framed | Closed: correct |",
          "|---|---|---|---|---|"]
    P = o["paired_vs_ach"]
    for m in main_m[:-1]:
        def d(s, k, m=m):
            lo, hi = P[s][m][k]
            return f"[{lo:+.2f}, {hi:+.2f}]"
        L.append(f"| {NAMES[m]} | {d('false_flag', 'framed')} | {d('authentic', 'named_true')} | {d('mimicry', 'framed')} | "
                 f"{d('closed', 'accuracy')} |")
    if o.get("marker_sweep"):
        L += ["", "#### Number of planted / mimicked items", "",
              "| n | Method | False flag: names framed | Authentic: names true | Authentic: calls frame | Mimicry: names framed |",
              "|---|---|---|---|---|---|"]
        for n, per in o["marker_sweep"].items():
            for m in per["false_flag"]:
                L.append(f"| {n} | {NAMES[m]} | {per['false_flag'][m]['framed']:.3f} | {per['authentic'][m]['named_true']:.3f} | "
                         f"{per['authentic'][m]['detected']:.3f} | {per['mimicry'][m]['framed']:.3f} |")
    L += ["", "*Correct*: closed/authentic = names the true group; open = declines; false_flag/mimicry = names the true "
          "group or concludes the framed group was framed. *Calls it a frame* under authentic markers is a false alarm. "
          "Mimicry items are ordinary technique/software rows, so the gate cannot see them (it equals plain similarity there). "
          "*Brier, pooled calibration*: one grade/probability map fitted on closed+open+false_flag together and "
          "cross-fitted by group, i.e. without knowing which setting an incident comes from."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
