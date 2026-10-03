### False-flag robustness: baselines, controls and ablations (ATT&CK v19.2)

274 held-out incidents from 103 groups, 3 markers per incident. Brackets: group-cluster bootstrap 95% CI (1000 resamples); † = the rate is exactly 0 or 1, so the bootstrap interval is degenerate and a Wilson interval with the number of groups as the sample size is shown. Cross-fitted parameters (per group fold): tau = {0: 0.38, 1: 0.36}, k = {0: 15, 1: 10}; tau matched to ACH's open-world decline = {0: 0.25, 1: 0.255}, to ACH's closed-world accuracy = {0: 0.35, 1: 0.37}.

*Source: GitHub Actions run [37093689060](https://github.com/rakshit-737/occam/actions/runs/37093689060), commit `09cde53`, 2026-10-03T03:35:51+00:00.*

#### Planted markers (false_flag) vs authentic markers (control) vs TTP mimicry

| Method | False flag: correct | False flag: names framed | Authentic: names true | Authentic: calls it a frame | Mimicry: correct | Mimicry: names framed |
|---|---|---|---|---|---|---|
| TTP-similarity, marker boost 0.15 (shipped baseline) | 0.113 [0.06-0.17] | 0.880 [0.82-0.93] | 1.000 [0.96-1.00]† | 0.000 [0.00-0.04]† | 0.212 [0.16-0.27] | 0.763 [0.71-0.82] |
| TTP-similarity, marker boost 0.05 | 0.496 [0.42-0.57] | 0.124 [0.09-0.17] | 0.854 [0.80-0.90] | 0.000 [0.00-0.04]† | 0.212 [0.16-0.27] | 0.763 [0.71-0.82] |
| TTP-similarity, marker boost 0.3 | 0.000 [0.00-0.04]† | 1.000 [0.96-1.00]† | 1.000 [0.96-1.00]† | 0.000 [0.00-0.04]† | 0.212 [0.16-0.27] | 0.763 [0.71-0.82] |
| TTP-similarity, ignores spoofable rows | 0.533 [0.45-0.61] | 0.000 [0.00-0.04]† | 0.533 [0.45-0.61] | 0.000 [0.00-0.04]† | 0.212 [0.16-0.27] | 0.763 [0.71-0.82] |
| IDF coverage, ignores spoofable rows | 0.420 [0.35-0.49] | 0.000 [0.00-0.04]† | 0.420 [0.35-0.49] | 0.000 [0.00-0.04]† | 0.288 [0.22-0.36] | 0.321 [0.25-0.39] |
| Similarity + decline if cosine < tau (tau cross-fitted) | 0.266 [0.20-0.34] | 0.000 [0.00-0.04]† | 0.266 [0.20-0.34] | 0.000 [0.00-0.04]† | 0.109 [0.07-0.15] | 0.445 [0.38-0.50] |
| Similarity + decline, tau matched to ACH's open-world decline rate | 0.474 [0.40-0.55] | 0.000 [0.00-0.04]† | 0.474 [0.40-0.55] | 0.000 [0.00-0.04]† | 0.201 [0.14-0.25] | 0.715 [0.66-0.77] |
| Similarity + decline, tau matched to ACH's closed-world accuracy | 0.299 [0.23-0.37] | 0.000 [0.00-0.04]† | 0.299 [0.23-0.37] | 0.000 [0.00-0.04]† | 0.128 [0.08-0.17] | 0.460 [0.40-0.52] |
| Similarity + consistency gate (k cross-fitted) | 0.920 [0.88-0.95] | 0.080 [0.05-0.12] | 0.770 [0.71-0.83] | 0.230 [0.17-0.29] | 0.212 [0.16-0.27] | 0.763 [0.71-0.82] |
| OCCAM ACH (full) | 0.734 [0.67-0.80] | 0.011 [0.00-0.03] | 0.358 [0.29-0.43] | 0.186 [0.14-0.24] | 0.179 [0.12-0.24] | 0.270 [0.21-0.33] |

#### Closed and open world (abstention) and setting-agnostic calibration

| Method | Closed: correct | Closed: declines | Open: correct decline | Brier, pooled map | Brier, ACH minus method (paired) | Overconfident errors, pooled map |
|---|---|---|---|---|---|---|
| TTP-similarity, marker boost 0.15 (shipped baseline) | 0.533 [0.45-0.61] | 0.000 [0.00-0.04]† | 0.000 [0.00-0.04]† | 0.160 [0.14-0.18] | [+0.031, +0.080] | 0/822 [0.000-0.036] |
| TTP-similarity, marker boost 0.05 | 0.533 [0.45-0.61] | 0.000 [0.00-0.04]† | 0.000 [0.00-0.04]† | 0.144 [0.12-0.16] | [+0.048, +0.095] | 7/822 [0.000-0.020] |
| TTP-similarity, marker boost 0.3 | 0.533 [0.45-0.61] | 0.000 [0.00-0.04]† | 0.000 [0.00-0.04]† | 0.124 [0.11-0.14] | [+0.068, +0.111] | 0/822 [0.000-0.036] |
| TTP-similarity, ignores spoofable rows | 0.533 [0.45-0.61] | 0.000 [0.00-0.04]† | 0.000 [0.00-0.04]† | 0.151 [0.13-0.17] | [+0.039, +0.087] | 7/822 [0.000-0.020] |
| IDF coverage, ignores spoofable rows | 0.420 [0.35-0.49] | 0.000 [0.00-0.04]† | 0.000 [0.00-0.04]† | 0.167 [0.14-0.19] | [+0.021, +0.074] | 0/822 [0.000-0.036] |
| Similarity + decline if cosine < tau (tau cross-fitted) | 0.266 [0.20-0.34] | 0.690 [0.62-0.76] | 0.945 [0.92-0.97] | 0.214 [0.20-0.23] | [-0.016, +0.017] | 10/822 [0.001-0.026] |
| Similarity + decline, tau matched to ACH's open-world decline rate | 0.474 [0.40-0.55] | 0.230 [0.18-0.28] | 0.478 [0.42-0.54] | 0.208 [0.19-0.22] | [-0.014, +0.027] | 10/822 [0.001-0.026] |
| Similarity + decline, tau matched to ACH's closed-world accuracy | 0.299 [0.23-0.37] | 0.639 [0.56-0.71] | 0.934 [0.91-0.96] | 0.214 [0.20-0.23] | [-0.016, +0.017] | 10/822 [0.001-0.026] |
| Similarity + consistency gate (k cross-fitted) | 0.533 [0.45-0.61] | 0.000 [0.00-0.04]† | 0.000 [0.00-0.04]† | 0.204 [0.19-0.22] | [-0.005, +0.027] | 15/822 [0.007-0.031] |
| OCCAM ACH (full) | 0.299 [0.23-0.37] | 0.365 [0.30-0.43] | 0.460 [0.39-0.53] | 0.214 [0.20-0.23] |  | 1/822 [0.000-0.004] |

#### Brier score under the pooled map, per setting: ACH minus method (paired 95% CI)

| Method | Closed | Open | False flag | All three pooled |
|---|---|---|---|---|
| OCCAM ACH (full), value | 0.189 | 0.249 | 0.205 | 0.214 |
| TTP-similarity, marker boost 0.15 (shipped baseline) (0.315 / 0.032 / 0.131 / 0.160) | [-0.178, -0.075] | [+0.197, +0.238] | [+0.045, +0.104] | [+0.031, +0.080] |
| TTP-similarity, marker boost 0.05 (0.190 / 0.070 / 0.171 / 0.144) | [-0.040, +0.034] | [+0.156, +0.203] | [-0.004, +0.074] | [+0.048, +0.095] |
| TTP-similarity, marker boost 0.3 (0.315 / 0.042 / 0.016 / 0.124) | [-0.180, -0.072] | [+0.186, +0.229] | [+0.169, +0.211] | [+0.068, +0.111] |
| TTP-similarity, ignores spoofable rows (0.189 / 0.076 / 0.189 / 0.151) | [-0.037, +0.035] | [+0.150, +0.198] | [-0.024, +0.056] | [+0.039, +0.087] |
| IDF coverage, ignores spoofable rows (0.206 / 0.088 / 0.206 / 0.167) | [-0.054, +0.016] | [+0.139, +0.184] | [-0.039, +0.040] | [+0.021, +0.074] |
| Similarity + decline if cosine < tau (tau cross-fitted) (0.165 / 0.313 / 0.165 / 0.214) | [+0.000, +0.046] | [-0.088, -0.040] | [+0.011, +0.071] | [-0.016, +0.017] |
| Similarity + decline, tau matched to ACH's open-world decline rate (0.181 / 0.262 / 0.181 / 0.208) | [-0.020, +0.034] | [-0.040, +0.015] | [-0.005, +0.057] | [-0.014, +0.027] |
| Similarity + decline, tau matched to ACH's closed-world accuracy (0.170 / 0.302 / 0.170 / 0.214) | [-0.005, +0.040] | [-0.077, -0.030] | [+0.006, +0.067] | [-0.016, +0.017] |
| Similarity + consistency gate (k cross-fitted) (0.176 / 0.156 / 0.280 / 0.204) | [-0.011, +0.037] | [+0.070, +0.116] | [-0.112, -0.041] | [-0.005, +0.027] |

#### Ablations of ACH (each row removes one mechanism)

| Variant | Closed correct | Open correct | False flag correct | names framed | names true | Authentic: names true | Authentic: calls frame | Mimicry: correct | Mimicry: names framed | Brier, pooled map | Brier, variant minus full ACH (paired) | Overconfident errors, pooled map |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OCCAM ACH (full) | 0.299 | 0.460 | 0.734 | 0.011 | 0.022 | 0.358 | 0.186 | 0.179 | 0.270 | 0.214 |  | 1/822 |
| ACH without false-flag hypotheses | 0.299 | 0.460 | 0.201 | 0.011 | 0.201 | 0.369 | 0.000 | 0.179 | 0.270 | 0.207 | [-0.023, +0.011] | 1/822 |
| ACH without unknown-actor hypothesis | 0.372 | 0.000 | 0.945 | 0.033 | 0.026 | 0.518 | 0.372 | 0.212 | 0.307 | 0.181 | [-0.048, -0.020] | 27/822 |
| ACH without spoofable x0.5 discount | 0.299 | 0.460 | 0.726 | 0.011 | 0.004 | 0.372 | 0.193 | 0.179 | 0.270 | 0.231 | [+0.010, +0.023] | 1/822 |
| ACH without confidence caps | 0.299 | 0.460 | 0.734 | 0.011 | 0.022 | 0.358 | 0.186 | 0.179 | 0.270 | 0.207 | [-0.010, -0.005] | 2/822 |
| ACH without diagnosticity weighting | 0.237 | 0.723 | 0.631 | 0.004 | 0.022 | 0.263 | 0.117 | 0.168 | 0.182 | 0.234 | [+0.010, +0.029] | 0/822 |
| ACH without FF hypotheses, discount and caps | 0.299 | 0.460 | 0.131 | 0.026 | 0.131 | 0.401 | 0.000 | 0.179 | 0.270 | 0.207 | [-0.026, +0.011] | 0/822 |
| ACH, support-aware ranking | 0.401 | 0.055 | 0.887 | 0.015 | 0.131 | 0.507 | 0.255 | 0.245 | 0.354 | 0.203 | [-0.028, +0.005] | 5/822 |
| ACH, top-5 similarity shortlist | 0.339 | 0.642 | 0.679 | 0.011 | 0.018 | 0.350 | 0.153 | 0.230 | 0.292 | 0.234 | [+0.010, +0.030] | 4/822 |

#### Paired difference ACH minus method, 95% cluster-bootstrap interval

| Method | Closed: correct | Open: correct decline | False flag: correct | False flag: names framed | Authentic: names true | Authentic: calls it a frame | Mimicry: correct | Mimicry: names framed |
|---|---|---|---|---|---|---|---|---|
| TTP-similarity, marker boost 0.15 (shipped baseline) | [-0.317, -0.152] | [+0.393, +0.531] | [+0.534, +0.700] | [-0.921, -0.811] | [-0.712, -0.574] | [+0.138, +0.244] | [-0.101, +0.035] | [-0.560, -0.422] |
| TTP-similarity, marker boost 0.05 | [-0.317, -0.152] | [+0.393, +0.531] | [+0.147, +0.327] | [-0.160, -0.073] | [-0.573, -0.428] | [+0.138, +0.244] | [-0.101, +0.035] | [-0.560, -0.422] |
| TTP-similarity, marker boost 0.3 | [-0.317, -0.152] | [+0.393, +0.531] | [+0.669, +0.796] | [-1.000, -0.974] | [-0.712, -0.574] | [+0.138, +0.244] | [-0.101, +0.035] | [-0.560, -0.422] |
| TTP-similarity, ignores spoofable rows | [-0.317, -0.152] | [+0.393, +0.531] | [+0.111, +0.289] | [+0.000, +0.026] | [-0.260, -0.098] | [+0.138, +0.244] | [-0.101, +0.035] | [-0.560, -0.422] |
| IDF coverage, ignores spoofable rows | [-0.161, -0.082] | [+0.393, +0.531] | [+0.241, +0.396] | [+0.000, +0.026] | [-0.109, -0.011] | [+0.138, +0.244] | [-0.160, -0.066] | [-0.086, -0.018] |
| Similarity + decline if cosine < tau (tau cross-fitted) | [-0.053, +0.119] | [-0.560, -0.410] | [+0.371, +0.556] | [+0.000, +0.026] | [+0.004, +0.178] | [+0.138, +0.244] | [+0.008, +0.131] | [-0.252, -0.102] |
| Similarity + decline, tau matched to ACH's open-world decline rate | [-0.254, -0.100] | [-0.114, +0.073] | [+0.174, +0.352] | [+0.000, +0.026] | [-0.193, -0.044] | [+0.138, +0.244] | [-0.088, +0.046] | [-0.518, -0.372] |
| Similarity + decline, tau matched to ACH's closed-world accuracy | [-0.083, +0.080] | [-0.548, -0.396] | [+0.337, +0.525] | [+0.000, +0.026] | [-0.026, +0.140] | [+0.138, +0.244] | [-0.014, +0.116] | [-0.264, -0.120] |
| Similarity + consistency gate (k cross-fitted) | [-0.317, -0.152] | [+0.393, +0.531] | [-0.256, -0.122] | [-0.107, -0.037] | [-0.485, -0.342] | [-0.118, +0.025] | [-0.101, +0.035] | [-0.560, -0.422] |

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

*Correct*: closed/authentic = names the true group; open = declines; false_flag/mimicry = names the true group or concludes the framed group was framed. *Calls it a frame* under authentic markers is a false alarm. Mimicry items are ordinary technique/software rows, so the gate cannot see them (it equals plain similarity there). *Pooled map*: one probability map (histogram binning; the learned grade map for ACH variants) fitted on closed + open + false_flag together and cross-fitted by group, i.e. without knowing which setting an incident comes from; Brier and overconfident errors (wrong with calibrated probability >= 0.8) are over all three settings (822 answers). Per setting it gives similarity 0.315 / 0.032 / 0.131 and ACH 0.189 / 0.249 / 0.205 (closed / open / false_flag), the same map as the pooled table in `results/attribution.md`. The pooled number depends on the equal 1:1:1 mix of settings. Raw (uncalibrated) overconfident errors under planted markers: similarity 194/274, ACH 0/274. Brier rewards a matcher that is always framed but states low probabilities: marker boost 0.3 is framed 1.000 of the time under planted markers, yet has the lowest pooled Brier (0.124; false flag 0.016), so Brier alone does not measure resistance to framing.
