"""Attribution over real ATT&CK group profiles: OCCAM's ACH vs a naive baseline.

Two attributors share one interface -- ``attribute(evidence) -> Attribution``:

* `SimilarityAttributor` -- the *naive TTP-similarity* baseline the
  research question is framed against: IDF-weighted cosine similarity between
  the observed techniques/software and every group profile, confidence =
  softmax over similarities. Spoofable markers are (naively) counted as
  matches for the actor they point at.
* `ACHAttributor` -- the Heuer ACH engine from `occam.ach` with the
  mandatory unknown-actor and false-flag hypotheses and capped confidence.

Both return the *probability that the leading named answer is correct*, so
calibration (Brier, ECE) can be compared on equal terms.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .ach import ACHEngine
from .attack import AttackKB
from .models import ActorProfile, Evidence, EvidenceKind

#: ICD-203 likelihood-band midpoints used to turn ACH grades into probabilities.
GRADE_PROB = {"high": 0.875, "moderate": 0.675, "low": 0.5}


@dataclass
class Attribution:
    leading: str | None          # actor id, or None for unknown / false-flag conclusions
    leading_kind: str            # actor | unknown | false_flag
    probability: float           # stated probability that `leading` is right
    confidence: str              # high | moderate | low (baseline derives it from probability)
    ranked_actors: list[str] = field(default_factory=list)  # named actors, best first
    flagged: str | None = None   # actor the conclusion says was *framed* (false-flag conclusions)
    hard_score: float | None = None  # baseline only: best cosine on non-spoofable evidence


def evidence_from_items(items: list[str], kb: AttackKB, prefix: str = "E") -> list[Evidence]:
    """Turn observed technique / software ids into ACH evidence rows."""
    out = []
    for i, x in enumerate(sorted(items), 1):
        kind = EvidenceKind.TOOL if x.startswith("S") or x.startswith("tool:") else EvidenceKind.TTP
        name = (kb.get(x).name if kb.get(x) else x)
        out.append(Evidence(f"{prefix}{i}", f"{kind.value}: {x} {name}", kind, value=x, reliability="B", credibility=2))
    return out


def planted_markers(framed_actor: str, n: int = 3, prefix: str = "FF") -> list[Evidence]:
    """Spoofable markers (code overlap, metadata, language) pointing at one actor."""
    kinds = [EvidenceKind.CODE_OVERLAP, EvidenceKind.METADATA, EvidenceKind.LANGUAGE_ARTIFACT, EvidenceKind.CLAIM]
    return [
        Evidence(f"{prefix}{i + 1}", f"planted {kinds[i % 4].value} marker -> {framed_actor}", kinds[i % 4],
                 points_to=[framed_actor], reliability="B", credibility=2)
        for i in range(n)
    ]


def _grade(p: float) -> str:
    return "high" if p >= 0.8 else "moderate" if p >= 0.55 else "low"


class SimilarityAttributor:
    """IDF-weighted cosine nearest-profile matching with softmax confidence.

    ``marker_boost`` is how much cosine each spoofable marker adds to the actor
    it points at (0 = the baseline ignores spoofable evidence entirely) and
    ``temperature`` is the softmax temperature. The defaults (0.15, 0.05) are
    the *marker-trusting* baseline; results depend strongly on ``marker_boost``
    (see ``results/falseflag.md`` for a sweep).
    """

    name = "baseline: TTP-similarity (IDF cosine + softmax)"

    def __init__(self, profiles: list[ActorProfile], kb: AttackKB, temperature: float = 0.05, marker_boost: float = 0.15):
        self.profiles = profiles
        self.kb = kb
        self.temperature = temperature
        self.marker_boost = marker_boost
        n = max(kb.n_groups, len(profiles), 1)
        self._idf = lambda x: math.log((1 + n) / (1 + kb.usage.get(x, 0))) + 1.0
        self._vecs = [({x: self._idf(x) for x in (*p.techniques, *p.tools)}) for p in profiles]
        self._norms = [math.sqrt(sum(v * v for v in vec.values())) or 1.0 for vec in self._vecs]

    def scores(self, evidence: list[Evidence]) -> list[float]:
        obs = {e.value: self._idf(e.value) for e in evidence if e.value and not e.spoofable}
        on = math.sqrt(sum(v * v for v in obs.values())) or 1.0
        out = []
        for p, vec, pn in zip(self.profiles, self._vecs, self._norms):
            s = sum(w * vec[x] for x, w in obs.items() if x in vec) / (on * pn)
            s += self.marker_boost * sum(1 for e in evidence if e.spoofable and p.id in e.points_to)
            out.append(s)
        return out

    def attribute(self, evidence: list[Evidence]) -> Attribution:
        s = self.scores(evidence)
        order = sorted(range(len(s)), key=lambda i: -s[i])
        m = max(s)
        z = [math.exp((x - m) / self.temperature) for x in s]
        p = z[order[0]] / sum(z)
        hard = max(self.hard_scores(evidence), default=0.0)
        return Attribution(self.profiles[order[0]].id, "actor", p, _grade(p), [self.profiles[i].id for i in order],
                           hard_score=hard)

    def hard_scores(self, evidence: list[Evidence]) -> list[float]:
        """Cosine on non-spoofable evidence only (no marker boost)."""
        boost, self.marker_boost = self.marker_boost, 0.0
        try:
            return self.scores(evidence)
        finally:
            self.marker_boost = boost


class ACHAttributor:
    """OCCAM's ACH engine applied to ATT&CK profiles."""

    name = "OCCAM ACH (least-inconsistency + confidence caps)"

    def __init__(self, profiles: list[ActorProfile], kb: AttackKB, shortlist: int | None = None,
                 ranking_rule: str = "heuer", grade_prob: dict[str, float] | None = None, **engine_kw):
        self.profiles = profiles
        self.kb = kb
        self.shortlist = shortlist
        self.ranking_rule = ranking_rule
        #: grade -> stated probability; defaults to ICD-203 midpoints, or a learned
        #: `occam.calibration.GradeCalibrator` mapping
        self.grade_prob = dict(grade_prob or GRADE_PROB)
        #: extra `occam.ach.ACHEngine` switches (ablations)
        self.engine_kw = engine_kw
        self._sim = SimilarityAttributor(profiles, kb) if shortlist else None

    def candidates(self, evidence: list[Evidence]) -> list[ActorProfile]:
        """All profiles, or -- with ``shortlist`` -- the top-k by TTP similarity
        plus every actor that a spoofable marker points at (so the matching
        false-flag hypothesis is always on the table)."""
        if not self._sim:
            return self.profiles
        s = self._sim.scores([e for e in evidence if not e.spoofable])
        order = sorted(range(len(s)), key=lambda i: -s[i])[: self.shortlist]
        keep = {self.profiles[i].id for i in order} | {p for e in evidence if e.spoofable for p in e.points_to}
        return [p for p in self.profiles if p.id in keep]

    def assess(self, evidence: list[Evidence]):
        return ACHEngine(self.candidates(evidence), evidence, kb=self.kb, sensitivity=False,
                         ranking_rule=self.ranking_rule, **self.engine_kw).assess()

    def attribute(self, evidence: list[Evidence]) -> Attribution:
        a = self.assess(evidence)
        top = a.leading.hypothesis
        actors = [s.hypothesis.actor_id for s in a.ranking if s.hypothesis.kind == "actor"]
        return Attribution(top.actor_id if top.kind == "actor" else None, top.kind,
                           self.grade_prob[a.confidence], a.confidence, actors,
                           flagged=top.actor_id if top.kind == "false_flag" else None)


class IDFCoverageAttributor(SimilarityAttributor):
    """Plain coverage baseline: the share of the observed IDF mass that a
    group's profile covers (no length normalisation of the profile, so large
    profiles are not penalised). Spoofable markers are ignored."""

    name = "baseline: IDF coverage"

    def __init__(self, profiles: list[ActorProfile], kb: AttackKB, temperature: float = 0.05):
        super().__init__(profiles, kb, temperature=temperature, marker_boost=0.0)

    def scores(self, evidence: list[Evidence]) -> list[float]:
        obs = {e.value: self._idf(e.value) for e in evidence if e.value and not e.spoofable}
        tot = sum(obs.values()) or 1.0
        return [sum(w for x, w in obs.items() if x in vec) / tot for vec in self._vecs]
