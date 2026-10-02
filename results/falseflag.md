### False-flag robustness: baselines, controls and ablations (ATT&CK v19.2)

274 held-out incidents from 103 groups, 3 markers per incident. Brackets: group-cluster bootstrap 95% CI. Cross-fitted parameters: tau = {0: 0.38, 1: 0.36}, k = {0: 15, 1: 10} (per group fold).

#### Planted markers (false_flag) vs authentic markers (control) vs TTP mimicry

| Method | False flag: correct | False flag: names framed | Authentic: names true | Authentic: calls it a frame | Mimicry: correct | Mimicry: names framed |
|---|---|---|---|---|---|---|
| TTP-similarity, marker boost 0.15 (shipped baseline) | 0.113 [0.06-0.17] | 0.880 [0.82-0.93] | 1.000 [1.00-1.00] | 0.000 [0.00-0.00] | 0.212 [0.16-0.27] | 0.763 [0.71-0.82] |
| TTP-similarity, marker boost 0.05 | 0.496 [0.42-0.57] | 0.124 [0.09-0.17] | 0.854 [0.80-0.90] | 0.000 [0.00-0.00] | 0.212 [0.16-0.27] | 0.763 [0.71-0.82] |
| TTP-similarity, ignores spoofable rows | 0.533 [0.45-0.61] | 0.000 [0.00-0.00] | 0.533 [0.45-0.61] | 0.000 [0.00-0.00] | 0.212 [0.16-0.27] | 0.763 [0.71-0.82] |
| IDF coverage, ignores spoofable rows | 0.420 [0.35-0.49] | 0.000 [0.00-0.00] | 0.420 [0.35-0.49] | 0.000 [0.00-0.00] | 0.288 [0.22-0.36] | 0.321 [0.25-0.39] |
| Similarity + decline if cosine < tau (tau cross-fitted) | 0.266 [0.20-0.34] | 0.000 [0.00-0.00] | 0.266 [0.20-0.34] | 0.000 [0.00-0.00] | 0.109 [0.07-0.15] | 0.445 [0.38-0.50] |
| Similarity + consistency gate (k cross-fitted) | 0.920 [0.88-0.95] | 0.080 [0.05-0.12] | 0.770 [0.71-0.83] | 0.230 [0.17-0.29] | 0.212 [0.16-0.27] | 0.763 [0.71-0.82] |
| OCCAM ACH (full) | 0.734 [0.67-0.80] | 0.011 [0.00-0.03] | 0.358 [0.29-0.43] | 0.186 [0.14-0.24] | 0.179 [0.12-0.24] | 0.270 [0.21-0.33] |

#### Closed and open world (abstention)

| Method | Closed: correct | Closed: declines | Open: correct decline | Brier, pooled calibration |
|---|---|---|---|---|
| TTP-similarity, marker boost 0.15 (shipped baseline) | 0.533 [0.45-0.61] | 0.000 | 0.000 [0.00-0.00] | 0.160 |
| TTP-similarity, marker boost 0.05 | 0.533 [0.45-0.61] | 0.000 | 0.000 [0.00-0.00] | 0.144 |
| TTP-similarity, ignores spoofable rows | 0.533 [0.45-0.61] | 0.000 | 0.000 [0.00-0.00] | 0.151 |
| IDF coverage, ignores spoofable rows | 0.420 [0.35-0.49] | 0.000 | 0.000 [0.00-0.00] | 0.167 |
| Similarity + decline if cosine < tau (tau cross-fitted) | 0.266 [0.20-0.34] | 0.690 | 0.945 [0.92-0.97] |  |
| Similarity + consistency gate (k cross-fitted) | 0.533 [0.45-0.61] | 0.000 | 0.000 [0.00-0.00] |  |
| OCCAM ACH (full) | 0.299 [0.23-0.37] | 0.365 | 0.460 [0.39-0.53] | 0.214 |

#### Ablations of ACH (each row removes one mechanism)

| Variant | Closed correct | Open correct | False flag correct | names framed | names true | Authentic: names true | Authentic: calls frame | Mimicry: names framed |
|---|---|---|---|---|---|---|---|---|
| OCCAM ACH (full) | 0.299 | 0.460 | 0.734 | 0.011 | 0.022 | 0.358 | 0.186 | 0.270 |
| ACH without false-flag hypotheses | 0.299 | 0.460 | 0.201 | 0.011 | 0.201 | 0.369 | 0.000 | 0.270 |
| ACH without unknown-actor hypothesis | 0.372 | 0.000 | 0.945 | 0.033 | 0.026 | 0.518 | 0.372 | 0.307 |
| ACH without spoofable x0.5 discount | 0.299 | 0.460 | 0.726 | 0.011 | 0.004 | 0.372 | 0.193 | 0.270 |
| ACH without confidence caps | 0.299 | 0.460 | 0.734 | 0.011 | 0.022 | 0.358 | 0.186 | 0.270 |
| ACH without diagnosticity weighting | 0.237 | 0.723 | 0.631 | 0.004 | 0.022 | 0.263 | 0.117 | 0.182 |
| ACH without FF hypotheses, discount and caps | 0.299 | 0.460 | 0.131 | 0.026 | 0.131 | 0.401 | 0.000 | 0.270 |
| ACH, support-aware ranking | 0.401 | 0.055 | 0.887 | 0.015 | 0.131 | 0.507 | 0.255 | 0.354 |

#### Paired difference ACH minus method, 95% cluster-bootstrap interval

| Method | False flag: names framed | Authentic: names true | Mimicry: names framed | Closed: correct |
|---|---|---|---|---|
| TTP-similarity, marker boost 0.15 (shipped baseline) | [-0.92, -0.81] | [-0.71, -0.57] | [-0.56, -0.42] | [-0.32, -0.15] |
| TTP-similarity, marker boost 0.05 | [-0.16, -0.07] | [-0.57, -0.43] | [-0.56, -0.42] | [-0.32, -0.15] |
| TTP-similarity, ignores spoofable rows | [+0.00, +0.03] | [-0.26, -0.10] | [-0.56, -0.42] | [-0.32, -0.15] |
| IDF coverage, ignores spoofable rows | [+0.00, +0.03] | [-0.11, -0.01] | [-0.09, -0.02] | [-0.16, -0.08] |
| Similarity + decline if cosine < tau (tau cross-fitted) | [+0.00, +0.03] | [+0.00, +0.18] | [-0.25, -0.10] | [-0.05, +0.12] |
| Similarity + consistency gate (k cross-fitted) | [-0.11, -0.04] | [-0.49, -0.34] | [-0.56, -0.42] | [-0.32, -0.15] |

#### Number of planted / mimicked items

| n | Method | False flag: names framed | Authentic: names true | Authentic: calls frame | Mimicry: names framed |
|---|---|---|---|---|---|
| 1 | TTP-similarity, marker boost 0.15 (shipped baseline) | 0.124 | 0.854 | 0.000 | 0.208 |
| 1 | TTP-similarity, ignores spoofable rows | 0.000 | 0.533 | 0.000 | 0.208 |
| 1 | IDF coverage, ignores spoofable rows | 0.000 | 0.420 | 0.000 | 0.036 |
| 1 | OCCAM ACH (full) | 0.007 | 0.321 | 0.153 | 0.066 |
| 1 | ACH without false-flag hypotheses | 0.007 | 0.336 | 0.000 | 0.066 |
| 1 | Similarity + consistency gate (k cross-fitted) | 0.080 | 0.770 | 0.230 | 0.208 |
| 6 | TTP-similarity, marker boost 0.15 (shipped baseline) | 1.000 | 1.000 | 0.000 | 0.909 |
| 6 | TTP-similarity, ignores spoofable rows | 0.000 | 0.533 | 0.000 | 0.909 |
| 6 | IDF coverage, ignores spoofable rows | 0.000 | 0.420 | 0.000 | 0.613 |
| 6 | OCCAM ACH (full) | 0.011 | 0.372 | 0.193 | 0.442 |
| 6 | ACH without false-flag hypotheses | 0.026 | 0.401 | 0.000 | 0.442 |
| 6 | Similarity + consistency gate (k cross-fitted) | 0.080 | 0.770 | 0.230 | 0.909 |

*Correct*: closed/authentic = names the true group; open = declines; false_flag/mimicry = names the true group or concludes the framed group was framed. *Calls it a frame* under authentic markers is a false alarm. Mimicry items are ordinary technique/software rows, so the gate cannot see them (it equals plain similarity there). *Brier, pooled calibration*: one grade/probability map fitted on closed+open+false_flag together and cross-fitted by group, i.e. without knowing which setting an incident comes from.
