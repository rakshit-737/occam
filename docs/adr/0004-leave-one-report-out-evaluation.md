# ADR 0004: Evaluate attribution by leaving one report out of ATT&CK

- Status: accepted
- Date: 2026-09-26

## Context
No public dataset pairs incidents with ground-truth attribution at scale. ATT&CK does something close: every `uses` relationship between a group and a technique or software cites the public report it came from. Evaluating against the full profiles would leak, because the incident's own techniques would already be in the true group's profile.

## Decision
- An **incident** is a (group, cited report) pair with at least 4 techniques or software. At most 3 incidents are taken per group, to limit dominance by heavily reported groups. That gives 274 incidents from 103 groups.
- For each incident, `HoldoutWorld` removes every item of the group that is supported **only** by that report, and decrements the group-usage counts used for rarity. Items also cited by other reports stay, because the analyst would know them from those reports.
- Three settings:
  - **closed**: the true group is a candidate.
  - **open**: the true group is removed, so the correct answer is to decline.
  - **false_flag**: 3 spoofable markers frame a random other group. A correct answer names the true group or concludes that the framed group was framed.
- Every attributor states the probability that its conclusion is correct. We report Brier and ECE with 95% bootstrap CIs, plus a histogram-binning recalibration cross-fitted over a 2-fold *group* split. The recalibration shows how much of each method's error is miscalibration rather than ranking.

## Consequences
- The benchmark is reproducible from the public ATT&CK bundle alone (`scripts/bench_attribution.py`).
- Incidents are *reported* slices of activity, not raw telemetry. Real incidents are noisier, as the APTnotes end-to-end benchmark shows.
- Planted markers are synthetic evidence rows. The test measures how the reasoning handles deception, not how well deception gets detected in raw artefacts.
