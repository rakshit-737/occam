# OCCAM

**Auditable threat-intel reasoning.** OCCAM extracts ATT&CK TTPs from report prose (every hit anchored to its source span), clusters activity into campaigns on a Diamond-model graph, and runs Heuer's Analysis of Competing Hypotheses (ACH) with mandatory *unknown actor* and *false flag* hypotheses. Confidence is graded to go **down** when the case rests on evidence that is cheap to plant.

> The rules and models propose; the ACH matrix and the analyst decide.

[Try the static workbench demo](demo/index.html){ .md-button .md-button--primary } [Getting started](getting-started.md){ .md-button }

## Headline results (real data)

| Question | OCCAM | Baseline |
| --- | --- | --- |
| Framed group named when 3 planted markers point at it (274 held-out ATT&CK incidents) | **1.1%** | 88.0% (TTP-similarity) |
| Wrong at stated p >= 0.8 under false flags | **0.0%** | 70.8% |
| Correct "unknown" when the true group is untracked | **46%** (64% with shortlist) | 0% |
| Closed-world top-1 attribution | 30% (40% with the opt-in support-aware ranking) | **53%** |
| Closed-world Brier with the learned grade map (cross-fitted) | **0.156** | 0.179 |
| TTP extraction, document micro-F1 (TRAM2, 5-fold) | **0.710** | 0.387 (keyword) |
| Campaign clustering ARI (held-out groups) | **0.249** | 0.107 (single linkage) |

The trade-off is measured, not hidden: mandatory disconfirming-evidence weighting makes attribution far harder to steer with false flags, and costs top-1 accuracy when nobody is lying. See [Benchmarks](benchmarks.md) and [Limitations](limitations.md).

!!! warning "Decision support, lab use only"
    Attribution has diplomatic, legal and human consequences. Results about real ATT&CK groups are benchmark artefacts, not findings. OCCAM reads text and JSON only; it never contacts infrastructure or downloads malware.
