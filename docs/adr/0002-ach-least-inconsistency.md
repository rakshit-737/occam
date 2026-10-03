# ADR 0002: ACH ranks by least inconsistency and applies confidence caps

- Status: accepted
- Date: 2026-09-26

## Context
Naive attribution counts matching TTPs and names the closest actor, which is what our similarity baseline does. Two failures follow. The method always names someone, even when the real actor is untracked. It is also easy to steer with planted artefacts (code overlap, language settings, compile-time metadata, claims), as the Olympic Destroyer case showed. Heuer's ACH counters this by focusing on the evidence that *disconfirms* each hypothesis.

## Decision
- Hypotheses are one per candidate actor, plus a mandatory **unknown actor**, plus one **false flag: X was framed** for every actor that a spoofable marker points at.
- Cells use CC/C/N/I/II. The rules only propose them, and an analyst can override any cell.
- Each row is weighted by Admiralty reliability and credibility times *diagnosticity* (the spread of ratings across hypotheses). Non-diagnostic rows weigh 0, and spoofable rows are multiplied by 0.5.
- On real ATT&CK data, diagnosticity is data-driven. A technique used by ≥30% of groups is non-diagnostic (N). One used by ≤3 groups is rated CC when it matches. A technique that matches only at the parent level is N.
- **Ranking is by least weighted inconsistency.** Support is reported but never used for ranking. Ties go to the more conservative conclusion: unknown, then false flag, then a named actor.
- Confidence comes from the relative margin and the number of diagnostic items, and then **caps** apply:
  - LOW if most support is spoofable.
  - At most MODERATE for unknown or false-flag conclusions.
  - At most MODERATE when a same-actor false-flag hypothesis is not decisively rejected, or when planted-marker indicators exist.
- Confidence grades map to ICD-203 band midpoints for scoring: high 0.875, moderate 0.675, low 0.5.

## Consequences
- The engine is deliberately conservative. The benchmark (`results/attribution.md`) shows the trade-off:
  - ACH names the true group less often than the similarity baseline in the closed world (0.30 vs 0.53).
  - It declines correctly far more often than the never-abstaining matcher when the true group is untracked (0.46 vs 0.00).
  - It almost never names the framed group under planted markers (1% vs 88%).

> **Note (2026-10-03, after 1.1.0).** Two of these consequences need qualifying against the later benchmark (`results/falseflag.md`, `results/attribution.md`). First, a cosine-threshold baseline that *can* abstain declines more: 0.945 with its threshold cross-fitted for closed + open accuracy, and 0.934 when the threshold is matched to ACH's closed-world accuracy. Second, the overconfident-error rate (wrong at stated p >= 0.8) is not zero: it is 0.000 / 0.004 / 0.000 in the closed / open / false-flag settings, which is 1 of 274 open-world answers. The confidence caps nearly guarantee such a low rate, so it is not evidence of better calibration. Under one setting-agnostic calibration map ACH's pooled Brier score is worse than the matcher's (0.214 vs 0.160).
- Because least-inconsistency ignores support, large profiles have an advantage: they have fewer "absent" cells. The optional similarity shortlist (ADR 0005) reduces the candidate set, which partly mitigates this.
