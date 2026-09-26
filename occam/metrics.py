"""Evaluation metrics (stdlib only): multi-label P/R/F1, calibration, clustering."""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence


def prf(gold: Sequence[set[str]], pred: Sequence[set[str]]) -> dict[str, float]:
    """Micro and macro precision/recall/F1 for multi-label predictions."""
    tp = fp = fn = 0
    per: dict[str, list[int]] = {}
    for g, p in zip(gold, pred):
        for x in p & g:
            per.setdefault(x, [0, 0, 0])[0] += 1
        for x in p - g:
            per.setdefault(x, [0, 0, 0])[1] += 1
        for x in g - p:
            per.setdefault(x, [0, 0, 0])[2] += 1
        tp += len(p & g)
        fp += len(p - g)
        fn += len(g - p)
    P = tp / (tp + fp) if tp + fp else 0.0
    R = tp / (tp + fn) if tp + fn else 0.0
    f1s = []
    for a, b, c in per.values():
        if a + c == 0:  # label never in gold: skip for macro (standard 'labels present' macro)
            continue
        p_, r_ = (a / (a + b) if a + b else 0.0), a / (a + c)
        f1s.append(2 * p_ * r_ / (p_ + r_) if p_ + r_ else 0.0)
    return {
        "micro_precision": P,
        "micro_recall": R,
        "micro_f1": 2 * P * R / (P + R) if P + R else 0.0,
        "macro_f1": sum(f1s) / len(f1s) if f1s else 0.0,
        "n_labels_in_gold": len(f1s),
    }


def brier(probs: Sequence[float], correct: Sequence[bool]) -> float:
    return sum((p - float(c)) ** 2 for p, c in zip(probs, correct)) / max(len(probs), 1)


def ece(probs: Sequence[float], correct: Sequence[bool], bins: int = 10) -> float:
    """Expected calibration error with equal-width bins."""
    n = len(probs)
    if not n:
        return 0.0
    tot = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(probs) if (lo <= p < hi) or (b == bins - 1 and p == 1.0)]
        if idx:
            conf = sum(probs[i] for i in idx) / len(idx)
            acc = sum(correct[i] for i in idx) / len(idx)
            tot += len(idx) / n * abs(conf - acc)
    return tot


def reliability(probs: Sequence[float], correct: Sequence[bool], bins: int = 10) -> list[tuple[float, float, int]]:
    """(mean confidence, accuracy, count) per non-empty bin."""
    out = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(probs) if (lo <= p < hi) or (b == bins - 1 and p == 1.0)]
        if idx:
            out.append((sum(probs[i] for i in idx) / len(idx), sum(correct[i] for i in idx) / len(idx), len(idx)))
    return out


def purity(labels_true: Sequence[str], labels_pred: Sequence[int]) -> float:
    clusters: dict[int, Counter] = {}
    for t, p in zip(labels_true, labels_pred):
        clusters.setdefault(p, Counter())[t] += 1
    return sum(c.most_common(1)[0][1] for c in clusters.values()) / max(len(labels_true), 1)


def _entropy(counts: Iterable[int], n: int) -> float:
    return -sum(c / n * math.log(c / n) for c in counts if c)


def nmi(labels_true: Sequence[str], labels_pred: Sequence[int]) -> float:
    """Normalised mutual information (arithmetic normalisation, as sklearn default)."""
    n = len(labels_true)
    if n == 0:
        return 0.0
    ct = Counter(labels_true)
    cp = Counter(labels_pred)
    joint = Counter(zip(labels_true, labels_pred))
    mi = sum(v / n * math.log((v * n) / (ct[t] * cp[p])) for (t, p), v in joint.items())
    ht, hp = _entropy(ct.values(), n), _entropy(cp.values(), n)
    if ht == 0 and hp == 0:
        return 1.0
    denom = (ht + hp) / 2
    return mi / denom if denom else 0.0


def ari(labels_true: Sequence[str], labels_pred: Sequence[int]) -> float:
    """Adjusted Rand index."""
    def c2(x: int) -> float:
        return x * (x - 1) / 2

    n = len(labels_true)
    joint = Counter(zip(labels_true, labels_pred))
    sum_ij = sum(c2(v) for v in joint.values())
    a = sum(c2(v) for v in Counter(labels_true).values())
    b = sum(c2(v) for v in Counter(labels_pred).values())
    exp = a * b / c2(n) if n > 1 else 0.0
    mx = (a + b) / 2
    return (sum_ij - exp) / (mx - exp) if mx != exp else 1.0
