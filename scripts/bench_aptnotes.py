#!/usr/bin/env python
"""End-to-end benchmark on real APTnotes reports: prose -> TTPs -> attribution.

Each report in the APTnotes subset fetched by ``download_data.py`` carries a
group label derived from its filename (e.g. ``Operation_Molerats`` ->
G0021). For every report OCCAM:

1. extracts ATT&CK techniques + software from the PDF text (keyword
   extractor, optionally plus the TF-IDF classifier),
2. turns them into ACH evidence, and
3. attributes the report against all ATT&CK group profiles with the
   TTP-similarity baseline and with OCCAM's ACH engine.

The extracted reports are also clustered (Louvain vs single-linkage) and
scored against the filename labels.

Caveat (stated in the README): ATT&CK group profiles are themselves partly
built from public reports like these, so this is an *optimistic* end-to-end
check of the pipeline, not a leakage-free attribution estimate -- the
leave-one-report-out benchmark (``bench_attribution.py``) is the clean one.

Usage::

    python scripts/bench_aptnotes.py [--classifier]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from occam.attribution import ACHAttributor, SimilarityAttributor, evidence_from_items  # noqa: E402
from occam.extract import extract  # noqa: E402
from occam.graph import louvain_clusters, single_linkage_clusters  # noqa: E402
from occam.knowledge import AttackData  # noqa: E402
from occam.metrics import ari, brier, nmi, purity  # noqa: E402

DATA = REPO.parent.parent / "datasets" / "occam"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--classifier", action="store_true", help="also use the TF-IDF technique classifier")
    ap.add_argument("--out", type=Path, default=REPO / "results")
    a = ap.parse_args(argv)
    t0 = time.time()

    data = AttackData.load(a.data / "enterprise-attack-19.2.json")
    kb = data.to_kb()
    profiles = data.actor_profiles()
    index = json.loads((a.data / "aptnotes" / "index.json").read_text(encoding="utf-8"))
    clf = None
    if a.classifier:
        from occam.classifier import TechniqueClassifier, training_corpus

        texts, labels = training_corpus(data)
        tram = json.loads((a.data / "tram" / "multi_label.json").read_text(encoding="utf-8"))
        texts += [r["sentence"] for r in tram]
        labels += [set(r["labels"]) for r in tram]
        clf = TechniqueClassifier(threshold=0.8, names={t: v.name for t, v in data.techniques.items()}).fit(texts, labels)
        print(f"classifier trained on {len(texts)} sentences ({time.time() - t0:.0f}s)")

    attributors = {"similarity": SimilarityAttributor(profiles, kb), "ach": ACHAttributor(profiles, kb),
                   "ach-top5": ACHAttributor(profiles, kb, shortlist=5)}
    rows, events, truth, skipped = [], {}, {}, []
    for rec in index:
        txt = a.data / "aptnotes" / "text" / rec["text"]
        try:
            text = txt.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:  # e.g. local AV quarantines reports that quote webshell code
            skipped.append((rec["path"], f"unreadable: {exc.strerror or exc}"))
            continue
        if len(text.strip()) < 500:
            skipped.append((rec["path"], "no text layer (scanned / image-only PDF)"))
            continue
        r = extract(text, rec["file"], kb, classifier=clf)
        items = sorted(r.technique_ids() | {h.technique_id for h in r.tools})
        if not items:
            skipped.append((rec["path"], "no techniques or software extracted"))
            continue
        ev = evidence_from_items(items, kb)
        row = {"report": rec["path"], "group": rec["group"], "techniques": len(r.techniques), "software": len(r.tools),
               "indicators": len(r.indicators)}
        for name, att in attributors.items():
            res = att.attribute(ev)
            row[name] = {"leading": res.leading, "kind": res.leading_kind, "p": res.probability,
                         "top5": rec["group"] in res.ranked_actors[:5]}
        rows.append(row)
        events[rec["file"]] = {"capability": items,
                               "infrastructure": sorted({i.value.lower() for i in r.indicators if i.type in ("ipv4", "domain", "sha256", "md5")})}
        truth[rec["file"]] = rec["group"]
    n = len(rows)
    summary = {}
    for name in attributors:
        correct = [row[name]["leading"] == row["group"] for row in rows]
        summary[name] = {
            "top1": sum(correct) / n,
            "top5": sum(row[name]["top5"] for row in rows) / n,
            "named_rate": sum(row[name]["leading"] is not None for row in rows) / n,
            "brier": brier([row[name]["p"] for row in rows], correct),
            "high_conf_wrong": sum(1 for row, c in zip(rows, correct) if not c and row[name]["p"] >= 0.8) / n,
        }
    ids = sorted(truth)
    t = [truth[i] for i in ids]
    clus = {}
    for label, lab in (("louvain (k=10, res=5.0)", louvain_clusters(events, resolution=5.0, knn=10)),
                       ("single-linkage (t=0.3)", single_linkage_clusters(events, 0.3))):
        p = [lab[i] for i in ids]
        clus[label] = {"purity": purity(t, p), "nmi": nmi(t, p), "ari": ari(t, p), "clusters": len(set(p))}

    out = {
        "reports": n, "skipped": skipped, "groups": len(set(truth.values())), "classifier": bool(clf),
        "mean_techniques": sum(r["techniques"] for r in rows) / n, "mean_software": sum(r["software"] for r in rows) / n,
        "mean_indicators": sum(r["indicators"] for r in rows) / n,
        "reports_per_group": dict(Counter(truth.values()).most_common()),
        "attribution": summary, "clustering": clus, "per_report": rows, "runtime_s": round(time.time() - t0, 1),
    }
    a.out.mkdir(parents=True, exist_ok=True)
    suffix = "_clf" if clf else ""
    (a.out / f"aptnotes{suffix}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = [f"### End-to-end on APTnotes ({n} real reports, {out['groups']} groups; extractor: keyword"
          f"{' + classifier' if clf else ''})", "",
          f"Mean per report: {out['mean_techniques']:.1f} techniques, {out['mean_software']:.1f} software, "
          f"{out['mean_indicators']:.1f} IOCs (all span-anchored).", "",
          "| Attributor | Top-1 | Top-5 | Names someone | Brier | Wrong at p>=0.8 |", "|---|---|---|---|---|---|"]
    names = {"similarity": "TTP-similarity baseline", "ach": "OCCAM ACH", "ach-top5": "OCCAM ACH, top-5 shortlist"}
    for k, v in summary.items():
        md.append(f"| {names[k]} | {v['top1']:.3f} | {v['top5']:.3f} | {v['named_rate']:.3f} | {v['brier']:.3f} | {v['high_conf_wrong']:.3f} |")
    md += ["", "| Clustering of the reports | Purity | NMI | ARI | #clusters |", "|---|---|---|---|---|"]
    for k, v in clus.items():
        md.append(f"| {k} | {v['purity']:.3f} | {v['nmi']:.3f} | {v['ari']:.3f} | {v['clusters']} |")
    text = "\n".join(md) + "\n"
    (a.out / f"aptnotes{suffix}.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
