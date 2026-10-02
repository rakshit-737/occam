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

Leakage: ATT&CK group profiles are partly built from public reports like
these. Two numbers are therefore reported: ``as-is`` (upper bound) and
``leak-controlled``, where every ATT&CK citation of the true group that
appears to be this report is held out first (same machinery as the
leave-one-report-out benchmark). A citation is taken to be this report when
its source name shares a distinctive word with the report's file name/title,
or names the group and carries the report's year (a heuristic; matches are
listed in the JSON). Reports with no extracted technique or software are
scored as declines, so every extractor is scored on the same reports.
Intervals: Wilson 95%. ``--evidence software|techniques`` is an ablation
that keeps only one kind of extracted item.

Usage::

    python scripts/bench_aptnotes.py [--classifier]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from occam.attribution import ACHAttributor, SimilarityAttributor, evidence_from_items  # noqa: E402
from occam.evaluation import HoldoutWorld, Incident  # noqa: E402
from occam.extract import extract  # noqa: E402
from occam.graph import louvain_clusters, single_linkage_clusters  # noqa: E402
from occam.knowledge import AttackData  # noqa: E402
from occam.metrics import ari, brier, nmi, purity  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))
_GENERIC = {"report", "reports", "attack", "attacks", "group", "groups", "operation", "operations", "threat", "threats",
            "campaign", "campaigns", "malware", "analysis", "targeted", "security", "update", "technical", "research",
            "global", "advanced", "persistent", "whitepaper", "paper", "intelligence", "against", "using", "cyber",
            "espionage", "hackers", "behind", "linked", "activity", "january", "february", "march", "april", "june",
            "july", "august", "september", "october", "november", "december", "trend", "micro", "symantec", "fireeye",
            "kaspersky", "securelist", "crowdstrike", "mandiant", "trendmicro", "unit42", "networks", "blog"}


def wilson(k: int, n: int) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    z, p = 1.96, k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, c - h), min(1.0, c + h))


def _words(s: str) -> set[str]:
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s).lower()
    return {w for w in re.findall(r"[a-z]{5,}", s) if w not in _GENERIC}


def self_citations(rec: dict, title: str, data: AttackData, hw) -> list[str]:
    """ATT&CK citations of the true group that look like this very report (heuristic)."""
    g = rec["group"]
    year = rec["path"][:4]
    grp = data.groups[g]
    alias_words = set().union(*(_words(x) for x in {grp.name, *grp.aliases}))
    mine = _words(Path(rec["path"]).stem + " " + title)
    out = []
    for ref in sorted({r for refs in hw._support[g].values() for r in refs}):
        w = _words(ref)
        if (w & mine) - alias_words or ((w & alias_words) and year in ref):
            out.append(ref)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--classifier", action="store_true", help="also use the TF-IDF technique classifier")
    ap.add_argument("--save-model", type=Path, help="save the trained classifier for reuse with --model")
    ap.add_argument("--model", type=Path, help="pre-trained model from `occam train-classifier` (implies --classifier)")
    ap.add_argument("--top-k", type=int, default=None, help="keep only the k most confident classifier techniques per report")
    ap.add_argument("--evidence", choices=["all", "software", "techniques"], default="all",
                    help="ablation: attribute on only one kind of extracted item")
    ap.add_argument("--out", type=Path, default=REPO / "results")
    a = ap.parse_args(argv)
    t0 = time.time()

    data = AttackData.load(a.data / "enterprise-attack-19.2.json")
    kb = data.to_kb()
    profiles = data.actor_profiles()
    index = json.loads((a.data / "aptnotes" / "index.json").read_text(encoding="utf-8"))
    clf = None
    if a.model:
        from occam.classifier import TechniqueClassifier

        clf = TechniqueClassifier.load(a.model)
    elif a.classifier:
        from occam.classifier import TechniqueClassifier, training_corpus

        texts, labels = training_corpus(data)
        tram = json.loads((a.data / "tram" / "multi_label.json").read_text(encoding="utf-8"))
        texts += [r["sentence"] for r in tram]
        labels += [set(r["labels"]) for r in tram]
        clf = TechniqueClassifier(threshold=0.8, names={t: v.name for t, v in data.techniques.items()}).fit(texts, labels)
        if a.save_model:
            clf.save(a.save_model)
        print(f"classifier trained on {len(texts)} sentences ({time.time() - t0:.0f}s)")

    if clf is not None and a.top_k:
        clf.top_k = a.top_k
    makers = {"similarity": SimilarityAttributor, "ach": ACHAttributor,
              "ach-top5": lambda p, k: ACHAttributor(p, k, shortlist=5)}
    attributors = {n: m(profiles, kb) for n, m in makers.items()}
    hw = HoldoutWorld.build(data)
    with (a.data / "aptnotes" / "APTnotes.csv").open(encoding="utf-8", errors="replace") as f:
        titles = {re.sub(r"[^a-z0-9]", "", r["Filename"].lower()): r["Title"] for r in csv.DictReader(f)}
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
        techs, tools = r.technique_ids(), {h.technique_id for h in r.tools}
        items = sorted((techs if a.evidence != "software" else set()) | (tools if a.evidence != "techniques" else set()))
        title = titles.get(re.sub(r"[^a-z0-9]", "", Path(rec["path"]).stem.lower()), "")
        cites = self_citations(rec, title, data, hw)
        row = {"report": rec["path"], "group": rec["group"], "label_source": rec.get("label_source", "group"),
               "techniques": len(r.techniques), "software": len(r.tools), "indicators": len(r.indicators),
               "items": len(items), "self_citations": cites}
        world = hw.world(Incident(rec["group"], cites[0], items, tuple(cites))) if cites else (profiles, kb)
        for variant, (prof, kbx) in (("asis", (profiles, kb)), ("leakfree", world)):
            for name in attributors:
                if not items:  # nothing extracted: the pipeline declines
                    row[f"{name}@{variant}"] = {"leading": None, "kind": "none", "p": 0.5, "top5": False}
                    continue
                att = attributors[name] if variant == "asis" or not cites else makers[name](prof, kbx)
                res = att.attribute(evidence_from_items(items, kbx))
                row[f"{name}@{variant}"] = {"leading": res.leading, "kind": res.leading_kind, "p": res.probability,
                                            "top5": rec["group"] in res.ranked_actors[:5]}
        rows.append(row)
        if not items:
            continue
        events[rec["file"]] = {"capability": items,
                               "infrastructure": sorted({i.value.lower() for i in r.indicators if i.type in ("ipv4", "domain", "sha256", "md5")})}
        truth[rec["file"]] = rec["group"]
    n = len(rows)
    summary = {}
    for variant in ("asis", "leakfree"):
        for base in attributors:
            name = f"{base}@{variant}"
            correct = [row[name]["leading"] == row["group"] for row in rows]
            wrong_hi = sum(1 for row, c in zip(rows, correct) if not c and row[name]["p"] >= 0.8)
            summary[name] = {
                "top1": sum(correct) / n, "top1_ci95": wilson(sum(correct), n),
                "top5": sum(row[name]["top5"] for row in rows) / n,
                "named_rate": sum(row[name]["leading"] is not None for row in rows) / n,
                "brier": brier([row[name]["p"] for row in rows], correct),
                "high_conf_wrong": wrong_hi / n, "high_conf_wrong_count": wrong_hi,
            }
    ids = sorted(truth)
    t = [truth[i] for i in ids]
    clus = {}
    for label, lab in (("louvain (k=10, res=5.0)", louvain_clusters(events, resolution=5.0, knn=10)),
                       ("single-linkage (t=0.3)", single_linkage_clusters(events, 0.3))):
        p = [lab[i] for i in ids]
        clus[label] = {"purity": purity(t, p), "nmi": nmi(t, p), "ari": ari(t, p), "clusters": len(set(p))}

    out = {
        "reports": n, "skipped": skipped, "evidence": a.evidence,
        "reports_with_self_citation": sum(bool(r["self_citations"]) for r in rows),
        "no_items_extracted": sum(1 for r in rows if not r["items"]),
        "groups": len(set(truth.values())), "classifier": bool(clf), "top_k": a.top_k if clf else None,
        "mean_techniques": sum(r["techniques"] for r in rows) / n, "mean_software": sum(r["software"] for r in rows) / n,
        "mean_indicators": sum(r["indicators"] for r in rows) / n,
        "reports_per_group": dict(Counter(truth.values()).most_common()),
        "attribution": summary, "clustering": clus, "per_report": rows, "runtime_s": round(time.time() - t0, 1),
    }
    a.out.mkdir(parents=True, exist_ok=True)
    suffix = ("_clf" + (f"_top{a.top_k}" if a.top_k else "")) if clf else ""
    suffix += "" if a.evidence == "all" else f"_{a.evidence}only"
    (a.out / f"aptnotes{suffix}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = [f"### End-to-end on APTnotes ({n} real reports, {out['groups']} groups; extractor: keyword"
          f"{' + classifier' if clf else ''}{f', top-{a.top_k} per report' if clf and a.top_k else ''})", "",
          f"Mean per report: {out['mean_techniques']:.1f} techniques, {out['mean_software']:.1f} software, "
          f"{out['mean_indicators']:.1f} IOCs (all span-anchored). Evidence used: {a.evidence}. "
          f"{out['no_items_extracted']} reports with nothing extracted are scored as declines. "
          f"{out['reports_with_self_citation']} of {n} reports matched an ATT&CK citation of their own group "
          "(held out in the leak-controlled rows).", "",
          "| Attributor | Profiles | Top-1 [Wilson 95%] | Top-5 | Names someone | Brier | Wrong at p>=0.8 |",
          "|---|---|---|---|---|---|---|"]
    names = {"similarity": "TTP-similarity baseline", "ach": "OCCAM ACH", "ach-top5": "OCCAM ACH, top-5 shortlist"}
    vname = {"asis": "as-is (upper bound)", "leakfree": "leak-controlled"}
    for k, v in summary.items():
        b, var = k.split("@")
        lo, hi = v["top1_ci95"]
        md.append(f"| {names[b]} | {vname[var]} | {v['top1']:.3f} [{lo:.2f}-{hi:.2f}] | {v['top5']:.3f} | "
                  f"{v['named_rate']:.3f} | {v['brier']:.3f} | {v['high_conf_wrong_count']}/{n} |")
    md += ["", "| Clustering of the reports | Purity | NMI | ARI | #clusters |", "|---|---|---|---|---|"]
    for k, v in clus.items():
        md.append(f"| {k} | {v['purity']:.3f} | {v['nmi']:.3f} | {v['ari']:.3f} | {v['clusters']} |")
    text = "\n".join(md) + "\n"
    (a.out / f"aptnotes{suffix}.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
