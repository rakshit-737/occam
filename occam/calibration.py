"""Learned confidence-grade -> probability map (a calibrated grader).

ACH states its confidence as a grade (high / moderate / low). By default the
grade maps to fixed ICD-203 band midpoints (:data:`occam.attribution.GRADE_PROB`).
:class:`GradeCalibrator` learns that map from labelled outcomes instead: each
grade's probability is the Beta-smoothed empirical accuracy of answers given
at that grade, optionally monotone (a higher grade never gets a lower
probability, via pooling adjacent violators).

The benchmark fits it on the leave-one-report-out results with a group-wise
2-fold cross-fit, so reported calibrated scores never use their own labels.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

GRADES = ("low", "moderate", "high")


@dataclass
class GradeCalibrator:
    prior_strength: float = 2.0
    prior_mean: float = 0.5
    monotone: bool = True
    probs: dict[str, float] = field(default_factory=dict)
    counts: dict[str, list[int]] = field(default_factory=dict)  # grade -> [correct, total]

    def fit(self, grades: Iterable[str], correct: Iterable[bool]) -> GradeCalibrator:
        c = {g: [0, 0] for g in GRADES}
        for g, ok in zip(grades, correct):
            if g not in c:
                raise ValueError(f"unknown grade {g!r}")
            c[g][0] += bool(ok)
            c[g][1] += 1
        a = self.prior_strength
        probs = {g: (h + a * self.prior_mean) / (n + a) if n + a else self.prior_mean for g, (h, n) in c.items()}
        if self.monotone:
            probs = _pava(probs, c, a)
        self.counts, self.probs = c, probs
        return self

    def __getitem__(self, grade: str) -> float:
        return self.probs[grade]

    def mapping(self) -> dict[str, float]:
        return dict(self.probs)

    def to_dict(self) -> dict:
        return {"probs": self.probs, "counts": self.counts, "prior_strength": self.prior_strength,
                "prior_mean": self.prior_mean, "monotone": self.monotone}

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> GradeCalibrator:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        if set(d.get("probs", {})) != set(GRADES):
            raise ValueError("calibration file must map exactly low/moderate/high")
        if not all(0.0 <= float(p) <= 1.0 for p in d["probs"].values()):
            raise ValueError("calibrated probabilities must lie in [0, 1]")
        return cls(d.get("prior_strength", 2.0), d.get("prior_mean", 0.5), d.get("monotone", True),
                   {k: float(v) for k, v in d["probs"].items()}, d.get("counts", {}))


def _pava(probs: dict[str, float], counts: dict[str, list[int]], a: float) -> dict[str, float]:
    """Pool adjacent violators so p(low) <= p(moderate) <= p(high)."""
    blocks = [[probs[g], counts[g][1] + a or 1e-9, [g]] for g in GRADES]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            v1, w1, g1 = blocks[i]
            v2, w2, g2 = blocks.pop(i + 1)
            blocks[i] = [(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2, g1 + g2]
            i = max(i - 1, 0)
        else:
            i += 1
    return {g: v for v, _, gs in blocks for g in gs}
