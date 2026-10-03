#!/usr/bin/env python
"""Reproduce rcATT (Legoy et al., 2020, arXiv:2004.14322v1) report-level TTP
classification under its own setup, and run OCCAM's report classifier on the
same folds.

Setup taken from the paper (Sec. 2-4) and the released code (vlegoy/rcATT @
f82f7fd, MIT, ``classification_tools/__init__.py`` ``train()``): 1,490
ATT&CK-cited reports (``training_data_original.csv``, ISO-8859-1), techniques
with < 5 reports dropped, 5-fold cross-validation (KFold, shuffle,
random_state=42 as in the released code; the paper only says 5-fold), binary
relevance (one classifier per label), micro / macro precision, recall and F0.5
(beta = 0.5). Paper reference numbers are the "Inde." rows of Table 4 of
arXiv:2004.14322v1 (mean +- sd over folds; Table 5 repeats them, and the same
means without SD are the TF-IDF "BR Linear SVC" rows of Tables 2 and 3).

Pipelines: a 2 x 2 ablation of the two settings in which the released code
differs from the paper text (tokenisation and class weighting), plus OCCAM.

* ``rcatt-released``          -- the released code: rcATT's text clean-up, NLTK
  word tokens WordNet-lemmatised (tactics) or Snowball-stemmed (techniques),
  NLTK stop words plus rcATT's extra stemmed stop words, TF-IDF (tactics:
  max_df=0.90; techniques: min_df=2, max_df=0.99), SelectPercentile(chi2, 50)
  over all labels, then one LinearSVC(class_weight="balanced") per label
  (tactics: dual=True; techniques: dual=False; max_iter=1000).
* ``rcatt-released-noweight`` -- the same with class_weight=None.
* ``rcatt-paper``             -- the paper text's description: TF-IDF bag of
  words with scikit-learn's default tokeniser and plain NLTK stop words (no
  stemming or lemmatising), the same df limits, chi2 selection and LinearSVC
  as the code, without class weighting. (The paper text describes keeping the
  words with the highest TF-IDF scores; the code's chi2 selection is used for
  both so that only tokenisation and weighting differ.)
* ``rcatt-paper-balanced``    -- the paper-text pipeline with class_weight="balanced".
* ``occam-lr``                -- OCCAM's classifier family (TF-IDF 1-2 grams +
  logistic regression, one-vs-rest, as in :mod:`occam.classifier`) at
  threshold 0.5, trained on the same folds.

Usage::

    python scripts/bench_rcatt.py               # ~25 min, writes results/rcatt_reproduction.{json,md}
    python scripts/bench_rcatt.py --limit 300   # smoke run on the first 300 reports
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from _benchutil import provenance, source_line  # noqa: E402
from _rcatt_preprocessing import clean_text  # noqa: E402

DATA = Path(os.environ.get("OCCAM_DATA", REPO.parent.parent / "datasets" / "occam"))

PAPER_SOURCE = ("rcATT paper (Legoy et al. 2020, arXiv:2004.14322v1, Table 4 'Inde.' rows; "
                "same means in Tables 2-3, TF-IDF BR Linear SVC)")
PAPER = {  # Legoy et al. 2020 (arXiv:2004.14322v1), Table 4 "Inde." rows (mean +- sd over 5 folds), percent
    "techniques": {"micro_p": (37.18, 6.75), "micro_r": (29.79, 5.91), "micro_f05": (35.02, 5.32),
                   "macro_p": (28.84, 6.9), "macro_r": (22.67, 5.94), "macro_f05": (25.06, 6.09)},
    "tactics": {"micro_p": (65.64, 3.76), "micro_r": (64.69, 3.0), "micro_f05": (65.38, 2.87),
                "macro_p": (60.26, 3.2), "macro_r": (58.50, 3.68), "macro_f05": (59.47, 2.29)},
}
#: rcATT's extra stop words (classification_tools/__init__.py, train())
RCATT_EXTRA_STOP = ["'ll", "'re", "'ve", "ha", "wa", "'d", "'s", "abov", "ani", "becaus", "befor", "could", "doe", "dure",
                    "might", "must", "n't", "need", "onc", "onli", "ourselv", "sha", "themselv", "veri", "whi", "wo",
                    "would", "yourselv"]
NAMES = {"paper": PAPER_SOURCE,
         "rcatt-released": "Reproduction, released rcATT pipeline (stemmed/lemmatised tokens, balanced class weights)",
         "rcatt-released-noweight": "Released pipeline without class weighting",
         "rcatt-paper": "Pipeline as the paper text describes it (default tokens, no class weighting)",
         "rcatt-paper-balanced": "Paper-text pipeline with balanced class weights",
         "occam-lr": "OCCAM TF-IDF + LR, same folds"}
#: (label, minuend, subtrahend) of the fold-paired ablation differences
EFFECTS = [("class weighting, released tokens", "rcatt-released", "rcatt-released-noweight"),
           ("class weighting, paper-text tokens", "rcatt-paper-balanced", "rcatt-paper"),
           ("rcATT tokenisation, balanced weights", "rcatt-released", "rcatt-paper-balanced"),
           ("rcATT tokenisation, no weighting", "rcatt-released-noweight", "rcatt-paper"),
           ("both (released minus paper text)", "rcatt-released", "rcatt-paper")]


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


def _ident(x):
    return x


def pipelines(task: str, docs: list[str]):
    """Pipelines; the (slow) NLTK tokenisation is done once per task and the
    vectoriser consumes the token lists -- equivalent to rcATT's tokenizer +
    stop-word filtering inside every fold, because tokenisation is per document
    and has no fitted state."""
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

    nltk_stop = list(stopwords.words("english"))
    rcatt_stop = set(nltk_stop) | set(RCATT_EXTRA_STOP)
    if task == "techniques":
        st = EnglishStemmer()

        def tok(d):
            return [st.stem(t) for t in nltk.word_tokenize(d)]
        df = {"min_df": 2, "max_df": 0.99}
        svc = {"dual": False, "max_iter": 1000}
    else:
        wnl = WordNetLemmatizer()

        def tok(d):
            return [wnl.lemmatize(t) for t in nltk.word_tokenize(d)]
        df = {"max_df": 0.90}
        svc = {"dual": True, "max_iter": 1000}

    toks = [tuple(t for t in tok(d) if t not in rcatt_stop) for d in docs]

    def rcatt(tokens: bool, weight: str | None):
        def build():
            vec = TfidfVectorizer(analyzer=_ident, **df) if tokens else TfidfVectorizer(stop_words=nltk_stop, **df)
            return Pipeline([
                ("tfidf", vec),
                ("sel", SelectPercentile(chi2, percentile=50)),  # one selection over all labels, as in rcATT
                ("clf", OneVsRestClassifier(LinearSVC(class_weight=weight, **svc), n_jobs=4)),
            ])
        return build

    def occam():
        return Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9, sublinear_tf=True, max_features=200_000)),
            ("clf", OneVsRestClassifier(n_jobs=4, estimator=LogisticRegression(C=4.0, max_iter=2000, class_weight="balanced"))),
        ])

    return {"rcatt-released": (rcatt(True, "balanced"), toks),
            "rcatt-released-noweight": (rcatt(True, None), toks),
            "rcatt-paper": (rcatt(False, None), docs),
            "rcatt-paper-balanced": (rcatt(False, "balanced"), docs),
            "occam-lr": (occam, docs)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--limit", type=int, default=None, help="use only the first N reports (smoke run)")
    ap.add_argument("--out", type=Path, default=REPO / "results")
    a = ap.parse_args(argv)
    import nltk

    nltk.data.path.insert(0, str(a.data / "nltk_data"))
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.model_selection import KFold

    warnings.filterwarnings("ignore", category=ConvergenceWarning)  # rcATT's max_iter=1000, kept as released
    t0 = time.time()
    csv_path = a.data / "rcatt" / "training_data_original.csv"
    prov = provenance([csv_path], argv)
    texts, y, cols = load(csv_path)
    if a.limit:
        texts, y = texts[: a.limit], y[: a.limit]
    docs = [clean_text(t) for t in texts]
    out: dict = {"n_reports": len(docs), "tasks": {}, "paper": PAPER, "paper_source": PAPER_SOURCE}
    for task in ("tactics", "techniques"):
        idx = [i for i, c in enumerate(cols) if c.startswith("TA" if task == "tactics" else "T") and
               (task == "tactics" or not c.startswith("TA"))]
        Y = y[:, idx]
        if task == "techniques":
            keep = Y.sum(axis=0) >= 5
            Y = Y[:, keep]
        out["tasks"][task] = {"n_labels": int(Y.shape[1]), "methods": {}}
        for name, (make, X) in pipelines(task, docs).items():
            folds = []
            for tr, te in KFold(5, shuffle=True, random_state=42).split(docs):
                m = make().fit([X[i] for i in tr], Y[tr])
                folds.append(scores(Y[te], m.predict([X[i] for i in te])))
            agg = {k: (statistics.fmean(f[k] for f in folds), statistics.stdev(f[k] for f in folds)) for k in folds[0]}
            out["tasks"][task]["methods"][name] = {"mean_sd": agg, "folds": folds}
            print(f"[{task}] {name}: micro F0.5 {agg['micro_f05'][0]:.2f} macro F0.5 {agg['macro_f05'][0]:.2f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
        M = out["tasks"][task]["methods"]
        out["tasks"][task]["effects_micro_f05"] = {
            label: _paired([f["micro_f05"] for f in M[x]["folds"]], [f["micro_f05"] for f in M[y_]["folds"]])
            for label, x, y_ in EFFECTS}
    out["runtime_s"] = round(time.time() - t0, 1)
    out["provenance"] = prov
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "rcatt_reproduction.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = render(out)
    (a.out / "rcatt_reproduction.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def _paired(a: list[float], b: list[float]) -> tuple[float, float]:
    """Mean and sample SD over folds of the per-fold difference a - b (same folds)."""
    d = [x - y for x, y in zip(a, b)]
    return statistics.fmean(d), statistics.stdev(d)


def render(o: dict) -> str:
    L = ["### Reproduction of rcATT (Legoy et al. 2020) report-level TTP classification", "",
         f"{o['n_reports']} reports, 5-fold CV (KFold, shuffle, seed 42, as in the released code), binary relevance; "
         "mean ± SD over folds (dispersion of the 5 folds, not a confidence interval), percent.", "",
         source_line(o.get("provenance")), ""]
    for task, t in o["tasks"].items():
        L += [f"#### {task.capitalize()} ({t['n_labels']} labels)", "",
              "| Source | Micro P | Micro R | Micro F0.5 | Macro P | Macro R | Macro F0.5 |", "|---|---|---|---|---|---|---|"]
        rows = [("paper", o["paper"][task])] + [(m, r["mean_sd"]) for m, r in t["methods"].items()]
        for m, r in rows:
            L.append(f"| {NAMES[m]} | " + " | ".join(f"{r[k][0]:.2f} ± {r[k][1]:.2f}" for k in
                                                     ("micro_p", "micro_r", "micro_f05", "macro_p", "macro_r", "macro_f05")) + " |")
        if t.get("effects_micro_f05"):
            L += ["", "| Effect on micro F0.5 (same 5 folds) | Fold-paired difference, mean ± SD |", "|---|---|"]
            for label, (mu, sd) in t["effects_micro_f05"].items():
                L.append(f"| {label} | {mu:+.2f} ± {sd:.2f} |")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
