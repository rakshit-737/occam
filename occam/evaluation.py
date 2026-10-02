"""Attribution benchmark on real MITRE ATT&CK group usage.

Protocol -- *leave-one-report-out*:

Every ATT&CK ``uses`` relationship of a group cites the public report(s) it was
taken from. For each (group, cited report) pair with at least ``min_items``
techniques/software, the items cited by that report form one held-out
**incident**. The group's profile is rebuilt *without* any item supported only
by that report (and group-usage counts are decremented accordingly), so the
attributor never sees the incident it is asked to attribute.

Three settings, each asking a different question of the attributor:

* ``closed``  -- the true group is in the candidate set; correct = name it.
* ``open``    -- the true group is removed from the candidate set (an
  untracked actor); correct = decline to name anyone (unknown / false-flag).
* ``false_flag`` -- as ``closed`` plus ``n_markers`` spoofable markers
  (code overlap, metadata, language, claim) planted to frame a different
  random group. The stated conclusion is correct if it names the true group
  *or* concludes "false flag: <framed group> was framed" (which is true).
  Naming the framed group is a *framed* error; ``named_true`` counts only
  conclusions that name the real group.

Extra settings (opt-in via ``settings=``), added after the round-3 audit:

* ``authentic`` -- control for ``false_flag``: the same spoofable markers
  point at the TRUE group (genuine code/language overlap). Correct = name the
  true group; concluding "the true group was framed" is a *false alarm*
  (``detected_frame`` then counts false alarms).
* ``mimicry`` -- the adversary copies ``n_markers`` of the framed group's
  rarest techniques/software as ordinary *hard* (non-spoofable) evidence, the
  harder false flag in which nothing is pre-typed as spoofable.
  Scored as ``false_flag``.

Stated probabilities are compared with outcomes via Brier score and ECE.
:func:`crossfit_calibrate` additionally re-maps stated probabilities with
histogram binning fitted on the *other* half of the groups (2-fold, split by
group so no actor is in both halves), for a calibrated comparison.
"""
from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from .attack import AttackKB
from .attribution import Attribution, evidence_from_items, planted_markers
from .knowledge import AttackData
from .metrics import brier, ece
from .models import ActorProfile

SETTINGS = ("closed", "open", "false_flag")
ALL_SETTINGS = ("closed", "open", "false_flag", "authentic", "mimicry")


@dataclass
class Incident:
    group: str
    reference: str
    items: list[str]
    #: every citation that belongs to this incident (a campaign cites several
    #: reports); defaults to ``(reference,)``
    refs: tuple[str, ...] = ()
    kind: str = "report"  # report | campaign

    @property
    def ref_set(self) -> set[str]:
        return set(self.refs) or {self.reference}


@dataclass
class Outcome:
    incident: Incident
    setting: str
    attribution: Attribution
    correct: bool
    framed: bool = False
    top5: bool = False
    named_true: bool = False
    detected_frame: bool = False
    #: the group the markers / mimicked items point at (None in closed / open)
    marker_target: str | None = None


def incidents(data: AttackData, min_items: int = 4, max_per_group: int | None = None,
              min_profile: int = 8) -> list[Incident]:
    """One incident per (group, cited report) with >= ``min_items`` items.

    Groups whose remaining profile would have fewer than ``min_profile`` items
    are skipped (nothing meaningful to attribute against).
    """
    by_group_ref: dict[tuple[str, str], set[str]] = defaultdict(set)
    group_items: dict[str, set[str]] = defaultdict(set)
    for u in data.uses:
        if u.source not in data.groups:
            continue
        group_items[u.source].add(u.target)
        for r in u.references:
            by_group_ref[(u.source, r)].add(u.target)
    out = []
    per_group: dict[str, int] = defaultdict(int)
    for (g, r), items in sorted(by_group_ref.items()):
        if len(items) < min_items:
            continue
        if max_per_group is not None and per_group[g] >= max_per_group:
            continue
        remaining = group_items[g] - _only_supported_by(data, g, r)
        if len(remaining) < min_profile:
            continue
        per_group[g] += 1
        out.append(Incident(g, r, sorted(items)))
    return out


def _only_supported_by(data: AttackData, group: str, ref: str) -> set[str]:
    """Items of ``group`` whose every citation is ``ref`` (removed when held out)."""
    support: dict[str, set[str]] = defaultdict(set)
    for u in data.uses:
        if u.source == group:
            support[u.target] |= set(u.references) or {"<uncited>"}
    return {x for x, refs in support.items() if refs == {ref}}


@dataclass
class HoldoutWorld:
    """Profiles + KB with one incident's evidence removed from its group."""

    data: AttackData
    base_profiles: dict[str, ActorProfile]
    base_kb: AttackKB
    _support: dict[str, dict[str, set[str]]] = field(default_factory=dict)

    @classmethod
    def build(cls, data: AttackData) -> HoldoutWorld:
        kb = data.to_kb()
        profiles = {p.id: p for p in data.actor_profiles()}
        support: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for u in data.uses:
            if u.source in data.groups:
                support[u.source][u.target] |= set(u.references) or {"<uncited>"}
        return cls(data, profiles, kb, support)

    def world(self, inc: Incident, drop_group: bool = False) -> tuple[list[ActorProfile], AttackKB]:
        g = inc.group
        mine = inc.ref_set
        removed = {x for x, refs in self._support[g].items() if refs <= mine}
        if drop_group:
            removed = set(self._support[g])
        usage = dict(self.base_kb.usage)
        for x in removed:
            usage[x] = max(0, usage.get(x, 0) - 1)
        n_groups = self.base_kb.n_groups - (1 if drop_group else 0)
        kb = AttackKB(self.base_kb.techniques, self.base_kb.tools, usage, n_groups,
                      self.base_kb.common_frac, self.base_kb.rare_max)
        profiles = []
        for pid, p in self.base_profiles.items():
            if pid == g:
                if drop_group:
                    continue
                p = ActorProfile(p.id, p.name, [t for t in p.techniques if t not in removed],
                                 [t for t in p.tools if t not in removed], description=p.description)
            profiles.append(p)
        return profiles, kb


Factory = Callable[[list[ActorProfile], AttackKB], object]


def campaign_incidents(data: AttackData, min_items: int = 4, min_profile: int = 8) -> list[Incident]:
    """One incident per ATT&CK *campaign* attributed to a group.

    The incident is everything ATT&CK records the campaign as using. When it is
    held out, every item of the attributed group that is cited *only* by the
    campaign's own references is removed from the group's profile, so the
    campaign cannot be matched against a copy of itself.
    """
    camp_items: dict[str, set[str]] = defaultdict(set)
    camp_refs: dict[str, set[str]] = defaultdict(set)
    for u in data.uses:
        if u.source in data.campaigns:
            camp_items[u.source].add(u.target)
            camp_refs[u.source] |= set(u.references)
    support: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for u in data.uses:
        if u.source in data.groups:
            support[u.source][u.target] |= set(u.references) or {"<uncited>"}
    out = []
    for cid, gid in sorted(data.attributed_to.items()):
        items = camp_items.get(cid, set())
        if len(items) < min_items or gid not in data.groups:
            continue
        refs = camp_refs[cid] - {"mitre-attack"}
        remaining = {x for x, r in support[gid].items() if not r <= refs}
        if len(remaining) < min_profile:
            continue
        out.append(Incident(gid, cid, sorted(items), tuple(sorted(refs)), kind="campaign"))
    return out


def temporal_incidents(old: AttackData, new: AttackData, min_items: int = 4, max_per_group: int | None = 3,
                       min_profile: int = 8) -> list[Incident]:
    """Incidents that only exist in a *later* ATT&CK release.

    Profiles come from ``old``; incidents are (a) campaigns of ``new`` that are
    absent from ``old`` and (b) (group, report) pairs of ``new`` whose report
    ``old`` never cited for that group. Only groups already tracked in ``old``
    (with a profile of >= ``min_profile`` items) are kept: the question is
    whether yesterday's knowledge attributes tomorrow's activity.
    """
    old_idx = old._usage_index()
    tracked = {g for g in old.groups if len(old_idx.get(g, ())) >= min_profile}
    old_refs: dict[str, set[str]] = defaultdict(set)
    for u in old.uses:
        if u.source in old.groups:
            old_refs[u.source] |= set(u.references)
    out = [Incident(i.group, i.reference, i.items, i.refs, kind="campaign")
           for i in campaign_incidents(new, min_items=min_items, min_profile=0)
           if i.reference not in old.campaigns and i.group in tracked]
    by_group_ref: dict[tuple[str, str], set[str]] = defaultdict(set)
    for u in new.uses:
        if u.source in tracked:
            for r in u.references:
                if r not in old_refs[u.source]:
                    by_group_ref[(u.source, r)].add(u.target)
    per_group: dict[str, int] = defaultdict(int)
    for (g, r), items in sorted(by_group_ref.items()):
        if len(items) >= min_items and (max_per_group is None or per_group[g] < max_per_group):
            per_group[g] += 1
            out.append(Incident(g, r, sorted(items)))
    return out


@dataclass
class StaticWorld:
    """Fixed profiles + KB (temporal split: nothing to hold out, the past simply
    does not contain the future incident). ``drop_group`` removes the group."""

    base_profiles: dict[str, ActorProfile]
    base_kb: AttackKB

    @classmethod
    def build(cls, data: AttackData) -> StaticWorld:
        return cls({p.id: p for p in data.actor_profiles()}, data.to_kb())

    def world(self, inc: Incident, drop_group: bool = False) -> tuple[list[ActorProfile], AttackKB]:
        profiles = [p for pid, p in self.base_profiles.items() if not (drop_group and pid == inc.group)]
        return profiles, self.base_kb


def evaluate(data: AttackData, factories: dict[str, Factory], settings: Iterable[str] = SETTINGS,
             min_items: int = 4, max_per_group: int | None = 3, n_markers: int = 3, seed: int = 7,
             limit: int | None = None, progress: Callable[[int, int], None] | None = None,
             incs: list[Incident] | None = None, hw=None) -> dict[str, dict[str, list[Outcome]]]:
    """Run every attributor on every incident in every setting.

    By default the incidents are :func:`incidents` of ``data`` in a
    :class:`HoldoutWorld`; pass ``incs`` / ``hw`` for campaign or temporal
    protocols.
    """
    hw = hw or HoldoutWorld.build(data)
    if incs is None:
        incs = incidents(data, min_items=min_items, max_per_group=max_per_group)
    if limit:
        incs = random.Random(seed).sample(incs, min(limit, len(incs)))
    rng = random.Random(seed)
    group_ids = sorted(hw.base_profiles)
    frame_for = {id(i): rng.choice([g for g in group_ids if g != i.group]) for i in incs}
    results: dict[str, dict[str, list[Outcome]]] = {n: {s: [] for s in settings} for n in factories}
    for k, inc in enumerate(incs):
        for setting in settings:
            profiles, kb = hw.world(inc, drop_group=(setting == "open"))
            ev = evidence_from_items(inc.items, kb)
            framed = target = None
            if setting == "false_flag":
                framed = target = frame_for[id(inc)]
                ev = ev + planted_markers(framed, n_markers)
            elif setting == "authentic":
                target = inc.group
                ev = ev + planted_markers(inc.group, n_markers)
            elif setting == "mimicry":
                framed = target = frame_for[id(inc)]
                ev = evidence_from_items(sorted(set(inc.items) | set(mimicry_items(profiles, kb, framed, inc.items, n_markers))), kb)
            elif setting not in ("closed", "open"):
                raise ValueError(f"unknown setting {setting!r}")
            for name, make in factories.items():
                att: Attribution = make(profiles, kb).attribute(ev)
                if setting == "authentic":
                    detected = att.flagged == inc.group      # a false alarm
                else:
                    detected = bool(framed) and att.flagged == framed
                if setting == "open":
                    ok = att.leading is None
                elif setting == "authentic":
                    ok = att.leading == inc.group
                else:
                    ok = att.leading == inc.group or detected
                results[name][setting].append(Outcome(
                    inc, setting, att, ok,
                    framed=bool(framed) and att.leading == framed,
                    top5=inc.group in att.ranked_actors[:5],
                    named_true=att.leading == inc.group,
                    detected_frame=detected,
                    marker_target=target,
                ))
        if progress:
            progress(k + 1, len(incs))
    return results


def mimicry_items(profiles: list[ActorProfile], kb: AttackKB, framed: str, have: list[str], n: int) -> list[str]:
    """The ``n`` rarest (fewest ATT&CK groups) items of ``framed`` that the
    incident does not already contain -- what a careful imitator would copy."""
    prof = next(p for p in profiles if p.id == framed)
    cand = sorted((set(prof.techniques) | set(prof.tools)) - set(have))
    return sorted(cand, key=lambda x: (kb.usage.get(x, 0), x))[:n]


def _fold(group: str) -> int:
    return int(group.lstrip("G") or 0) % 2


def crossfit_calibrate(outcomes: list[Outcome], bins: int = 10, prior: float = 1.0) -> list[float]:
    """Histogram-binning recalibration, 2-fold cross-fitted by group.

    Each outcome's stated probability is replaced by the (Laplace-smoothed)
    empirical accuracy of its probability bin in the *other* fold, so no
    incident is calibrated with its own label or its own group's labels.
    """
    def b(p: float) -> int:
        return min(int(p * bins), bins - 1)

    stats = {f: [[0.0, 0.0] for _ in range(bins)] for f in (0, 1)}
    for o in outcomes:
        s = stats[_fold(o.incident.group)][b(o.attribution.probability)]
        s[0] += o.correct
        s[1] += 1
    base = {f: (sum(x[0] for x in stats[f]) + prior) / (sum(x[1] for x in stats[f]) + 2 * prior) for f in (0, 1)}
    out = []
    for o in outcomes:
        other = 1 - _fold(o.incident.group)
        hit, n = stats[other][b(o.attribution.probability)]
        out.append((hit + prior * base[other]) / (n + prior))
    return out


def crossfit_grade_calibrate(outcomes: list[Outcome]) -> list[float]:
    """Replace each stated probability with the learned probability of its ACH
    grade, fitted on the *other* group fold (see :class:`occam.calibration.GradeCalibrator`)."""
    from .calibration import GradeCalibrator

    cal = {}
    for f in (0, 1):
        tr = [o for o in outcomes if _fold(o.incident.group) != f]
        cal[f] = GradeCalibrator().fit([o.attribution.confidence for o in tr], [o.correct for o in tr])
    return [cal[_fold(o.incident.group)][o.attribution.confidence] for o in outcomes]


def summarize(outcomes: list[Outcome], probs: list[float] | None = None) -> dict[str, float]:
    n = len(outcomes) or 1
    probs = [o.attribution.probability for o in outcomes] if probs is None else probs
    corr = [o.correct for o in outcomes]
    named = [o for o in outcomes if o.attribution.leading is not None]
    return {
        "n": len(outcomes),
        "accuracy": sum(corr) / n,
        "top5": sum(o.top5 for o in outcomes) / n,
        "named_rate": len(named) / n,
        "precision_when_named": (sum(o.correct for o in named) / len(named)) if named else 0.0,
        "framed_rate": sum(o.framed for o in outcomes) / n,
        "named_true": sum(o.named_true for o in outcomes) / n,
        "detected_frame": sum(o.detected_frame for o in outcomes) / n,
        "mean_stated_prob": sum(probs) / n,
        "brier": brier(probs, corr),
        "ece": ece(probs, corr),
        "overconfident_errors": sum(1 for o, p in zip(outcomes, probs) if not o.correct and p >= 0.8) / n,
        "high_conf_rate": sum(o.attribution.confidence == "high" for o in outcomes) / n,
    }
