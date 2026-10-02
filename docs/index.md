# OCCAM

**Contribution:** an open, leakage-controlled benchmark for attack attribution under *planted*, *authentic* and *mimicked* false-flag evidence, and an auditable ACH engine measured on it. Resisting planted markers turns out to come from typing evidence as spoofable; ACH's distinct gain is under TTP **mimicry** (framed group named 27% vs 76% for TTP-similarity) and in declining on untracked actors, at a measured cost in closed-world accuracy.

[![The OCCAM workbench](figures/workbench.png)](https://rakshit-737.github.io/occam/demo/)

[Try the live demo](https://rakshit-737.github.io/occam/demo/){ .md-button .md-button--primary } [How it works](how-it-works.md){ .md-button } [Evaluation](evaluation.md){ .md-button }

OCCAM extracts ATT&CK techniques, software and IOCs from report prose (every hit anchored to its source span), clusters activity into campaigns, and runs Heuer's Analysis of Competing Hypotheses with mandatory *unknown actor* and *false flag* hypotheses. Confidence goes **down** when the case rests on evidence that is cheap to plant, and every cell of the matrix can be overridden by an analyst.

## Try it in 60 seconds

```bash
# browser: https://rakshit-737.github.io/occam/demo/
docker run --rm -p 127.0.0.1:8000:8000 ghcr.io/rakshit-737/occam:latest   # http://127.0.0.1:8000/
git clone --depth 1 https://github.com/rakshit-737/occam && cd occam && python -m pip install -e . && occam demo
```

## Headline results

274 held-out ATT&CK incidents from 103 groups; full tables, 95% intervals and methodology are on [Evaluation](evaluation.md).

| Question | OCCAM ACH | Best simple baseline | Naive TTP-similarity |
| --- | --- | --- | --- |
| Framed group named, 3 planted spoofable markers | 1.1% | **0%** (ignore spoofable rows) | 88.0% |
| Correct under planted markers (true group or detected frame) | 73.4% | **92.0%** (consistency gate) | 11.3% |
| Genuine markers called a frame-up | 18.6% | 0% | 0% |
| Framed group named under TTP **mimicry** | **27.0%** | 32.1% (IDF coverage) | 76.3% |
| Correct "unknown" when the true group is untracked | 46.0% | 94.5% (cosine threshold; closed-world accuracy drops to 27%) | 0% |
| Closed-world top-1 | 29.9% | **53.3%** | 53.3% |
| rcATT tactic micro F0.5, paper vs our reproduction | | 65.38 vs 64.63 | |
| TRAM2 document micro-F1 (TF-IDF + LR) | **0.710 ± 0.023** | 0.388 (keywords) | |

!!! warning "Decision support, lab use only"
    Attribution has diplomatic, legal and human consequences. Results about real ATT&CK groups are benchmark artefacts, not findings. OCCAM reads text and JSON only; it never contacts infrastructure or downloads malware.
