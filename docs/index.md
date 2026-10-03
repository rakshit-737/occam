# OCCAM

**Contribution:** an open, leakage-controlled benchmark for attack attribution under *planted*, *authentic* and *mimicked* false-flag evidence, plus an auditable ACH engine measured on it. The numbers below include where ACH loses.

[![The OCCAM workbench](figures/workbench.png)](https://rakshit-737.github.io/occam-cti-attribution/demo/)

[Try the live demo](https://rakshit-737.github.io/occam-cti-attribution/demo/){ .md-button .md-button--primary } [How it works](how-it-works.md){ .md-button } [Evaluation](evaluation.md){ .md-button } [Preprint (PDF)](https://rakshit-737.github.io/occam-cti-attribution/preprint.pdf){ .md-button }

OCCAM extracts ATT&CK techniques, software and IOCs from report prose, and anchors every hit to its source span. It clusters activity into campaigns. It then runs Heuer's Analysis of Competing Hypotheses with mandatory *unknown actor* and *false flag* hypotheses. Confidence goes **down** when the case rests on evidence that is cheap to plant, and an analyst can override every cell of the matrix.

## Research question and answer

*Does automated ACH with mandatory disconfirming-evidence weighting give better-calibrated, less overconfident attribution than naive TTP-similarity matching, especially under false flags?*

**Mostly no.** ACH's remaining advantage is an inspectable matrix with span-anchored evidence. That is a design property and is not measured here.

- **Calibration is worse overall.** Under one setting-agnostic calibration map, the pooled Brier score is 0.214 for ACH and 0.160 for the marker-trusting similarity matcher (paired difference +0.031 to +0.080, for an equal mix of closed, open and planted-marker incidents). ACH is better only in the closed world.
- **Overconfidence.** Under planted markers, ACH's capped grades are never wrong at stated p ≥ 0.8 (0/274). The matcher's softmax is wrong at that level 70.8% of the time. After one recalibration, neither method makes such errors (1/822 vs 0/822).
- **Planted markers.** ACH names the framed group 1.1% of the time, against 88% for the matcher. A baseline that ignores spoofable rows is never framed, and a consistency gate is correct more often.
- **Mimicry.** ACH is framed less often than IDF coverage (27.0% vs 32.1%) but is correct less often (17.9% vs 28.8%; paired −16.0 to −6.6 points).
- **Abstention.** An abstaining cosine-threshold baseline declines more on untracked actors at the same closed-world accuracy (93.4% vs 46.0%).

## Try it in 60 seconds

```bash
# browser: https://rakshit-737.github.io/occam-cti-attribution/demo/
docker run --rm -p 127.0.0.1:8000:8000 ghcr.io/rakshit-737/occam-cti-attribution:latest   # http://127.0.0.1:8000/
git clone --depth 1 https://github.com/rakshit-737/occam-cti-attribution && cd occam && python -m pip install -e . && occam demo
```

## Headline results

The test set is 274 held-out ATT&CK incidents from 103 groups. Brackets are 95% group-cluster bootstrap intervals. † marks a rate of exactly 0, shown with a Wilson interval that uses the 103 groups as its sample size. Each row links to its result file. All rows come from bench run [37093689060](https://github.com/rakshit-737/occam-cti-attribution/actions/runs/37093689060) (commit `09cde53`). Full tables and methods are on [Evaluation](evaluation.md).

| Question | OCCAM ACH | Best simple baseline | Naive TTP-similarity | Source |
| --- | --- | --- | --- | --- |
| Framed group named, 3 planted spoofable markers | 1.1% [0.0–2.6] | **0%** [0.0–3.6]† (ignore spoofable rows) | 88.0% [82.3–93.3] | [falseflag](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/falseflag.md) |
| Correct under planted markers (true group or detected frame) | 73.4% [66.9–79.6] | **92.0%** [88.4–95.2] (consistency gate) | 11.3% [6.4–16.9] | [falseflag](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/falseflag.md) |
| Genuine markers called a frame-up | 18.6% [13.8–24.4] | 0% [0.0–3.6]† | 0% [0.0–3.6]† | [falseflag](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/falseflag.md) |
| Framed group named under TTP **mimicry** | **27.0%** [21.3–33.5] | 32.1% [25.4–39.2] (IDF coverage) | 76.3% [70.9–81.8] | [falseflag](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/falseflag.md) |
| Correct under TTP mimicry | 17.9% [12.2–23.8] | **28.8%** [21.9–35.8] (IDF coverage) | 21.2% [15.5–27.0] | [falseflag](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/falseflag.md) |
| Correct "unknown" when the true group is untracked | 46.0% [39.3–53.1] | **93.4%** [90.6–96.1] (cosine threshold matched to ACH's closed-world accuracy) | 0% [0.0–3.6]† | [falseflag](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/falseflag.md) |
| Closed-world top-1 | 29.9% [22.9–37.1] | **53.3%** [45.3–60.8] | 53.3% [45.3–60.8] | [falseflag](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/falseflag.md) |
| Brier, one setting-agnostic map, three settings pooled (lower is better) | 0.214 [0.202–0.226] | 0.214 [0.203–0.226] (abstaining baseline) | **0.160** [0.141–0.178] (ACH minus it: +0.031 to +0.080) | [falseflag](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/falseflag.md) |

Extraction and reproduction use their own metrics, so they have a separate table.

| Task | Result | Comparison | Source |
| --- | --- | --- | --- |
| rcATT tactic micro F0.5 | released code reproduces 64.82 ± 3.44 | paper: 65.38 ± 2.87 (Table 4) | [rcatt_reproduction](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/rcatt_reproduction.md) |
| rcATT technique micro F0.5 (197 techniques) | released code reproduces 36.33 ± 1.39 | paper: 35.02 ± 5.32 (Table 4) | [rcatt_reproduction](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/rcatt_reproduction.md) |
| TRAM2 document micro-F1, TF-IDF + LR | 0.710 [0.680–0.738] | keywords: 0.388 [0.329–0.434] | [extraction](https://github.com/rakshit-737/occam-cti-attribution/blob/main/results/extraction.md) |

The ± values are SDs over 5 folds: they describe spread, not confidence. The TRAM2 brackets are document-bootstrap 95% intervals.

!!! warning "Decision support, lab use only"
    Attribution has diplomatic, legal and human consequences. Results about real ATT&CK groups are benchmark artefacts, not findings. OCCAM reads text and JSON only; it never contacts infrastructure or downloads malware.
