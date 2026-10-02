#!/usr/bin/env python
"""Reproduce rcATT (Legoy et al., 2020, arXiv:2004.14322) report-level TTP
classification under its own setup, and run OCCAM's report classifier on the
same folds.

Setup taken from the paper (Sec. 2-4, Tables 2-4) and the released code
(vlegoy/rcATT @ f82f7fd, MIT): 1,490 ATT&CK-cited reports
(``training_data_original.csv``, ISO-8859-1), techniques with < 5 reports
dropped, 5-fold cross-validation (KFold, shuffle, random_state=42), binary
relevance (one classifier per label), micro / macro precision, recall and
F0.5 (beta = 0.5). Paper reference numbers are the "Inde." rows of Table 4
(mean +- sd over folds).

Pipelines:

* ``rcatt-released``  -- TF-IDF (Snowball stemmer, NLTK stop words, min_df=2,
  max_df=0.99 for techniques / 0.90 + WordNet lemmatiser for tactics), then per
  label SelectPercentile(chi2, 50) and LinearSVC(class_weight="balanced").
* ``rcatt-paper``     -- as described in the paper text: TF-IDF bag of words,
  half of the features kept, plain LinearSVC (no class weighting).
* ``occam-lr``        -- OCCAM's classifier family (TF-IDF 1-2 grams +
  logistic regression, one-vs-rest, as in :mod:`occam.classifier`) at
  threshold 0.5, trained on the same folds.

Usage::

    python scripts/bench_rcatt.py          # ~5 min, writes results/rcatt_reproduction.{json,md}
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from _rcatt_preprocessing import clean_text  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))

PAPER = {  # Legoy et al. 2020, Table 4, "Inde." rows (mean +- sd over 5 folds), percent
    "techniques": {"micro_p": (37.18, 6.75), "micro_r": (29.79, 5.91), "micro_f05": (35.02, 5.32),
                   "macro_p": (28.84, 6.9), "macro_r": (22.67, 5.94), "macro_f05": (25.06, 6.09)},
    "tactics": {"micro_p": (65.64, 3.76), "micro_r": (64.69, 3.0), "micro_f05": (65.38, 2.87),
                "macro_p": (60.26, 3.2), "macro_r": (58.50, 3.68), "macro_f05": (59.47, 2.29)},
}


def load(path: Path):
    csv.field_size_limit(10**9)
    with path.open(encoding="ISO-8859-1", newline="") as f:
        rows = list(csv.reader(f))
    head, body = rows[0], rows[1:]
    texts = [r[0] for r in body]
    y = np.array([[int(float(v or 0)) for v in r[1:]] for r in body])
    cols = head[1:]
    return texts, y, cols


def scores(Y: np.ndarray, P: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import fbeta_score, precision_score, recall_score

    out = {}
    for avg in ("micro", "macro"):
        out[f"{avg}_p"] = 100 * precision_score(Y, P, average=avg, zero_division=0)
        out[f"{avg}_r"] = 100 * recall_score(Y, P, average=avg, zero_division=0)
        out[f"{avg}_f05"] = 100 * fbeta_score(Y, P, beta=0.5, average=avg, zero_division=0)
    return out


def pipelines(task: str):
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    from nltk.stem.snowball import EnglishStemmer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.feature_selection import SelectPercentile, chi2
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.svm import LinearSVC

    stop = sorted(set(stopwords.words("english")))
    if task == "techniques":
        st = EnglishStemmer()

        def tok(d):
            return [st.stem(t) for t in nltk.word_tokenize(d)]
        max_df = 0.99
    else:
        wnl = WordNetLemmatizer()

        def tok(d):
            return [wnl.lemmatize(t) for t in nltk.word_tokenize(d)]
        max_df = 0.90

    def released():
        return Pipeline([
            ("tfidf", TfidfVectorizer(tokenizer=tok, token_pattern=None, stop_words=stop, min_df=2, max_df=max_df)),
            ("clf", OneVsRestClassifier(Pipeline([("sel", SelectPercentile(chi2, percentile=50)),
                                                  ("svc", LinearSVC(dual=task == "tactics", class_weight="balanced",
                                                                    max_iter=5000))]))),
        ])

    def paper():
        return Pipeline([
            ("tfidf", TfidfVectorizer(stop_words=stop, min_df=2, max_df=max_df)),
            ("clf", OneVsRestClassifier(Pipeline([("sel", SelectPercentile(chi2, percentile=50)),
                                                  ("svc", LinearSVC(max_iter=5000))]))),
        ])

    def occam():
        return Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9, sublinear_tf=True, max_features=200_000)),
            ("clf", OneVsRestClassifier(LogisticRegression(C=4.0, max_iter=2000, class_weight="balanced"))),
        ])

    return {"rcatt-released": released, "rcatt-paper": paper, "occam-lr": occam}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=REPO / "results")
    a = ap.parse_args(argv)
    import nltk

    nltk.data.path.insert(0, str(a.data / "nltk_data"))
    from sklearn.model_selection import KFold

    t0 = time.time()
    texts, y, cols = load(a.data / "rcatt" / "training_data_original.csv")
    docs = [clean_text(t) for t in texts]
    out: dict = {"n_reports": len(docs), "tasks": {}, "paper": PAPER}
    for task in ("tactics", "techniques"):
        idx = [i for i, c in enumerate(cols) if c.startswith("TA" if task == "tactics" else "T") and
               (task == "tactics" or not c.startswith("TA"))]
        Y = y[:, idx]
        if task == "techniques":
            keep = Y.sum(axis=0) >= 5
            Y = Y[:, keep]
        out["tasks"][task] = {"n_labels": int(Y.shape[1]), "methods": {}}
        for name, make in pipelines(task).items():
            folds = []
            for tr, te in KFold(5, shuffle=True, random_state=42).split(docs):
                m = make().fit([docs[i] for i in tr], Y[tr])
                folds.append(scores(Y[te], m.predict([docs[i] for i in te])))
            agg = {k: (statistics.fmean(f[k] for f in folds), statistics.stdev(f[k] for f in folds)) for k in folds[0]}
            out["tasks"][task]["methods"][name] = {"mean_sd": agg, "folds": folds}
            print(f"[{task}] {name}: micro F0.5 {agg['micro_f05'][0]:.2f} macro F0.5 {agg['macro_f05'][0]:.2f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
    out["runtime_s"] = round(time.time() - t0, 1)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "rcatt_reproduction.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = render(out)
    (a.out / "rcatt_reproduction.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def render(o: dict) -> str:
    names = {"paper": "rcATT paper, Table 4 (reported)", "rcatt-released": "Reproduction, released rcATT pipeline",
             "rcatt-paper": "Reproduction, pipeline as described in the paper", "occam-lr": "OCCAM TF-IDF + LR, same folds"}
    L = ["### Reproduction of rcATT (Legoy et al. 2020) report-level TTP classification", "",
         f"{o['n_reports']} reports, 5-fold CV (KFold, shuffle, seed 42), binary relevance; mean ± SD over folds, percent.", ""]
    for task, t in o["tasks"].items():
        L += [f"#### {task.capitalize()} ({t['n_labels']} labels)", "",
              "| Source | Micro P | Micro R | Micro F0.5 | Macro P | Macro R | Macro F0.5 |", "|---|---|---|---|---|---|---|"]
        rows = [("paper", o["paper"][task])] + [(m, r["mean_sd"]) for m, r in t["methods"].items()]
        for m, r in rows:
            L.append(f"| {names[m]} | " + " | ".join(f"{r[k][0]:.2f} ± {r[k][1]:.2f}" for k in
                                                     ("micro_p", "micro_r", "micro_f05", "macro_p", "macro_r", "macro_f05")) + " |")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
