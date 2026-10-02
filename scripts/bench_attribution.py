#!/usr/bin/env python
"""Attribution benchmark on held-out MITRE ATT&CK group usage.

Leave-one-report-out: every (group, cited report) pair with >= 4 techniques /
software becomes an incident; items supported only by that report are removed
from the group's profile before attributing it (see :mod:`occam.evaluation`).
Compares OCCAM's ACH engine with a naive IDF-cosine TTP-similarity baseline in
closed-world, open-world and false-flag settings, with calibration metrics.

Usage::

    python scripts/bench_attribution.py          # writes results/attribution.{json,md} + docs/figures/*.png
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
from functools import partial
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from occam.attribution import ACHAttributor, SimilarityAttributor  # noqa: E402
from occam.calibration import GradeCalibrator  # noqa: E402
from occam.evaluation import SETTINGS, crossfit_calibrate, crossfit_grade_calibrate, evaluate, summarize  # noqa: E402
from occam.knowledge import AttackData  # noqa: E402
from occam.metrics import reliability  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))
NAMES = {"similarity": "TTP-similarity baseline", "ach": "OCCAM ACH", "ach-top5": "OCCAM ACH, top-5 similarity shortlist",
         "ach-balanced": "OCCAM ACH, support-aware ranking"}


def bootstrap_ci(values: list[float], n: int = 1000, seed: int = 0, groups: list[str] | None = None) -> tuple[float, float]:
    """95% percentile bootstrap of the mean; with ``groups``, a cluster bootstrap
    (all incidents of a resampled group enter together)."""
    rng = random.Random(seed)
    k = len(values)
    if not k:
        return (0.0, 0.0)
    if groups is None:
        means = sorted(sum(values[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    else:
        by: dict[str, list[float]] = {}
        for g, v in zip(groups, values):
            by.setdefault(g, []).append(v)
        keys = sorted(by)
        means = []
        for _ in range(n):
            xs = [v for g in (keys[rng.randrange(len(keys))] for _ in keys) for v in by[g]]
            means.append(sum(xs) / len(xs))
        means.sort()
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--min-items", type=int, default=4)
    ap.add_argument("--max-per-group", type=int, default=3)
    ap.add_argument("--markers", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--extra-seeds", default="11,13,17,19",
                    help="further false-flag framing seeds for the seed-variance table ('' to skip)")
    ap.add_argument("--limit", type=int, default=None, help="subsample incidents (quick runs)")
    ap.add_argument("--out", type=Path, default=REPO / "results")
    ap.add_argument("--figures", type=Path, default=REPO / "docs" / "figures")
    a = ap.parse_args(argv)

    t0 = time.time()
    data = AttackData.load(a.data / "enterprise-attack-19.2.json")
    print(json.dumps(data.summary()))
    factories = {"similarity": SimilarityAttributor, "ach": ACHAttributor, "ach-top5": partial(ACHAttributor, shortlist=5),
                 "ach-balanced": partial(ACHAttributor, ranking_rule="balanced")}

    def progress(i: int, n: int) -> None:
        if i % 25 == 0 or i == n:
            print(f"  {i}/{n} incidents ({time.time() - t0:.0f}s)", flush=True)

    res = evaluate(data, factories, min_items=a.min_items, max_per_group=a.max_per_group,
                   n_markers=a.markers, seed=a.seed, limit=a.limit, progress=progress)
    out: dict = {
        "attack_version": data.version,
        "protocol": {"min_items": a.min_items, "max_per_group": a.max_per_group, "markers": a.markers, "seed": a.seed},
        "n_incidents": len(res["ach"]["closed"]),
        "n_groups_with_incidents": len({o.incident.group for o in res["ach"]["closed"]}),
        "n_candidate_groups": len(data.actor_profiles()),
        "raw": {}, "calibrated": {}, "grade_calibrated": {}, "ci95": {}, "reliability": {},
    }
    for m, per in res.items():
        out["raw"][m], out["calibrated"][m], out["ci95"][m], out["reliability"][m] = {}, {}, {}, {}
        for s in SETTINGS:
            oc = per[s]
            out["raw"][m][s] = summarize(oc)
            cal = crossfit_calibrate(oc)
            out["calibrated"][m][s] = summarize(oc, cal)
            if m != "similarity":
                out["grade_calibrated"].setdefault(m, {})[s] = summarize(oc, crossfit_grade_calibrate(oc))
            grp = [o.incident.group for o in oc]
            out["ci95"][m][s] = {
                "accuracy": bootstrap_ci([float(o.correct) for o in oc], groups=grp),
                "brier": bootstrap_ci([(o.attribution.probability - o.correct) ** 2 for o in oc], groups=grp),
            }
            out["reliability"][m][s] = reliability([o.attribution.probability for o in oc], [o.correct for o in oc])
    # setting-agnostic (pooled) calibration, cross-fitted by group: what a deployed
    # map can actually do, since it cannot know which setting an incident is in
    out["pooled_calibrated"] = {}
    for m, per in res.items():
        pool = [o for s in SETTINGS for o in per[s]]
        if m == "similarity":
            p_all = crossfit_calibrate(pool)
        else:
            from occam.evaluation import _fold
            cals = {}
            for f in (0, 1):
                tr = [o for o in pool if _fold(o.incident.group) != f]
                cals[f] = GradeCalibrator().fit([o.attribution.confidence for o in tr], [o.correct for o in tr])
            p_all = [cals[_fold(o.incident.group)][o.attribution.confidence] for o in pool]
        out["pooled_calibrated"][m] = {}
        for s in SETTINGS:
            idx = [i for i, o in enumerate(pool) if o.setting == s]
            out["pooled_calibrated"][m][s] = summarize([pool[i] for i in idx], [p_all[i] for i in idx])
    # the shipped calibrated grader: fitted on every setting of plain ACH
    pooled = [o for s in SETTINGS for o in res["ach"][s]]
    grader = GradeCalibrator().fit([o.attribution.confidence for o in pooled], [o.correct for o in pooled])
    out["grade_calibrator"] = grader.to_dict()
    a.out.mkdir(parents=True, exist_ok=True)
    grader.save(a.out / "grade_calibration.json")
    seeds = [a.seed] + [int(x) for x in a.extra_seeds.split(",") if x.strip()]
    out["seed_variance"] = seed_variance(data, factories, a, seeds, res)
    out["runtime_s"] = round(time.time() - t0, 1)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "attribution.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = render(out)
    (a.out / "attribution.md").write_text(md, encoding="utf-8")
    print(md)
    plot(res, a.figures)
    return 0


def seed_variance(data, factories, a, seeds: list[int], first) -> dict:
    """False-flag results across framing seeds (closed/open do not depend on the seed)."""
    per: dict[str, dict[str, list[float]]] = {m: {"accuracy": [], "framed_rate": [], "brier": []} for m in factories}
    for i, sd in enumerate(seeds):
        res = first if i == 0 else evaluate(data, factories, settings=("false_flag",), min_items=a.min_items,
                                            max_per_group=a.max_per_group, n_markers=a.markers, seed=sd, limit=a.limit)
        for m in factories:
            r = summarize(res[m]["false_flag"])
            for k in per[m]:
                per[m][k].append(r[k])
        print(f"  seed {sd} done", flush=True)
    return {"seeds": seeds, "false_flag": {m: {k: {"mean": statistics.fmean(v), "sd": statistics.stdev(v), "values": v}
                                               for k, v in d.items()} for m, d in per.items()}}


def render(o: dict) -> str:
    L = [
        f"### Attribution on held-out ATT&CK group usage (ATT&CK v{o['attack_version']})",
        "",
        f"{o['n_incidents']} leave-one-report-out incidents from {o['n_groups_with_incidents']} groups; "
        f"{o['n_candidate_groups']} candidate group profiles; {o['protocol']['markers']} planted markers in the false-flag setting. "
        "95% CIs: group-cluster bootstrap.",
        "",
        "| Setting | Method | Correct [95% CI] | Names true group | Framed | Brier [95% CI] | ECE "
        "| Overconfident errors | Brier (recal.) | ECE (recal.) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in SETTINGS:
        for m in o["raw"]:
            r, c, ci = o["raw"][m][s], o["calibrated"][m][s], o["ci95"][m][s]
            L.append(
                f"| {s} | {NAMES[m]} | {r['accuracy']:.3f} [{ci['accuracy'][0]:.2f}-{ci['accuracy'][1]:.2f}] | "
                f"{r['named_true']:.3f} | {r['framed_rate']:.3f} | {r['brier']:.3f} [{ci['brier'][0]:.2f}-{ci['brier'][1]:.2f}] | "
                f"{r['ece']:.3f} | {r['overconfident_errors']:.3f} | {c['brier']:.3f} | {c['ece']:.3f} |"
            )
    L += ["", "*Correct*: closed = names the true group; open = declines to name (true group absent); "
          "false_flag = names the true group or concludes the framed group was framed. "
          "*Overconfident errors*: wrong with stated probability >= 0.8. "
          "*recal.*: histogram binning cross-fitted over a 2-fold group split."]
    L += ["", "#### Setting-agnostic calibration (the realistic number)", "",
          "One map fitted on closed + open + false_flag together, cross-fitted by group. The per-setting maps further below "
          "know which setting an incident comes from and are an oracle upper bound. "
          "Canonical pooled-calibration table; `results/falseflag.md` quotes the same map as one number over all three "
          "settings. A single map cannot help the similarity baseline: it never declines, so all its open-world answers "
          "are wrong and the map pulls every probability down. The closed-world Brier therefore rises from 0.179 (raw) to"
          " 0.315, while the open-world Brier falls to 0.032.", "",
          "| Setting | Method | Brier (pooled map) | ECE (pooled map) |", "|---|---|---|---|"]
    for s in SETTINGS:
        for m in o["pooled_calibrated"]:
            r = o["pooled_calibrated"][m][s]
            L.append(f"| {s} | {NAMES[m]} | {r['brier']:.3f} | {r['ece']:.3f} |")
    L += ["", "#### Learned grade -> probability map, fitted per setting (oracle upper bound)", "",
          "Stated probability per ACH grade, learned (Beta-smoothed, monotone) instead of fixed ICD-203 midpoints. "
          "Brier with the learned map is cross-fitted over a 2-fold group split.", "",
          "| Setting | Method | Brier (ICD-203 midpoints) | Brier (learned grades) | ECE (learned grades) |", "|---|---|---|---|---|"]
    for s in SETTINGS:
        for m, per in o["grade_calibrated"].items():
            L.append(f"| {s} | {NAMES[m]} | {o['raw'][m][s]['brier']:.3f} | {per[s]['brier']:.3f} | {per[s]['ece']:.3f} |")
    g = o["grade_calibrator"]
    L += ["", "Shipped map (fit on all settings of plain ACH, `results/grade_calibration.json`): "
          + ", ".join(f"{k} = {g['probs'][k]:.3f} (n={g['counts'][k][1]})" for k in ("low", "moderate", "high"))]
    sv = o["seed_variance"]
    L += ["", f"#### False-flag setting across framing seeds {sv['seeds']}", "",
          "| Method | Correct, mean ± sample SD | Names framed group, mean ± sample SD | Brier, mean ± sample SD |", "|---|---|---|---|"]
    for m, d in sv["false_flag"].items():
        L.append(f"| {NAMES[m]} | {d['accuracy']['mean']:.3f} ± {d['accuracy']['sd']:.3f} | "
                 f"{d['framed_rate']['mean']:.3f} ± {d['framed_rate']['sd']:.3f} | {d['brier']['mean']:.3f} ± {d['brier']['sd']:.3f} |")
    return "\n".join(L) + "\n"


def plot(res, fig_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: skipping figures")
        return
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    colors = {"similarity": "#c2412d", "ach": "#2b59c3", "ach-top5": "#1f7a3a", "ach-balanced": "#8a4fbf"}
    for ax, s in zip(axes, SETTINGS):
        ax.plot([0, 1], [0, 1], ls="--", c="#999", lw=1)
        for m in res:
            oc = res[m][s]
            pts = reliability([o.attribution.probability for o in oc], [o.correct for o in oc])
            if pts:
                xs, ys, ns = zip(*pts)
                ax.plot(xs, ys, marker="o", c=colors[m], label=NAMES[m])
                for x, y, n in pts:
                    ax.annotate(str(n), (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points", color=colors[m])
        ax.set_title(f"{s} world" if s != "false_flag" else "false-flag")
        ax.set_xlabel("stated probability")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("observed accuracy")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, frameon=False)
    fig.suptitle("Reliability of stated attribution confidence (held-out ATT&CK incidents)")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(fig_dir / "attribution_reliability.png", dpi=110)
    print(f"wrote {fig_dir / 'attribution_reliability.png'}")


if __name__ == "__main__":
    sys.exit(main())
