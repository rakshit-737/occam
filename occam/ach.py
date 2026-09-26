"""Analysis of Competing Hypotheses (Heuer) with confidence grading.

Design rules (deliberately conservative):

* Hypotheses are ranked by *least weighted inconsistency*, never by most
  support. Consistent evidence is reported but does not drive the ranking.
* Every assessment includes an ``unknown actor`` hypothesis and one
  ``false flag`` hypothesis per actor that planted-able markers point at.
* Spoofable evidence (code overlap, language artifacts, metadata, claims)
  is down-weighted and a conclusion leaning mostly on it is capped at LOW.
* Non-diagnostic evidence (rated the same for every hypothesis) gets zero
  weight, as in Heuer's method.
* The rule-based rater only proposes cells; analysts can override any cell
  and the result is recomputed deterministically.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .attack import AttackKB, load_bundled
from .models import (
    ActorProfile,
    Assessment,
    Consistency,
    Evidence,
    EvidenceKind,
    Hypothesis,
    HypothesisScore,
)

SPOOFABLE_DISCOUNT = 0.5
C = Consistency

_PHRASES = {"high": "highly likely", "moderate": "likely", "low": "roughly even chance / cannot be determined"}


def build_hypotheses(actors: Iterable[ActorProfile], evidence: Iterable[Evidence]) -> list[Hypothesis]:
    actors = list(actors)
    hyps = [Hypothesis(f"H-{a.id}", f"{a.name} conducted the activity", "actor", a.id) for a in actors]
    framed = sorted({p for e in evidence if e.spoofable for p in e.points_to})
    names = {a.id: a.name for a in actors}
    for aid in framed:
        hyps.append(
            Hypothesis(f"H-FF-{aid}", f"False flag: another actor framed {names.get(aid, aid)}", "false_flag", aid)
        )
    hyps.append(Hypothesis("H-UNKNOWN", "An unknown / untracked actor", "unknown", None))
    return hyps


def rate_actor(e: Evidence, a: ActorProfile, kb: AttackKB) -> Consistency:
    """Rate one evidence item against one actor profile.

    TTPs: common techniques are non-diagnostic (N); a match is C, or CC when
    the technique is rare across ATT&CK groups; a technique only matched at
    parent level (T1059.001 vs T1059.003) is N; absence from the profile is I.
    Absence is only *weakly* inconsistent because public profiles are
    incomplete - this is what keeps large-profile bias in check.
    """
    if e.points_to:
        if a.id in e.points_to:
            return C.C if e.spoofable else C.CC
        return C.I if e.spoofable else C.II
    if e.kind is EvidenceKind.TTP:
        if kb.is_common(e.value):
            return C.N
        techs = a.technique_set
        if e.value in techs:
            return C.CC if kb.is_rare(e.value) else C.C
        if e.value.split(".")[0] in a.technique_parents:
            return C.N
        return C.I
    if e.kind is EvidenceKind.TOOL:
        if e.value in a.tool_set:
            return C.C if kb.is_common(e.value) else C.CC
        return C.N if kb.is_common(e.value) else C.I
    if e.kind is EvidenceKind.INFRASTRUCTURE:
        return C.CC if e.value in a.infrastructure else C.I
    if e.kind is EvidenceKind.VICTIMOLOGY:
        return C.C if e.value in a.sectors else C.I
    return C.N


def rate(e: Evidence, h: Hypothesis, actors: dict[str, ActorProfile], kb: AttackKB) -> Consistency:
    if h.kind == "actor":
        return rate_actor(e, actors[h.actor_id], kb)
    if h.kind == "false_flag":
        framed = actors.get(h.actor_id)
        if e.spoofable:
            if h.actor_id in e.points_to:
                return C.CC  # planted markers are exactly what a false flag predicts
            return C.N
        if framed is None:
            return C.N
        r = rate_actor(e, framed, kb)
        if r.value <= C.I.value:
            return C.C   # hard evidence contradicting the framed actor fits a frame-up
        if r.value >= C.C.value:
            return C.I   # hard evidence genuinely matching the framed actor undermines it
        return C.N
    # unknown actor: hard, distinctive evidence that matches a tracked actor argues against it
    if not e.spoofable:
        best = max((rate_actor(e, a, kb).value for a in actors.values()), default=0)
        if best >= C.CC.value:
            return C.I
    return C.N


@dataclass
class ACHEngine:
    actors: list[ActorProfile]
    evidence: list[Evidence]
    question: str = "Who conducted the activity?"
    kb: AttackKB = field(default_factory=load_bundled)
    overrides: dict[tuple[str, str], Consistency] = field(default_factory=dict)
    sensitivity: bool = True  # leave-one-out "what would change" pass (O(E^2 H))
    #: "heuer" ranks by least weighted inconsistency only (default). "balanced" is a
    #: support-aware variant: score = inconsistency + support_weight * support, which
    #: lets consistent evidence count and so reduces the pull towards large profiles.
    ranking_rule: str = "heuer"
    support_weight: float = 0.5

    def __post_init__(self) -> None:
        ids = [e.id for e in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate evidence ids")
        if self.ranking_rule not in ("heuer", "balanced"):
            raise ValueError(f"unknown ranking_rule {self.ranking_rule!r}")
        self._actors = {a.id: a for a in self.actors}
        self.hypotheses = build_hypotheses(self.actors, self.evidence)
        self._rows: dict[str, dict[str, Consistency]] = {}

    # -- matrix -------------------------------------------------------------
    def _rule_row(self, e: Evidence) -> dict[str, Consistency]:
        row = self._rows.get(e.id)
        if row is None:
            row = {h.id: rate(e, h, self._actors, self.kb) for h in self.hypotheses}
            self._rows[e.id] = row
        return row

    def matrix(self, evidence: list[Evidence] | None = None) -> dict[str, dict[str, Consistency]]:
        ev = self.evidence if evidence is None else evidence
        m: dict[str, dict[str, Consistency]] = {}
        for e in ev:
            base = self._rule_row(e)
            m[e.id] = {h.id: self.overrides.get((e.id, h.id)) or base[h.id] for h in self.hypotheses}
        return m

    def override(self, evidence_id: str, hypothesis_id: str, rating: Consistency | str) -> None:
        if evidence_id not in {e.id for e in self.evidence}:
            raise KeyError(evidence_id)
        if hypothesis_id not in {h.id for h in self.hypotheses}:
            raise KeyError(hypothesis_id)
        self.overrides[(evidence_id, hypothesis_id)] = rating if isinstance(rating, Consistency) else Consistency.parse(rating)

    @staticmethod
    def _diag_weight(e: Evidence, row: dict[str, Consistency]) -> float:
        vals = [r.value for r in row.values()]
        spread = (max(vals) - min(vals)) / 4.0  # 0 = non-diagnostic, 1 = maximally diagnostic
        w = e.weight * spread
        return w * SPOOFABLE_DISCOUNT if e.spoofable else w

    def _score(self, evidence: list[Evidence]) -> tuple[list[HypothesisScore], dict, dict[str, float]]:
        m = self.matrix(evidence)
        weights = {e.id: self._diag_weight(e, m[e.id]) for e in evidence}
        by_id = {e.id: e for e in evidence}
        scores = []
        for h in self.hypotheses:
            inc = sup = spoof_sup = 0.0
            for eid, row in m.items():
                v, w = row[h.id].value, weights[eid]
                if v < 0:
                    inc += v * w
                elif v > 0:
                    sup += v * w
                    if by_id[eid].spoofable:
                        spoof_sup += v * w
            if self.ranking_rule == "balanced":
                # consistent evidence offsets inconsistency; spoofable support never helps rank
                inc = inc + self.support_weight * (sup - spoof_sup)  # net score, may be > 0
            scores.append(HypothesisScore(h, inc, sup, (spoof_sup / sup) if sup else 0.0))
        # Least inconsistency first (Heuer). Ties go to the MORE CONSERVATIVE hypothesis
        # (unknown > false flag > named actor) before support, to resist overconfident naming.
        order = {"unknown": 0, "false_flag": 1, "actor": 2}
        scores.sort(key=lambda s: (-round(s.inconsistency, 9), order[s.hypothesis.kind], -s.support))
        return scores, m, weights

    # -- assessment ---------------------------------------------------------
    def assess(self) -> Assessment:
        if not self.evidence:
            raise ValueError("ACH needs at least one evidence item")
        ranking, m, weights = self._score(self.evidence)
        top, second = ranking[0], ranking[1]
        total = sum(weights.values()) or 1e-9
        rel_gap = (top.inconsistency - second.inconsistency) / total
        n_diag = sum(1 for w in weights.values() if w > 0)
        rationale: list[str] = [
            f"Leading hypothesis '{top.hypothesis.label}' has weighted inconsistency {top.inconsistency:.2f} "
            f"vs {second.inconsistency:.2f} for runner-up '{second.hypothesis.label}' (relative gap {rel_gap:.2f}).",
            f"{n_diag} of {len(self.evidence)} evidence items are diagnostic.",
        ]

        if rel_gap >= 0.35 and n_diag >= 5:
            conf = "high"
        elif rel_gap >= 0.15 and n_diag >= 3:
            conf = "moderate"
        else:
            conf = "low"
            rationale.append("Margin between top hypotheses is small or evidence is thin -> LOW.")

        def cap(level: str, why: str) -> None:
            nonlocal conf
            rank = {"low": 0, "moderate": 1, "high": 2}
            if rank[conf] > rank[level]:
                conf = level
                rationale.append(f"Capped at {level.upper()}: {why}")

        if top.spoofable_support_ratio >= 0.5:
            cap("low", "most supporting evidence is cheaply spoofable (code/language/metadata/claims).")
        if top.hypothesis.kind != "actor":
            cap("moderate", "deception / unknown-actor conclusions cannot be confirmed from technical evidence alone.")
        if top.hypothesis.kind == "actor":
            ff = next((s for s in ranking if s.hypothesis.kind == "false_flag" and s.hypothesis.actor_id == top.hypothesis.actor_id), None)
            if ff and (top.inconsistency - ff.inconsistency) / total < 0.35:
                cap("moderate", "a false-flag hypothesis for the same actor is not decisively rejected.")

        ff_ind = self._false_flag_indicators()
        if ff_ind:
            cap("moderate", "false-flag / planted-marker indicators are present; active deception limits confidence.")

        return Assessment(
            question=self.question,
            ranking=ranking,
            matrix=m,
            diagnostic_weights=weights,
            confidence=conf,
            likelihood_phrase=_PHRASES[conf],
            rationale=rationale,
            false_flag_indicators=ff_ind,
            what_would_change=self._sensitivity(top, second, m, weights) if self.sensitivity else [],
        )

    def _false_flag_indicators(self) -> list[str]:
        out: list[str] = []
        spoof_targets = {p for e in self.evidence if e.spoofable for p in e.points_to}
        if len(spoof_targets) > 1:
            out.append(f"Spoofable markers point at multiple actors ({', '.join(sorted(spoof_targets))}) - planted-marker pattern.")
        for aid in sorted(spoof_targets):
            actor = self._actors.get(aid)
            if not actor:
                continue
            contra = [e.id for e in self.evidence if not e.spoofable and rate_actor(e, actor, self.kb).value < 0]
            if contra:
                out.append(f"Markers implicate {actor.name}, but hard evidence {contra} contradicts that actor.")
        return out

    def _sensitivity(self, top: HypothesisScore, second: HypothesisScore, m, weights) -> list[str]:
        out: list[str] = []
        for e in self.evidence:
            rest = [x for x in self.evidence if x.id != e.id]
            if not rest:
                continue
            new_rank, _, _ = self._score(rest)
            if new_rank[0].hypothesis.id != top.hypothesis.id:
                out.append(f"Discrediting {e.id} ({e.description}) would make '{new_rank[0].hypothesis.label}' lead.")
        drivers = sorted(
            (e for e in self.evidence if m[e.id][second.hypothesis.id].value < 0),
            key=lambda e: m[e.id][second.hypothesis.id].value * weights[e.id],
        )[:3]
        for e in drivers:
            out.append(f"{e.id} is a key reason '{second.hypothesis.label}' is rejected; re-verify its source ({e.reliability}{e.credibility}).")
        if not out:
            out.append("No single evidence item flips the conclusion; new independent evidence would be required.")
        return out


def render_matrix(a: Assessment, evidence: list[Evidence]) -> str:
    hyps = [s.hypothesis for s in a.ranking]
    head = f"{'evidence':<10}{'w':>6} " + " ".join(f"{h.id[:14]:>14}" for h in hyps)
    lines = [head, "-" * len(head)]
    for e in evidence:
        row = a.matrix[e.id]
        tag = "*" if e.spoofable else " "
        lines.append(f"{e.id + tag:<10}{a.diagnostic_weights[e.id]:>6.2f} " + " ".join(f"{row[h.id].name:>14}" for h in hyps))
    lines.append("-" * len(head))
    lines.append(f"{'INCONS.':<16} " + " ".join(f"{s.inconsistency:>14.2f}" for s in a.ranking))
    lines.append("(* = spoofable evidence, down-weighted)")
    return "\n".join(lines)
