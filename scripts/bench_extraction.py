#!/usr/bin/env python
"""TTP-extraction benchmark on MITRE CTID TRAM2 (151 real reports, 50 techniques).

Methods (all predictions restricted to the 50 TRAM technique labels):

* ``keyword``  -- OCCAM's deterministic baseline: ATT&CK technique names
  matched as whole words (what ``occam extract`` does without a model).
* ``clf-attack`` -- TF-IDF + logistic regression trained ONLY on MITRE ATT&CK
  procedure examples / technique descriptions (no TRAM text): transfer from
  ATT&CK's own prose to vendor reports.
* ``clf-attack+tram`` -- the same model also trained on the TRAM sentences of
  the training documents.

Protocol: 5-fold cross-validation grouped by *document* (a report never has
sentences in both train and test). Decision thresholds are tuned on an inner
20% split of the training documents only. Metrics are micro/macro P/R/F1 at
sentence level (all sentences, including unlabelled ones) and at document
level (union of predicted vs gold techniques per report).

Usage::

    python scripts/bench_extraction.py            # writes results/extraction.{json,md}
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from occam.classifier import TechniqueClassifier, training_corpus  # noqa: E402
from occam.extract import _patterns  # noqa: E402
from occam.knowledge import AttackData  # noqa: E402
from occam.metrics import prf  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def load_tram(path: Path) -> list[tuple[str, str, set[str]]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [(r["doc_title"], r["sentence"], set(r["labels"])) for r in rows]


def keyword_predict(texts: list[str], kb, labels: set[str]) -> list[set[str]]:
    techs = [t for tid, t in kb.techniques.items() if tid in labels]
    out = []
    for text in texts:
        low = text.lower()
        hits = set()
        for t in techs:
            for _kw, pat, case in _patterns(t):
                if pat.search(text if case else low):
                    hits.add(t.id)
                    break
        out.append(hits)
    return out


def doc_level(docs: list[str], sets: list[set[str]]) -> tuple[list[str], list[set[str]]]:
    agg: dict[str, set[str]] = defaultdict(set)
    for d, s in zip(docs, sets):
        agg[d] |= s
    keys = sorted(agg)
    return keys, [agg[k] for k in keys]


def tune_threshold(clf: TechniqueClassifier, texts: list[str], gold: list[set[str]]) -> float:
    P = clf.predict_proba(texts)
    cls = clf.classes
    best, best_f = 0.5, -1.0
    for th in THRESHOLDS:
        pred = [{cls[j] for j in (row >= th).nonzero()[0]} for row in P]
        f = prf(gold, pred)["micro_f1"]
        if f > best_f:
            best, best_f = th, f
    return best


def folds_by_doc(docs: list[str], k: int, seed: int) -> list[set[str]]:
    uniq = sorted(set(docs))
    random.Random(seed).shuffle(uniq)
    return [set(uniq[i::k]) for i in range(k)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", type=Path, default=REPO / "results")
    ap.add_argument("--keyword-only", action="store_true", help="recompute only the keyword baseline row")
    a = ap.parse_args(argv)

    t0 = time.time()
    attack = AttackData.load(a.data / "enterprise-attack-19.2.json")
    kb = attack.to_kb()
    rows = load_tram(a.data / "tram" / "multi_label.json")
    labels = sorted({x for _, _, ls in rows for x in ls})
    L = set(labels)
    docs = [d for d, _, _ in rows]
    texts = [s for _, s, _ in rows]
    gold = [ls for _, _, ls in rows]
    print(f"TRAM2: {len(rows)} sentences, {len(set(docs))} docs, {len(labels)} techniques "
          f"({sum(1 for g in gold if g)} labelled sentences)")

    att_texts, att_labels = training_corpus(attack)
    print(f"ATT&CK training corpus: {len(att_texts)} procedure/description sentences")

    preds: dict[str, list[set[str] | None]] = {m: [None] * len(rows) for m in ("keyword", "clf-attack", "clf-attack+tram")}
    kw = keyword_predict(texts, kb, L)
    preds["keyword"] = kw
    print(f"keyword baseline done ({time.time() - t0:.0f}s)")
    if a.keyword_only:  # refresh just the keyword row of an existing results file
        prev = json.loads((a.out / "extraction.json").read_text(encoding="utf-8"))
        dk, dg = doc_level(docs, gold)
        _, dp = doc_level(docs, kw)
        prev["results"]["keyword"] = {"sentence": prf(gold, kw), "document": prf(dg, dp)}
        (a.out / "extraction.json").write_text(json.dumps(prev, indent=1), encoding="utf-8")
        (a.out / "extraction.md").write_text(render(prev), encoding="utf-8")
        print(render(prev))
        return 0

    clf_a = TechniqueClassifier().fit(att_texts, att_labels, classes=L)
    print(f"clf-attack trained: {len(clf_a.classes)} classes ({time.time() - t0:.0f}s)")
    chosen: dict[str, list[float]] = {"clf-attack": [], "clf-attack+tram": []}

    folds = folds_by_doc(docs, a.folds, a.seed)
    for k, test_docs in enumerate(folds):
        train_docs = sorted(set(docs) - test_docs)
        random.Random(a.seed + k).shuffle(train_docs)
        val_docs = set(train_docs[: max(1, len(train_docs) // 5)])
        fit_idx = [i for i, d in enumerate(docs) if d not in test_docs and d not in val_docs]
        val_idx = [i for i, d in enumerate(docs) if d in val_docs]
        test_idx = [i for i, d in enumerate(docs) if d in test_docs]

        th_a = tune_threshold(clf_a, [texts[i] for i in val_idx], [gold[i] for i in val_idx])
        chosen["clf-attack"].append(th_a)
        for i, p in zip(test_idx, clf_a.predict([texts[i] for i in test_idx], th_a)):
            preds["clf-attack"][i] = p

        clf_t = TechniqueClassifier().fit(att_texts + [texts[i] for i in fit_idx],
                                          att_labels + [gold[i] for i in fit_idx], classes=L)
        th_t = tune_threshold(clf_t, [texts[i] for i in val_idx], [gold[i] for i in val_idx])
        chosen["clf-attack+tram"].append(th_t)
        for i, p in zip(test_idx, clf_t.predict([texts[i] for i in test_idx], th_t)):
            preds["clf-attack+tram"][i] = p
        print(f"fold {k + 1}/{a.folds}: th={th_a}/{th_t} ({time.time() - t0:.0f}s)", flush=True)

    results = {}
    for m, p in preds.items():
        sent = prf(gold, p)
        dk, dg = doc_level(docs, gold)
        _, dp = doc_level(docs, p)
        doc = prf(dg, dp)
        results[m] = {"sentence": sent, "document": doc}
        # spread: per-fold document micro-F1 (mean, sample SD) and a document bootstrap 95% CI
        per_fold = []
        for fd in folds:
            idx = [i for i, d in enumerate(docs) if d in fd]
            _, g_ = doc_level([docs[i] for i in idx], [gold[i] for i in idx])
            _, p_ = doc_level([docs[i] for i in idx], [p[i] for i in idx])
            per_fold.append(prf(g_, p_)["micro_f1"])
        rng = random.Random(0)
        boot = []
        for _ in range(500):
            pick = [rng.randrange(len(dk)) for _ in dk]
            boot.append(prf([dg[j] for j in pick], [dp[j] for j in pick])["micro_f1"])
        boot.sort()
        results[m]["document_micro_f1_folds"] = {"mean": statistics.fmean(per_fold), "sd": statistics.stdev(per_fold),
                                                 "values": per_fold}
        results[m]["document_micro_f1_ci95"] = (boot[12], boot[487])
    # per-technique F1 for the best model (sentence level)
    per = {}
    for t in labels:
        g1 = [{t} & g for g in gold]
        p1 = [{t} & p for p in preds["clf-attack+tram"]]
        per[t] = {"name": kb.techniques[t].name if t in kb.techniques else t, "support": sum(1 for g in g1 if g),
                  "f1": prf(g1, p1)["micro_f1"]}

    unpredictable = sorted(t for t in labels if t not in kb.techniques)
    out = {
        "labels_not_in_attack_kb": {"labels": unpredictable,
                                    "sentence_gold_share": sum(len(g & set(unpredictable)) for g in gold) / max(1, sum(len(g) for g in gold))},
        "dataset": {"name": "TRAM2 multi_label.json", "sentences": len(rows), "documents": len(set(docs)),
                    "techniques": len(labels), "labelled_sentences": sum(1 for g in gold if g)},
        "protocol": f"{a.folds}-fold CV grouped by document, seed {a.seed}; thresholds tuned on inner 20% doc split",
        "attack_version": attack.version,
        "thresholds": chosen,
        "results": results,
        "per_technique": per,
        "runtime_s": round(time.time() - t0, 1),
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "extraction.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    (a.out / "extraction.md").write_text(render(out), encoding="utf-8")
    print(render(out))
    return 0


def render(o: dict) -> str:
    names = {"keyword": "Keyword baseline (ATT&CK technique names)",
             "clf-attack": "TF-IDF+LR trained on ATT&CK procedures only",
             "clf-attack+tram": "TF-IDF+LR trained on ATT&CK + TRAM train folds"}
    lines = [
        f"### TTP extraction on TRAM2 ({o['dataset']['documents']} reports, {o['dataset']['sentences']} sentences, "
        f"{o['dataset']['techniques']} techniques)",
        "",
        f"Protocol: {o['protocol']}. ATT&CK v{o['attack_version']}.",
        "",
        "| Method | Sent. P | Sent. R | Sent. micro-F1 | Sent. macro-F1 | Doc P | Doc R | Doc micro-F1 | Doc macro-F1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for m, r in o["results"].items():
        s, d = r["sentence"], r["document"]
        lines.append(f"| {names[m]} | {s['micro_precision']:.3f} | {s['micro_recall']:.3f} | {s['micro_f1']:.3f} | "
                     f"{s['macro_f1']:.3f} | {d['micro_precision']:.3f} | {d['micro_recall']:.3f} | {d['micro_f1']:.3f} | "
                     f"{d['macro_f1']:.3f} |")
    lines += ["", "| Method | Doc micro-F1, fold mean ± SD | Doc micro-F1, document bootstrap 95% CI |", "|---|---|---|"]
    for m, r in o["results"].items():
        if "document_micro_f1_folds" in r:
            f, c = r["document_micro_f1_folds"], r["document_micro_f1_ci95"]
            lines.append(f"| {names[m]} | {f['mean']:.3f} ± {f['sd']:.3f} | {c[0]:.3f}-{c[1]:.3f} |")
    u = o.get("labels_not_in_attack_kb")
    if u and u["labels"]:
        lines += ["", f"{len(u['labels'])} TRAM labels ({', '.join(u['labels'])}) are revoked in ATT&CK v{o['attack_version']}, so the "
                  f"keyword and ATT&CK-only models cannot predict them ({u['sentence_gold_share']:.1%} of sentence-level gold labels)."]
    per = sorted(o["per_technique"].items(), key=lambda kv: -kv[1]["f1"])
    lines += ["", "Best / worst techniques (sentence F1, ATT&CK+TRAM model):", "",
              "| Technique | Support | F1 |", "|---|---|---|"]
    for t, v in per[:5] + per[-5:]:
        lines.append(f"| {t} {v['name']} | {v['support']} | {v['f1']:.3f} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
