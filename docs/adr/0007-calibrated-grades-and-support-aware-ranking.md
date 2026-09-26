# 0007 Learned grade map and an optional support-aware ranking

**Status:** accepted

## Context
The v0.2 benchmark showed two weaknesses. ACH's ICD-203 midpoint probabilities were over-optimistic (closed-world ECE 0.26). Least-inconsistency also favours groups with large ATT&CK profiles, so closed-world top-1 was 30% against 53% for naive similarity.

## Decision
- Ship `occam.calibration.GradeCalibrator`: a Beta-smoothed, monotone (pooled adjacent violators) accuracy per grade. It is fitted on the leave-one-report-out outcomes and saved to `results/grade_calibration.json`. It changes stated probabilities only, never the ranking. The benchmark reports it cross-fitted over a 2-fold group split.
- Add `ranking_rule="balanced"` to `ACHEngine`: score = inconsistency + 0.5 x non-spoofable support. Pure Heuer stays the default.

## Consequences
- Calibrated closed-world Brier is 0.156 (from 0.238), below the baseline's 0.179.
- Support-aware ranking lifts closed-world top-1 to 40% and false-flag correctness to 89%. Open-world correct-decline collapses from 46% to 5.5%, because the unknown hypothesis never receives support. Declining when the actor is untracked is a core safety property, so the variant stays opt-in.
