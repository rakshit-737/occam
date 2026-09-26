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
import random
import sys
import time
from functools import partial
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from occam.attribution import ACHAttributor, SimilarityAttributor  # noqa: E402
from occam.evaluation import SETTINGS, crossfit_calibrate, evaluate, summarize  # noqa: E402
from occam.knowledge import AttackData  # noqa: E402
from occam.metrics import reliability  # noqa: E402

DATA = REPO.parent.parent / "datasets" / "occam"
NAMES = {"similarity": "TTP-similarity baseline", "ach": "OCCAM ACH", "ach-top5": "OCCAM ACH, top-5 similarity shortlist"}


def bootstrap_ci(values: list[float], n: int = 1000, seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    k = len(values)
    if not k:
        return (0.0, 0.0)
    means = sorted(sum(values[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--min-items", type=int, default=4)
    ap.add_argument("--max-per-group", type=int, default=3)
    ap.add_argument("--markers", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--limit", type=int, default=None, help="subsample incidents (quick runs)")
    ap.add_argument("--out", type=Path, default=REPO / "results")
    ap.add_argument("--figures", type=Path, default=REPO / "docs" / "figures")
    a = ap.parse_args(argv)

    t0 = time.time()
    data = AttackData.load(a.data / "enterprise-attack-19.2.json")
    print(json.dumps(data.summary()))
    factories = {"similarity": SimilarityAttributor, "ach": ACHAttributor, "ach-top5": partial(ACHAttributor, shortlist=5)}

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
        "raw": {}, "calibrated": {}, "ci95": {}, "reliability": {},
    }
    for m, per in res.items():
        out["raw"][m], out["calibrated"][m], out["ci95"][m], out["reliability"][m] = {}, {}, {}, {}
        for s in SETTINGS:
            oc = per[s]
            out["raw"][m][s] = summarize(oc)
            cal = crossfit_calibrate(oc)
            out["calibrated"][m][s] = summarize(oc, cal)
            out["ci95"][m][s] = {
                "accuracy": bootstrap_ci([float(o.correct) for o in oc]),
                "brier": bootstrap_ci([(o.attribution.probability - o.correct) ** 2 for o in oc]),
            }
            out["reliability"][m][s] = reliability([o.attribution.probability for o in oc], [o.correct for o in oc])
    out["runtime_s"] = round(time.time() - t0, 1)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "attribution.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = render(out)
    (a.out / "attribution.md").write_text(md, encoding="utf-8")
    print(md)
    plot(res, a.figures)
    return 0


def render(o: dict) -> str:
    L = [
        f"### Attribution on held-out ATT&CK group usage (ATT&CK v{o['attack_version']})",
        "",
        f"{o['n_incidents']} leave-one-report-out incidents from {o['n_groups_with_incidents']} groups; "
        f"{o['n_candidate_groups']} candidate group profiles; {o['protocol']['markers']} planted markers in the false-flag setting.",
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
    colors = {"similarity": "#c2412d", "ach": "#2b59c3", "ach-top5": "#1f7a3a"}
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
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Reliability of stated attribution confidence (held-out ATT&CK incidents)")
    fig.tight_layout()
    fig.savefig(fig_dir / "attribution_reliability.png", dpi=110)
    print(f"wrote {fig_dir / 'attribution_reliability.png'}")


if __name__ == "__main__":
    sys.exit(main())
