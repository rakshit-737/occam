#!/usr/bin/env python
"""Harder / larger attribution evaluations (v1.1).

Protocols (all against ATT&CK Enterprise; see docs/evaluation.md):

* ``loro-all``   -- leave-one-report-out over *every* (group, report) pair
  with >= 4 items (no per-group cap), i.e. all groups ATT&CK documents.
* ``campaigns``  -- every ATT&CK *campaign* attributed to a group, held out
  with all of its references (:func:`occam.evaluation.campaign_incidents`).
* ``unattributed`` -- every campaign ATT&CK does *not* attribute: the only
  correct answer is to decline (open world, no planted true group).
* ``temporal-12.1`` / ``temporal-15.1`` -- profiles from an older ATT&CK
  release, incidents that only appear in v19.2 (campaigns and group/report
  pairs added later). Nothing is held out: the past simply lacks them.

Each protocol runs closed / open / false-flag (unattributed: open only), with
the false-flag setting repeated over 5 framing seeds (mean +- sample SD).
Intervals: group-cluster bootstrap (incidents of one group resampled
together) when n >= 50, Wilson score interval otherwise.

Temporal protocols map item ids the old release does not know: through
``revoked-by`` relationships of the new release, then sub-technique ->
parent; anything still unknown is dropped (an unknown id would otherwise be
rated inconsistent with every actor and push ACH towards "unknown"). The
share of remapped / dropped items is reported. ``unattributed-clean`` drops
unattributed campaigns whose own ATT&CK description names a tracked group.

Usage::

    python scripts/bench_attribution_extended.py            # results/attribution_extended.{json,md}
    python scripts/bench_attribution_extended.py --only campaigns temporal-15.1
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
import sys
import time
from functools import partial
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from _benchutil import degenerate_safe, provenance, source_line, wilson  # noqa: E402
from bench_attribution import NAMES  # noqa: E402

from occam.attribution import ACHAttributor, SimilarityAttributor  # noqa: E402
from occam.evaluation import (  # noqa: E402
    SETTINGS,
    HoldoutWorld,
    Incident,
    StaticWorld,
    campaign_incidents,
    evaluate,
    incidents,
    summarize,
    temporal_incidents,
)
from occam.knowledge import AttackData  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))
PROTOCOLS = ["loro-all", "campaigns", "unattributed", "unattributed-clean", "temporal-12.1", "temporal-15.1"]
DESCR = {
    "loro-all": "Leave-one-report-out, every (group, report) pair, no per-group cap",
    "campaigns": "ATT&CK campaigns attributed to a group, held out with all their references",
    "unattributed": "ATT&CK campaigns with no attributed group (correct = decline)",
    "unattributed-clean": "As unattributed, minus campaigns whose ATT&CK description names a tracked group",
    "temporal-12.1": "Profiles from ATT&CK v12.1 (released Nov 2022); incidents added to ATT&CK after it (in v19.2)",
    "temporal-15.1": "Profiles from ATT&CK v15.1 (released May 2024); incidents added to ATT&CK after it (in v19.2)",
}


def factories() -> dict:
    return {"similarity": SimilarityAttributor, "ach": ACHAttributor, "ach-top5": partial(ACHAttributor, shortlist=5),
            "ach-balanced": partial(ACHAttributor, ranking_rule="balanced")}


def interval(oc, key=lambda o: float(o.correct), n_boot: int = 1000, seed: int = 0) -> tuple[tuple[float, float], bool]:
    """Wilson interval for small n, group-cluster bootstrap otherwise. A rate of
    exactly 0 or 1 makes the bootstrap degenerate; it is then replaced by a
    Wilson interval with the number of groups as the sample size (second item
    of the result: whether that happened)."""
    vals = [key(o) for o in oc]
    n = len(vals)
    if not n:
        return (0.0, 0.0), False
    groups = sorted({o.incident.group for o in oc})
    if n < 50 or len(groups) < 10:
        return wilson(sum(vals), n), False
    by: dict[str, list[float]] = {}
    for o, v in zip(oc, vals):
        by.setdefault(o.incident.group, []).append(v)
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        xs = [v for g in (groups[rng.randrange(len(groups))] for _ in groups) for v in by[g]]
        means.append(sum(xs) / len(xs))
    means.sort()
    return degenerate_safe((means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]), sum(vals) / n, len(groups))


def remap(incs: list[Incident], old: AttackData, new_bundle: dict) -> tuple[list[Incident], dict]:
    """Map ids unknown to ``old`` (revoked-by, then parent technique); drop the rest."""
    known = set(old.techniques) | set(old.software)
    ext = {}
    for o in new_bundle["objects"]:
        for r in o.get("external_references", []):
            if r.get("source_name") == "mitre-attack" and r.get("external_id"):
                ext[o["id"]] = r["external_id"]
    newer_to_older: dict[str, str] = {}
    for o in new_bundle["objects"]:
        if o.get("type") == "relationship" and o.get("relationship_type") == "revoked-by":
            a, b = ext.get(o["source_ref"]), ext.get(o["target_ref"])
            if a and b and a in known:
                newer_to_older.setdefault(b, a)
    stats = {"items": 0, "known": 0, "revoked_map": 0, "parent_map": 0, "dropped": 0, "incidents_with_unknown": 0}
    out = []
    for i in incs:
        items, had = set(), False
        for x in i.items:
            stats["items"] += 1
            if x in known:
                stats["known"] += 1
                items.add(x)
            elif x in newer_to_older:
                stats["revoked_map"] += 1
                items.add(newer_to_older[x])
                had = True
            elif "." in x and x.split(".")[0] in known:
                stats["parent_map"] += 1
                items.add(x.split(".")[0])
                had = True
            else:
                stats["dropped"] += 1
                had = True
        stats["incidents_with_unknown"] += had
        if len(items) >= 4:
            out.append(Incident(i.group, i.reference, sorted(items), i.refs, i.kind))
    stats["kept_incidents"] = len(out)
    return out, stats


def names_tracked_group(desc: str, data: AttackData) -> list[str]:
    hits = []
    for g in data.groups.values():
        for n in {g.name, *g.aliases}:
            if len(n) >= 4 and re.search(r"\b" + re.escape(n) + r"\b", desc):
                hits.append(g.id)
                break
    return hits


def build(protocol: str, new: AttackData, data_dir: Path):
    """(incidents, world, settings) for one protocol."""
    if protocol == "loro-all":
        return incidents(new, max_per_group=None), HoldoutWorld.build(new), SETTINGS, {}
    if protocol == "campaigns":
        return campaign_incidents(new), HoldoutWorld.build(new), SETTINGS, {}
    if protocol.startswith("unattributed"):
        camp_items: dict[str, set[str]] = {}
        for u in new.uses:
            if u.source in new.campaigns:
                camp_items.setdefault(u.source, set()).add(u.target)
        incs = [Incident(f"C:{cid}", cid, sorted(items), kind="campaign") for cid, items in sorted(camp_items.items())
                if cid not in new.attributed_to and len(items) >= 4]
        named = {i.reference: names_tracked_group(new.campaigns[i.reference].description, new) for i in incs}
        if protocol == "unattributed-clean":
            incs = [i for i in incs if not named[i.reference]]
        extra = {"campaigns_naming_a_tracked_group": {k: v for k, v in named.items() if v}}
        return incs, StaticWorld.build(new), ("open",), extra
    if protocol.startswith("temporal-"):
        v = protocol.split("-", 1)[1]
        old = AttackData.load(data_dir / "attack-history" / f"enterprise-attack-{v}.json")
        raw = temporal_incidents(old, new, max_per_group=None)
        bundle = json.loads((data_dir / "enterprise-attack-19.2.json").read_text(encoding="utf-8"))
        incs, stats = remap(raw, old, bundle)
        stats["raw_incidents"] = len(raw)
        return incs, StaticWorld.build(old), SETTINGS, {"id_mapping": stats}
    raise ValueError(protocol)


def run_protocol(protocol: str, new: AttackData, a) -> dict:
    t0 = time.time()
    incs, world, settings, extra = build(protocol, new, a.data)
    n_groups = len({i.group for i in incs if not i.group.startswith("C:")})
    print(f"[{protocol}] {len(incs)} incidents, {n_groups} groups", flush=True)
    facs = factories()
    res = evaluate(new, facs, settings=settings, n_markers=a.markers, seed=a.seeds[0], incs=incs, hw=world)
    out: dict = {"description": DESCR[protocol], "n_incidents": len(incs),
                 "n_groups": n_groups, **extra,
                 "n_campaign_incidents": sum(i.kind == "campaign" for i in incs),
                 "n_candidates": len(world.base_profiles), "settings": {}}
    for s in settings:
        out["settings"][s] = {}
        for m in facs:
            oc = res[m][s]
            r = summarize(oc)
            r["ci95_accuracy"], r["ci95_accuracy_wilson"] = interval(oc)
            r["ci95_framed"], r["ci95_framed_wilson"] = interval(oc, key=lambda o: float(o.framed))
            out["settings"][s][m] = r
    if "false_flag" in settings and len(a.seeds) > 1:
        per = {m: {"accuracy": [], "framed_rate": [], "named_true": []} for m in facs}
        for i, sd in enumerate(a.seeds):
            rr = res if i == 0 else evaluate(new, facs, settings=("false_flag",), n_markers=a.markers, seed=sd,
                                            incs=incs, hw=world)
            for m in facs:
                r = summarize(rr[m]["false_flag"])
                for k in per[m]:
                    per[m][k].append(r[k])
        out["false_flag_seeds"] = {"seeds": a.seeds, "methods": {
            m: {k: {"mean": statistics.fmean(v), "sd": statistics.stdev(v)} for k, v in d.items()}
            for m, d in per.items()}}
    out["runtime_s"] = round(time.time() - t0, 1)
    print(f"[{protocol}] done in {out['runtime_s']}s", flush=True)
    return out


def render(o: dict) -> str:
    L = [f"### Extended attribution evaluation (profiles/incidents from ATT&CK, current release v{o['attack_version']})", "",
         source_line(o.get("provenance")), ""]
    L += ["| Protocol | Incidents | Groups | Candidate profiles |", "|---|---|---|---|"]
    for p, r in o["protocols"].items():
        L.append(f"| `{p}`: {r['description']} | {r['n_incidents']} ({r['n_campaign_incidents']} campaigns) | "
                 f"{r['n_groups']} | {r['n_candidates']} |")
    for p, r in o["protocols"].items():
        if "id_mapping" in r:
            st = r["id_mapping"]
            L.append(f"\n`{p}` id mapping: {st['items']} items, {st['known']} known to the old release, "
                     f"{st['revoked_map']} mapped via revoked-by, {st['parent_map']} to the parent technique, "
                     f"{st['dropped']} dropped ({st['dropped'] / max(st['items'], 1):.1%}); {st['incidents_with_unknown']} of "
                     f"{st['raw_incidents']} incidents had an unknown id; {st['kept_incidents']} kept (>= 4 items).")
        if r.get("campaigns_naming_a_tracked_group") and p == "unattributed":
            L.append(f"\n`unattributed`: {len(r['campaigns_naming_a_tracked_group'])} campaigns name a tracked group in their "
                     "own description (excluded in `unattributed-clean`).")
    L += ["", "| Protocol | Setting | Method | Correct [95% CI] | Names true group | Framed | Brier | "
          "Overconfident errors |", "|---|---|---|---|---|---|---|---|"]
    for p, r in o["protocols"].items():
        for s, per in r["settings"].items():
            for m, x in per.items():
                ca = x["ci95_accuracy"]
                dag = "†" if x.get("ci95_accuracy_wilson") else ""
                L.append(f"| {p} | {s} | {NAMES[m]} | {x['accuracy']:.3f} [{ca[0]:.2f}-{ca[1]:.2f}]{dag} | "
                         f"{x['named_true']:.3f} | {x['framed_rate']:.3f} | {x['brier']:.3f} | "
                         f"{x['overconfident_errors']:.3f} |")
    L += ["", "False-flag setting over framing seeds (mean ± sample SD):", "",
          "| Protocol | Method | Correct | Names framed group | Names true group |", "|---|---|---|---|---|"]
    for p, r in o["protocols"].items():
        fs = r.get("false_flag_seeds")
        if not fs:
            continue
        for m, d in fs["methods"].items():
            L.append(f"| {p} | {NAMES[m]} | {d['accuracy']['mean']:.3f} ± {d['accuracy']['sd']:.3f} | "
                     f"{d['framed_rate']['mean']:.3f} ± {d['framed_rate']['sd']:.3f} | "
                     f"{d['named_true']['mean']:.3f} ± {d['named_true']['sd']:.3f} |")
    L += ["", "*Correct*: closed = names the true group; open = declines to name; false_flag = names the true group "
          "or concludes the framed group was framed. Temporal protocols use the old release's profiles and KB and hold "
          "nothing out. Intervals: group-cluster bootstrap (n >= 50), else Wilson score interval. † = a rate of exactly 0 "
          "or 1 (e.g. the similarity baseline never declines), whose bootstrap interval is degenerate: a Wilson interval "
          "with the number of groups as the sample size is shown instead."]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--only", nargs="+", choices=PROTOCOLS, default=PROTOCOLS)
    ap.add_argument("--markers", type=int, default=3)
    ap.add_argument("--seeds", default="7,11,13,17,19")
    ap.add_argument("--out", type=Path, default=REPO / "results")
    a = ap.parse_args(argv)
    a.seeds = [int(x) for x in a.seeds.split(",")]
    attack = a.data / "enterprise-attack-19.2.json"
    hist = [a.data / "attack-history" / f"enterprise-attack-{v}.json" for v in ("12.1", "15.1")]
    prov = provenance([attack, *hist], argv)
    new = AttackData.load(attack)
    path = a.out / "attribution_extended.json"
    out = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"protocols": {}}
    out["attack_version"] = new.version
    out["provenance"] = prov
    for p in a.only:
        out["protocols"][p] = run_protocol(p, new, a)
        out["protocols"] = {k: out["protocols"][k] for k in PROTOCOLS if k in out["protocols"]}
        a.out.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=1), encoding="utf-8")  # checkpoint per protocol
    (a.out / "attribution_extended.md").write_text(render(out), encoding="utf-8")
    print(render(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
