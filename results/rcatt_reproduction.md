### Reproduction of rcATT (Legoy et al. 2020) report-level TTP classification

1490 reports, 5-fold CV (KFold, shuffle, seed 42, as in the released code), binary relevance; mean ± SD over folds (dispersion of the 5 folds, not a confidence interval), percent.

*Source: GitHub Actions run [37093689060](https://github.com/rakshit-737/occam-cti-attribution/actions/runs/37093689060), commit `09cde53`, 2026-10-03T03:35:46+00:00.*

#### Tactics (12 labels)

| Source | Micro P | Micro R | Micro F0.5 | Macro P | Macro R | Macro F0.5 |
|---|---|---|---|---|---|---|
| rcATT paper (Legoy et al. 2020, arXiv:2004.14322v1, Table 4 'Inde.' rows; same means in Tables 2-3, TF-IDF BR Linear SVC) | 65.64 ± 3.76 | 64.69 ± 3.00 | 65.38 ± 2.87 | 60.26 ± 3.20 | 58.50 ± 3.68 | 59.47 ± 2.29 |
| Reproduction, released rcATT pipeline (stemmed/lemmatised tokens, balanced class weights) | 64.97 ± 3.88 | 64.31 ± 2.32 | 64.82 ± 3.44 | 61.52 ± 4.93 | 58.00 ± 2.86 | 60.32 ± 4.23 |
| Released pipeline without class weighting | 71.37 ± 4.41 | 52.28 ± 2.10 | 66.50 ± 3.58 | 68.66 ± 6.72 | 42.29 ± 2.10 | 57.45 ± 4.48 |
| Pipeline as the paper text describes it (default tokens, no class weighting) | 71.81 ± 3.77 | 52.00 ± 2.14 | 66.71 ± 3.17 | 69.25 ± 6.11 | 41.82 ± 2.05 | 57.46 ± 3.98 |
| Paper-text pipeline with balanced class weights | 65.20 ± 4.24 | 63.93 ± 1.91 | 64.93 ± 3.71 | 61.47 ± 5.11 | 57.38 ± 2.52 | 60.14 ± 4.36 |
| OCCAM TF-IDF + LR, same folds | 61.07 ± 3.51 | 65.41 ± 3.14 | 61.88 ± 3.29 | 57.65 ± 5.15 | 59.50 ± 4.55 | 57.39 ± 5.03 |

| Effect on micro F0.5 (same 5 folds) | Fold-paired difference, mean ± SD |
|---|---|
| class weighting, released tokens | -1.67 ± 0.87 |
| class weighting, paper-text tokens | -1.79 ± 0.92 |
| rcATT tokenisation, balanced weights | -0.10 ± 0.46 |
| rcATT tokenisation, no weighting | -0.22 ± 0.78 |
| both (released minus paper text) | -1.89 ± 0.60 |

#### Techniques (197 labels)

| Source | Micro P | Micro R | Micro F0.5 | Macro P | Macro R | Macro F0.5 |
|---|---|---|---|---|---|---|
| rcATT paper (Legoy et al. 2020, arXiv:2004.14322v1, Table 4 'Inde.' rows; same means in Tables 2-3, TF-IDF BR Linear SVC) | 37.18 ± 6.75 | 29.79 ± 5.91 | 35.02 ± 5.32 | 28.84 ± 6.90 | 22.67 ± 5.94 | 25.06 ± 6.09 |
| Reproduction, released rcATT pipeline (stemmed/lemmatised tokens, balanced class weights) | 39.32 ± 2.02 | 27.95 ± 1.54 | 36.33 ± 1.39 | 33.99 ± 2.15 | 22.97 ± 1.48 | 28.86 ± 1.62 |
| Released pipeline without class weighting | 59.69 ± 2.38 | 10.33 ± 0.90 | 30.44 ± 1.48 | 22.27 ± 0.95 | 8.21 ± 0.96 | 14.66 ± 1.07 |
| Pipeline as the paper text describes it (default tokens, no class weighting) | 59.40 ± 3.09 | 9.70 ± 0.98 | 29.28 ± 2.05 | 20.91 ± 1.30 | 7.62 ± 1.00 | 13.64 ± 1.27 |
| Paper-text pipeline with balanced class weights | 39.86 ± 2.52 | 26.14 ± 1.22 | 36.06 ± 1.93 | 33.38 ± 1.58 | 21.40 ± 1.30 | 27.84 ± 1.34 |
| OCCAM TF-IDF + LR, same folds | 37.76 ± 2.12 | 24.81 ± 1.98 | 34.18 ± 2.10 | 15.93 ± 2.84 | 10.33 ± 1.13 | 12.94 ± 2.10 |

| Effect on micro F0.5 (same 5 folds) | Fold-paired difference, mean ± SD |
|---|---|
| class weighting, released tokens | +5.88 ± 2.51 |
| class weighting, paper-text tokens | +6.78 ± 3.17 |
| rcATT tokenisation, balanced weights | +0.27 ± 0.62 |
| rcATT tokenisation, no weighting | +1.16 ± 1.03 |
| both (released minus paper text) | +7.05 ± 2.86 |
