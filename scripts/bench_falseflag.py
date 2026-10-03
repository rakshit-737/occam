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
* *marker-aware* baselines derived from the boost-0 similarity run:
  ``abstain`` (decline when the best hard-evidence cosine < tau) and
  ``gate`` ("framed" when the marker target is not in the hard-evidence top-k,
  otherwise trust the markers); tau and k are cross-fitted over a 2-fold
  split by group (each fold's value is tuned on the other fold). Two more
  abstention operating points are cross-fitted to *match* ACH: tau chosen so
  the baseline declines on untracked actors as often as ACH does, and so it is
  as accurate as ACH in the closed world (a like-for-like comparison on the
  abstention frontier);
* OCCAM ACH and one-at-a-time ablations of each mechanism.

Calibration: one setting-agnostic map (histogram binning of the stated
probability, or the learned grade map for ACH variants) fitted on
closed + open + false_flag together and cross-fitted by group. Its Brier score
gets a paired group-cluster bootstrap interval (ACH minus each method, same
resamples), pooled and per setting; *overconfident errors* are wrong answers
with calibrated probability >= 0.8.

All intervals are group-cluster bootstrap 95% CIs (incidents of one group are
resampled together); paired differences use the same resamples. A rate of
exactly 0 or 1 has a degenerate bootstrap interval; it is replaced by a Wilson
interval with the number of groups as the sample size (marked with a dagger).

Usage::

    python scripts/bench_falseflag.py            # ~2 min on a GitHub runner, ~13 min on a laptop; results/falseflag.{json,md}
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
sys.path.insert(0, str(REPO / "scripts"))

from _benchutil import degenerate_safe, provenance, source_line  # noqa: E402

from occam.attribution import ACHAttributor, IDFCoverageAttributor, SimilarityAttributor  # noqa: E402
from occam.calibration import GradeCalibrator  # noqa: E402
from occam.evaluation import ALL_SETTINGS, _fold, evaluate, incidents  # noqa: E402
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
    "ach-top5": partial(ACHAttributor, shortlist=5),
}
NAMES = {
    "similarity": "TTP-similarity, marker boost 0.15 (shipped baseline)",
    "sim-boost-0.05": "TTP-similarity, marker boost 0.05",
    "sim-boost-0.3": "TTP-similarity, marker boost 0.3",
    "sim-boost-0": "TTP-similarity, ignores spoofable rows",
    "coverage": "IDF coverage, ignores spoofable rows",
    "abstain": "Similarity + decline if cosine < tau (tau cross-fitted)",
    "abstain-decline": "Similarity + decline, tau matched to ACH's open-world decline rate",
    "abstain-closed": "Similarity + decline, tau matched to ACH's closed-world accuracy",
    "gate": "Similarity + consistency gate (k cross-fitted)",
    "ach": "OCCAM ACH (full)",
    "ach-no-ff": "ACH without false-flag hypotheses",
    "ach-no-unknown": "ACH without unknown-actor hypothesis",
    "ach-no-discount": "ACH without spoofable x0.5 discount",
    "ach-no-caps": "ACH without confidence caps",
    "ach-no-diag": "ACH without diagnosticity weighting",
    "ach-none": "ACH without FF hypotheses, discount and caps",
    "ach-balanced": "ACH, support-aware ranking",
    "ach-top5": "ACH, top-5 similarity shortlist",
}
METRICS = ("accuracy", "named_true", "framed", "detected", "declined")
TAUS = [round(0.10 + 0.02 * i, 2) for i in range(21)]
FINE_TAUS = [round(0.005 * i, 3) for i in range(161)]  # 0 .. 0.8, for the frontier and matched operating points
KS = [1, 2, 3, 5, 8, 10, 15, 20, 30, 40, 60]
POOL = ("closed", "open", "false_flag")
MAIN = ["similarity", "sim-boost-0.05", "sim-boost-0.3", "sim-boost-0", "coverage", "abstain", "abstain-decline",
        "abstain-closed", "gate", "ach"]
N_BOOT = 1000


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


def crossfit_match(base: dict[str, list], target: dict[str, list[dict]], setting: str, key: str,
                   grid=FINE_TAUS) -> tuple[dict[str, list[dict]], dict[int, float]]:
    """Abstention threshold whose ``key`` rate in ``setting`` matches the target
    method's on the *other* group fold, applied to this fold (cross-fitted)."""
    chosen = {}
    for f in (0, 1):
        goal = mean([r for r in target[setting] if _fold(r["group"]) != f], key)
        tr = [o for o in base[setting] if _fold(o.incident.group) != f]
        chosen[f] = min(grid, key=lambda t: (abs(mean([abstain(o, t) for o in tr], key) - goal), t))
    out = {s: [abstain(o, chosen[_fold(o.incident.group)]) for o in oc] for s, oc in base.items()}
    return out, chosen


def cluster_boot(recs_by_method: dict[str, list[dict]], key: str, n: int = N_BOOT, seed: int = 0):
    """Group-cluster bootstrap of the mean of ``key`` for every method (the same
    resamples for all methods, so differences are paired)."""
    groups = sorted({r["group"] for rs in recs_by_method.values() for r in rs})
    gi = {g: i for i, g in enumerate(groups)}
    sums = {m: [0.0] * len(groups) for m in recs_by_method}
    cnts = {m: [0] * len(groups) for m in recs_by_method}
    for m, rs in recs_by_method.items():
        for r in rs:
            sums[m][gi[r["group"]]] += r[key]
            cnts[m][gi[r["group"]]] += 1
    rng = random.Random(seed)
    draws = {m: [] for m in recs_by_method}
    for _ in range(n):
        sample = [rng.randrange(len(groups)) for _ in groups]
        for m in recs_by_method:
            c = sum(cnts[m][i] for i in sample)
            draws[m].append(sum(sums[m][i] for i in sample) / c if c else 0.0)
    ci = {m: (sorted(d)[int(0.025 * n)], sorted(d)[int(0.975 * n) - 1]) for m, d in draws.items()}
    return ci, draws


def paired(draws: dict[str, list[float]], a: str, b: str, n: int = N_BOOT) -> tuple[float, float]:
    """95% interval of mean(a) - mean(b) over the shared resamples."""
    d = sorted(x - y for x, y in zip(draws[a], draws[b]))
    return d[int(0.025 * n)], d[int(0.975 * n) - 1]


def hist_crossfit(pool: list[dict], bins: int = 10, prior: float = 1.0) -> list[float]:
    """Histogram-binning recalibration of ``prob``, 2-fold cross-fitted by group
    (the same map as :func:`occam.evaluation.crossfit_calibrate`, on records)."""
    def b(p: float) -> int:
        return min(int(p * bins), bins - 1)

    stats = {f: [[0.0, 0.0] for _ in range(bins)] for f in (0, 1)}
    for r in pool:
        s = stats[_fold(r["group"])][b(r["prob"])]
        s[0] += r["accuracy"]
        s[1] += 1
    base = {f: (sum(x[0] for x in stats[f]) + prior) / (sum(x[1] for x in stats[f]) + 2 * prior) for f in (0, 1)}
    out = []
    for r in pool:
        other = 1 - _fold(r["group"])
        hit, n = stats[other][b(r["prob"])]
        out.append((hit + prior * base[other]) / (n + prior))
    return out


def grade_crossfit(pool: list[dict]) -> list[float]:
    """Learned grade -> probability map, 2-fold cross-fitted by group."""
    cal = {}
    for f in (0, 1):
        tr = [r for r in pool if _fold(r["group"]) != f]
        cal[f] = GradeCalibrator().fit([r["grade"] for r in tr], [bool(r["accuracy"]) for r in tr])
    return [cal[_fold(r["group"])][r["grade"]] for r in pool]


def pooled_records(recs: dict[str, dict[str, list[dict]]]) -> dict[str, list[dict]]:
    """Per method: closed + open + false_flag records with the setting-agnostic
    calibrated probability, its squared error and the overconfident-error flag."""
    out = {}
    for m, per in recs.items():
        pool = [r for s in POOL for r in per[s]]
        p = grade_crossfit(pool) if m.startswith("ach") else hist_crossfit(pool)
        out[m] = [{"group": r["group"], "setting": r["setting"], "p": pi, "sq": (pi - r["accuracy"]) ** 2,
                   "oc": float(not r["accuracy"] and pi >= 0.8)} for r, pi in zip(pool, p)]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--markers", type=int, default=3)
    ap.add_argument("--sweep", default="1,6", help="extra marker counts for false_flag/authentic/mimicry ('' to skip)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=REPO / "results")
    ap.add_argument("--figures", type=Path, default=REPO / "docs" / "figures")
    ap.add_argument("--render", action="store_true", help="only re-render the Markdown and figure from the existing JSON")
    a = ap.parse_args(argv)
    if a.render:
        o = json.loads((a.out / "falseflag.json").read_text(encoding="utf-8"))
        (a.out / "falseflag.md").write_text(render(o), encoding="utf-8")
        plot_frontier(o, a.figures)
        return 0
    t0 = time.time()
    attack = a.data / "enterprise-attack-19.2.json"
    prov = provenance([attack], argv)
    data = AttackData.load(attack)
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
    recs["abstain-decline"], tau_d = crossfit_match(base, recs["ach"], "open", "accuracy")
    recs["abstain-closed"], tau_c = crossfit_match(base, recs["ach"], "closed", "accuracy")

    # the abstention frontier (in-sample, for the figure): closed accuracy vs open decline as tau moves
    frontier = []
    for t in FINE_TAUS:
        frontier.append([t, mean([abstain(o, t) for o in base["closed"]], "accuracy"),
                         mean([abstain(o, t) for o in base["open"]], "accuracy")])

    n_groups = len({o.incident.group for o in res["ach"]["closed"]})
    out: dict = {"attack_version": data.version, "n_incidents": len(res["ach"]["closed"]), "n_groups": n_groups,
                 "markers": a.markers, "seed": a.seed, "n_boot": N_BOOT,
                 "tau": tau, "k": kk, "tau_matched_decline": tau_d, "tau_matched_closed": tau_c,
                 "summary": {}, "ci95": {}, "wilson_replaced": {}, "paired_vs_ach": {}, "brier_raw": {},
                 "overconfident_raw": {}}
    keys = ("accuracy", "framed", "named_true", "detected", "declined")
    for s in ALL_SETTINGS:
        by_m = {m: recs[m][s] for m in recs}
        out["summary"][s] = {m: {k: mean(rs, k) for k in METRICS} for m, rs in by_m.items()}
        out["ci95"][s], out["paired_vs_ach"][s], out["wilson_replaced"][s] = {}, {}, {}
        for k in keys:
            ci, draws = cluster_boot(by_m, k)
            out["ci95"][s][k] = {}
            for m in by_m:
                out["ci95"][s][k][m], repl = degenerate_safe(ci[m], out["summary"][s][m][k], n_groups)
                if repl:
                    out["wilson_replaced"][s].setdefault(k, []).append(m)
                out["paired_vs_ach"][s].setdefault(m, {})[k] = paired(draws, "ach", m)
        out["brier_raw"][s] = {m: brier([r["prob"] for r in recs[m][s]], [r["accuracy"] for r in recs[m][s]])
                               for m in FACTORIES}
        out["overconfident_raw"][s] = {m: sum(1 for r in recs[m][s] if not r["accuracy"] and r["prob"] >= 0.8)
                                       for m in FACTORIES}

    # setting-agnostic calibration: Brier and overconfident errors, with paired intervals
    pooled = pooled_records(recs)
    cal: dict = {"n": {m: len(v) for m, v in pooled.items()}, "brier": {}, "brier_ci95": {}, "brier_paired_vs_ach": {},
                 "overconfident": {}, "overconfident_count": {}, "overconfident_ci95": {}}
    for scope in ("pooled",) + POOL:
        sel = {m: [r for r in rs if scope == "pooled" or r["setting"] == scope] for m, rs in pooled.items()}
        ci, draws = cluster_boot(sel, "sq")
        oci, _ = cluster_boot(sel, "oc")
        for m, rs in sel.items():
            cal["brier"].setdefault(m, {})[scope] = mean(rs, "sq")
            cal["brier_ci95"].setdefault(m, {})[scope] = ci[m]
            cal["brier_paired_vs_ach"].setdefault(m, {})[scope] = paired(draws, "ach", m)
            rate = mean(rs, "oc")
            cal["overconfident"].setdefault(m, {})[scope] = rate
            cal["overconfident_count"].setdefault(m, {})[scope] = [int(sum(r["oc"] for r in rs)), len(rs)]
            cal["overconfident_ci95"].setdefault(m, {})[scope] = degenerate_safe(oci[m], rate, n_groups)[0]
    out["pooled_calibration"] = cal

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
    out["frontier"] = {"abstain_in_sample": frontier,
                       "points": {m: [out["summary"]["closed"][m]["accuracy"], out["summary"]["open"][m]["accuracy"]]
                                  for m in ("ach", "ach-top5", "ach-balanced", "abstain", "abstain-decline",
                                            "abstain-closed", "similarity")}}
    out["runtime_s"] = round(time.time() - t0, 1)
    out["provenance"] = prov
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "falseflag.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = render(out)
    (a.out / "falseflag.md").write_text(md, encoding="utf-8")
    print(md)
    plot_frontier(out, a.figures)
    return 0


def _pct(lo: float, hi: float, digits: int = 2) -> str:
    return f"[{lo:.{digits}f}-{hi:.{digits}f}]"


def _ci(o, s, m, k):
    lo, hi = o["ci95"][s][k][m]
    dag = "†" if m in o.get("wilson_replaced", {}).get(s, {}).get(k, []) else ""
    return f"{o['summary'][s][m][k]:.3f} {_pct(lo, hi)}{dag}"


def _d(lo: float, hi: float) -> str:
    return f"[{lo:+.3f}, {hi:+.3f}]"


def render(o: dict) -> str:
    C = o["pooled_calibration"]
    L = [f"### False-flag robustness: baselines, controls and ablations (ATT&CK v{o['attack_version']})", "",
         f"{o['n_incidents']} held-out incidents from {o['n_groups']} groups, {o['markers']} markers per incident. "
         f"Brackets: group-cluster bootstrap 95% CI ({o['n_boot']} resamples); † = the rate is exactly 0 or 1, so the "
         "bootstrap interval is degenerate and a Wilson interval with the number of groups as the sample size is shown. "
         f"Cross-fitted parameters (per group fold): tau = {o['tau']}, k = {o['k']}; tau matched to ACH's open-world "
         f"decline = {o['tau_matched_decline']}, to ACH's closed-world accuracy = {o['tau_matched_closed']}.", "",
         source_line(o.get("provenance")), ""]
    L += ["#### Planted markers (false_flag) vs authentic markers (control) vs TTP mimicry", "",
          "| Method | False flag: correct | False flag: names framed | Authentic: names true | Authentic: calls it a frame "
          "| Mimicry: correct | Mimicry: names framed |", "|---|---|---|---|---|---|---|"]
    for m in MAIN:
        L.append(f"| {NAMES[m]} | {_ci(o, 'false_flag', m, 'accuracy')} | {_ci(o, 'false_flag', m, 'framed')} | "
                 f"{_ci(o, 'authentic', m, 'named_true')} | {_ci(o, 'authentic', m, 'detected')} | "
                 f"{_ci(o, 'mimicry', m, 'accuracy')} | {_ci(o, 'mimicry', m, 'framed')} |")
    L += ["", "#### Closed and open world (abstention) and setting-agnostic calibration", "",
          "| Method | Closed: correct | Closed: declines | Open: correct decline | Brier, pooled map | "
          "Brier, ACH minus method (paired) | Overconfident errors, pooled map |", "|---|---|---|---|---|---|---|"]
    for m in MAIN:
        b, (lo, hi) = C["brier"][m]["pooled"], C["brier_ci95"][m]["pooled"]
        k, n = C["overconfident_count"][m]["pooled"]
        olo, ohi = C["overconfident_ci95"][m]["pooled"]
        diff = "" if m == "ach" else _d(*C["brier_paired_vs_ach"][m]["pooled"])
        L.append(f"| {NAMES[m]} | {_ci(o, 'closed', m, 'accuracy')} | {_ci(o, 'closed', m, 'declined')} | "
                 f"{_ci(o, 'open', m, 'accuracy')} | {b:.3f} {_pct(lo, hi)} | {diff} | {k}/{n} {_pct(olo, ohi, 3)} |")
    L += ["", "#### Brier score under the pooled map, per setting: ACH minus method (paired 95% CI)", "",
          "| Method | Closed | Open | False flag | All three pooled |", "|---|---|---|---|---|"]
    L.append("| OCCAM ACH (full), value | " + " | ".join(f"{C['brier']['ach'][s]:.3f}" for s in POOL + ("pooled",)) + " |")
    for m in [x for x in MAIN if x != "ach"]:
        vals = " / ".join(f"{C['brier'][m][s]:.3f}" for s in POOL + ("pooled",))
        L.append(f"| {NAMES[m]} ({vals}) | " + " | ".join(_d(*C["brier_paired_vs_ach"][m][s]) for s in POOL + ("pooled",)) + " |")
    L += ["", "#### Ablations of ACH (each row removes one mechanism)", "",
          "| Variant | Closed correct | Open correct | False flag correct | names framed | names true "
          "| Authentic: names true | Authentic: calls frame | Mimicry: correct | Mimicry: names framed "
          "| Brier, pooled map | Brier, variant minus full ACH (paired) | Overconfident errors, pooled map |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    S = o["summary"]
    for m in [x for x in S["closed"] if x.startswith("ach")]:
        lo, hi = C["brier_paired_vs_ach"][m]["pooled"]
        diff = "" if m == "ach" else _d(-hi, -lo)
        k, n = C["overconfident_count"][m]["pooled"]
        L.append(f"| {NAMES[m]} | {S['closed'][m]['accuracy']:.3f} | {S['open'][m]['accuracy']:.3f} | "
                 f"{S['false_flag'][m]['accuracy']:.3f} | {S['false_flag'][m]['framed']:.3f} | {S['false_flag'][m]['named_true']:.3f} | "
                 f"{S['authentic'][m]['named_true']:.3f} | {S['authentic'][m]['detected']:.3f} | "
                 f"{S['mimicry'][m]['accuracy']:.3f} | {S['mimicry'][m]['framed']:.3f} | "
                 f"{C['brier'][m]['pooled']:.3f} | {diff} | {k}/{n} |")
    L += ["", "#### Paired difference ACH minus method, 95% cluster-bootstrap interval", "",
          "| Method | Closed: correct | Open: correct decline | False flag: correct | False flag: names framed "
          "| Authentic: names true | Authentic: calls it a frame | Mimicry: correct | Mimicry: names framed |",
          "|---|---|---|---|---|---|---|---|---|"]
    P = o["paired_vs_ach"]
    cols = [("closed", "accuracy"), ("open", "accuracy"), ("false_flag", "accuracy"), ("false_flag", "framed"),
            ("authentic", "named_true"), ("authentic", "detected"), ("mimicry", "accuracy"), ("mimicry", "framed")]
    for m in [x for x in MAIN if x != "ach"]:
        L.append(f"| {NAMES[m]} | " + " | ".join(_d(*P[s][m][k]) for s, k in cols) + " |")
    if o.get("marker_sweep"):
        L += ["", "#### Number of planted / mimicked items", "",
              "| n | Method | False flag: names framed | Authentic: names true | Authentic: calls frame | Mimicry: names framed |",
              "|---|---|---|---|---|---|"]
        for n, per in o["marker_sweep"].items():
            for m in per["false_flag"]:
                L.append(f"| {n} | {NAMES[m]} | {per['false_flag'][m]['framed']:.3f} | {per['authentic'][m]['named_true']:.3f} | "
                         f"{per['authentic'][m]['detected']:.3f} | {per['mimicry'][m]['framed']:.3f} |")
    raw = o["overconfident_raw"]
    ff_sim, ff_ach = raw["false_flag"]["similarity"], raw["false_flag"]["ach"]
    b03 = C["brier"]["sim-boost-0.3"]
    per_sim = " / ".join(f"{C['brier']['similarity'][s]:.3f}" for s in POOL)
    per_ach = " / ".join(f"{C['brier']['ach'][s]:.3f}" for s in POOL)
    L += ["", "*Correct*: closed/authentic = names the true group; open = declines; false_flag/mimicry = names the true "
          "group or concludes the framed group was framed. *Calls it a frame* under authentic markers is a false alarm. "
          "Mimicry items are ordinary technique/software rows, so the gate cannot see them (it equals plain similarity there). "
          "*Pooled map*: one probability map (histogram binning; the learned grade map for ACH variants) fitted on "
          "closed + open + false_flag together and cross-fitted by group, i.e. without knowing which setting an incident "
          "comes from; Brier and overconfident errors (wrong with calibrated probability >= 0.8) are over all three "
          f"settings ({C['n']['ach']} answers). Per setting it gives similarity {per_sim} and ACH {per_ach} "
          "(closed / open / false_flag), the same map as the "
          "pooled table in `results/attribution.md`. The pooled number depends on the equal 1:1:1 mix of settings. "
          f"Raw (uncalibrated) overconfident errors under planted markers: similarity {ff_sim}/{o['n_incidents']}, "
          f"ACH {ff_ach}/{o['n_incidents']}. Brier rewards a matcher that is always framed but states low probabilities: "
          f"marker boost 0.3 is framed {o['summary']['false_flag']['sim-boost-0.3']['framed']:.3f} of the time under planted "
          f"markers, yet has the lowest pooled Brier ({b03['pooled']:.3f}; false flag {b03['false_flag']:.3f}), so Brier "
          "alone does not measure resistance to framing."]
    return "\n".join(L) + "\n"


def plot_frontier(o: dict, fig_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: skipping figures")
        return
    fig_dir.mkdir(parents=True, exist_ok=True)
    fr = o["frontier"]
    xs = [p[2] for p in fr["abstain_in_sample"]]
    ys = [p[1] for p in fr["abstain_in_sample"]]
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.plot(xs, ys, c="#c2412d", lw=1.6, label="Similarity + decline below cosine tau (all tau, in-sample)")
    style = {"ach": ("#2b59c3", "o", "OCCAM ACH"), "ach-top5": ("#1f7a3a", "s", "ACH, top-5 shortlist"),
             "ach-balanced": ("#8a4fbf", "D", "ACH, support-aware ranking"),
             "abstain": ("#c2412d", "^", "Abstain, tau cross-fitted"),
             "abstain-decline": ("#c2412d", "v", "Abstain, tau matched to ACH's decline"),
             "abstain-closed": ("#c2412d", "P", "Abstain, tau matched to ACH's accuracy"),
             "similarity": ("#555555", "x", "Similarity (never declines)")}
    for m, (c, mk, lab) in style.items():
        cl, op = fr["points"][m]
        ax.scatter([op], [cl], c=c, marker=mk, s=46, zorder=3, label=lab)
    ax.set_xlabel("correct decline when the true group is untracked (open world)")
    ax.set_ylabel("top-1 accuracy when it is tracked (closed world)")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(0, 0.6)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, loc="lower left", frameon=False)
    ax.set_title(f"Abstention trade-off, {o['n_incidents']} held-out ATT&CK incidents", fontsize=10)
    fig.tight_layout()
    fig.savefig(fig_dir / "abstention_frontier.png", dpi=110)
    plt.close(fig)
    print(f"wrote {fig_dir / 'abstention_frontier.png'}")


if __name__ == "__main__":
    sys.exit(main())
