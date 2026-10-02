### Reproduction of rcATT (Legoy et al. 2020) report-level TTP classification

1490 reports, 5-fold CV (KFold, shuffle, seed 42), binary relevance; mean ± SD over folds, percent.

#### Tactics (12 labels)

| Source | Micro P | Micro R | Micro F0.5 | Macro P | Macro R | Macro F0.5 |
|---|---|---|---|---|---|---|
| rcATT paper, Legoy et al. 2020, arXiv:2004.14322 (reported) | 65.64 ± 3.76 | 64.69 ± 3.00 | 65.38 ± 2.87 | 60.26 ± 3.20 | 58.50 ± 3.68 | 59.47 ± 2.29 |
| Reproduction, released rcATT pipeline | 64.72 ± 4.56 | 64.37 ± 2.50 | 64.63 ± 4.05 | 60.88 ± 5.09 | 58.34 ± 2.64 | 60.03 ± 4.41 |
| Reproduction, pipeline as described in the paper | 71.99 ± 4.23 | 50.26 ± 1.65 | 66.24 ± 3.25 | 68.60 ± 8.22 | 40.29 ± 1.88 | 56.42 ± 3.94 |
| OCCAM TF-IDF + LR, same folds | 61.07 ± 3.51 | 65.41 ± 3.14 | 61.88 ± 3.29 | 57.65 ± 5.15 | 59.50 ± 4.55 | 57.39 ± 5.03 |

#### Techniques (197 labels)

| Source | Micro P | Micro R | Micro F0.5 | Macro P | Macro R | Macro F0.5 |
|---|---|---|---|---|---|---|
| rcATT paper, Legoy et al. 2020, arXiv:2004.14322 (reported) | 37.18 ± 6.75 | 29.79 ± 5.91 | 35.02 ± 5.32 | 28.84 ± 6.90 | 22.67 ± 5.94 | 25.06 ± 6.09 |
| Reproduction, released rcATT pipeline | 38.96 ± 2.09 | 27.14 ± 1.61 | 35.81 ± 1.57 | 32.92 ± 1.49 | 22.08 ± 1.20 | 27.91 ± 1.18 |
| Reproduction, pipeline as described in the paper | 59.27 ± 3.60 | 9.20 ± 0.96 | 28.30 ± 2.05 | 20.30 ± 1.22 | 7.19 ± 0.80 | 13.11 ± 0.91 |
| OCCAM TF-IDF + LR, same folds | 37.76 ± 2.12 | 24.81 ± 1.98 | 34.18 ± 2.10 | 15.93 ± 2.84 | 10.33 ± 1.13 | 12.94 ± 2.10 |
