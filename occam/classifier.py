"""Sentence-level text -> ATT&CK technique classifier (multi-label).

Model: TF-IDF (word 1-2 grams + char 3-5 grams) -> one-vs-rest logistic
regression. Deliberately simple, CPU-only and inspectable; it is trained on
MITRE ATT&CK *procedure examples* (the "uses" relationship descriptions) and
technique descriptions, and optionally on TRAM2 annotated report sentences.

Every prediction is emitted as a span-anchored :class:`TechniqueHit` whose
span is the sentence it was predicted from, so the provenance contract of the
keyword extractor holds for ML output too.

Requires the optional ``ml`` extra (scikit-learn, numpy).
"""
from __future__ import annotations

import pickle
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .models import SourceSpan, TechniqueHit

_SENT = re.compile(r"[^.!?\n]+(?:[.!?]+|\n|$)")


def split_sentences(text: str, min_len: int = 20) -> list[tuple[int, int, str]]:
    """(start, end, sentence) triples with offsets into ``text``."""
    out = []
    for m in _SENT.finditer(text):
        s = m.group(0)
        stripped = s.strip()
        if len(stripped) >= min_len:
            start = m.start() + (len(s) - len(s.lstrip()))
            out.append((start, start + len(stripped), stripped))
    return out


def parent_of(tid: str) -> str:
    return tid.split(".")[0]


@dataclass
class TechniqueClassifier:
    threshold: float = 0.35
    parent_level: bool = False
    C: float = 8.0
    max_features: int = 60_000
    char_ngrams: bool = False  # adds char 3-5 grams: ~+0.01 F1 for ~5x training time
    n_jobs: int = 1  # >1 forks workers that each copy the feature matrix
    names: dict[str, str] = field(default_factory=dict)
    _vec: object = None
    _clf: object = None
    _mlb: object = None

    # -- training -------------------------------------------------------------
    def fit(self, texts: Sequence[str], labels: Sequence[Iterable[str]], min_examples: int = 2,
            classes: Iterable[str] | None = None) -> TechniqueClassifier:
        """Fit one binary model per technique.

        ``classes`` restricts the label space (e.g. to the 50 TRAM techniques);
        examples of other techniques then act as negatives / background.
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.multiclass import OneVsRestClassifier
        from sklearn.pipeline import FeatureUnion
        from sklearn.preprocessing import MultiLabelBinarizer

        labs = [{parent_of(x) if self.parent_level else x for x in ls} for ls in labels]
        counts: dict[str, int] = {}
        for ls in labs:
            for x in ls:
                counts[x] = counts.get(x, 0) + 1
        keep = {k for k, v in counts.items() if v >= min_examples}
        if classes is not None:
            keep &= set(classes)
        labs = [ls & keep for ls in labs]
        self._mlb = MultiLabelBinarizer(classes=sorted(keep))
        y = self._mlb.fit_transform(labs)
        parts = [("w", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=self.max_features, sublinear_tf=True,
                                       stop_words="english", token_pattern=r"(?u)\b[\w.\-]{2,}\b"))]
        if self.char_ngrams:
            parts.append(("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3,
                                               max_features=self.max_features, sublinear_tf=True)))
        self._vec = FeatureUnion(parts)
        X = self._vec.fit_transform(list(texts))
        self._clf = OneVsRestClassifier(
            LogisticRegression(C=self.C, solver="liblinear", class_weight="balanced", max_iter=200), n_jobs=self.n_jobs
        )
        self._clf.fit(X, y)
        return self

    @property
    def classes(self) -> list[str]:
        return list(self._mlb.classes_) if self._mlb is not None else []

    # -- inference ------------------------------------------------------------
    def predict_proba(self, texts: Sequence[str]):
        return self._clf.predict_proba(self._vec.transform(list(texts)))

    def predict(self, texts: Sequence[str], threshold: float | None = None) -> list[set[str]]:
        th = self.threshold if threshold is None else threshold
        P = self.predict_proba(texts)
        cls = self.classes
        return [{cls[j] for j in (row >= th).nonzero()[0]} for row in P]

    def hits(self, text: str, source_id: str = "doc", threshold: float | None = None) -> list[TechniqueHit]:
        """Span-anchored hits: one per (technique, best sentence)."""
        sents = split_sentences(text)
        if not sents:
            return []
        th = self.threshold if threshold is None else threshold
        P = self.predict_proba([s for _, _, s in sents])
        cls = self.classes
        best: dict[str, tuple[float, int]] = {}
        for i, row in enumerate(P):
            for j in (row >= th).nonzero()[0]:
                if cls[j] not in best or row[j] > best[cls[j]][0]:
                    best[cls[j]] = (float(row[j]), i)
        out = []
        for tid, (p, i) in sorted(best.items(), key=lambda kv: -kv[1][0]):
            s, e, sent = sents[i]
            out.append(TechniqueHit(tid, self.names.get(tid, tid), f"classifier p={p:.2f}", SourceSpan(source_id, s, e, text[s:e])))
        return out

    # -- persistence (only load files you produced yourself: pickle) ----------
    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(pickle.dumps(self))

    @staticmethod
    def load(path: str | Path) -> TechniqueClassifier:
        obj = pickle.loads(Path(path).read_bytes())  # noqa: S301 - trusted local artefact
        if not isinstance(obj, TechniqueClassifier):
            raise TypeError("not a TechniqueClassifier")
        return obj


def training_corpus(data, include_descriptions: bool = True) -> tuple[list[str], list[set[str]]]:
    """ATT&CK procedure examples (+ first sentences of technique descriptions)."""
    texts: list[str] = []
    labels: list[set[str]] = []
    for text, tid, _src in data.procedures():
        texts.append(text)
        labels.append({tid})
    if include_descriptions:
        for tid, t in data.techniques.items():
            for _, _, s in split_sentences(t.description)[:4]:
                texts.append(s)
                labels.append({tid})
    return texts, labels
