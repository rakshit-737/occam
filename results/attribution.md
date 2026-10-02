### Attribution on held-out ATT&CK group usage (ATT&CK v19.2)

274 leave-one-report-out incidents from 103 groups; 176 candidate group profiles; 3 planted markers in the false-flag setting. 95% CIs: group-cluster bootstrap.

| Setting | Method | Correct [95% CI] | Names true group | Framed | Brier [95% CI] | ECE | Overconfident errors | Brier (recal.) | ECE (recal.) |
|---|---|---|---|---|---|---|---|---|---|
| closed | TTP-similarity baseline | 0.533 [0.45-0.61] | 0.533 | 0.000 | 0.179 [0.15-0.21] | 0.102 | 0.011 | 0.180 | 0.068 |
| closed | OCCAM ACH | 0.299 [0.23-0.37] | 0.299 | 0.000 | 0.238 [0.22-0.25] | 0.257 | 0.000 | 0.156 | 0.007 |
| closed | OCCAM ACH, top-5 similarity shortlist | 0.339 [0.27-0.41] | 0.339 | 0.000 | 0.264 [0.24-0.28] | 0.253 | 0.007 | 0.201 | 0.075 |
| closed | OCCAM ACH, support-aware ranking | 0.401 [0.32-0.47] | 0.401 | 0.000 | 0.223 [0.20-0.24] | 0.240 | 0.004 | 0.161 | 0.071 |
| open | TTP-similarity baseline | 0.000 [0.00-0.00] | 0.000 | 0.000 | 0.077 [0.06-0.09] | 0.206 | 0.015 | 0.000 | 0.000 |
| open | OCCAM ACH | 0.460 [0.39-0.53] | 0.000 | 0.000 | 0.248 [0.24-0.26] | 0.071 | 0.004 | 0.245 | 0.064 |
| open | OCCAM ACH, top-5 similarity shortlist | 0.642 [0.58-0.70] | 0.000 | 0.000 | 0.234 [0.22-0.25] | 0.086 | 0.011 | 0.222 | 0.036 |
| open | OCCAM ACH, support-aware ranking | 0.055 [0.03-0.09] | 0.000 | 0.000 | 0.303 [0.29-0.32] | 0.493 | 0.015 | 0.052 | 0.001 |
| false_flag | TTP-similarity baseline | 0.113 [0.06-0.17] | 0.113 | 0.880 | 0.700 [0.65-0.75] | 0.755 | 0.708 | 0.100 | 0.054 |
| false_flag | OCCAM ACH | 0.734 [0.67-0.80] | 0.022 | 0.011 | 0.199 [0.19-0.21] | 0.144 | 0.000 | 0.176 | 0.023 |
| false_flag | OCCAM ACH, top-5 similarity shortlist | 0.679 [0.61-0.75] | 0.018 | 0.011 | 0.206 [0.19-0.22] | 0.096 | 0.000 | 0.192 | 0.032 |
| false_flag | OCCAM ACH, support-aware ranking | 0.887 [0.85-0.92] | 0.131 | 0.015 | 0.170 [0.16-0.18] | 0.285 | 0.000 | 0.094 | 0.054 |

*Correct*: closed = names the true group; open = declines to name (true group absent); false_flag = names the true group or concludes the framed group was framed. *Overconfident errors*: wrong with stated probability >= 0.8. *recal.*: histogram binning cross-fitted over a 2-fold group split.

#### Setting-agnostic calibration (the realistic number)

One map fitted on closed + open + false_flag together, cross-fitted by group. The per-setting maps further below know which setting an incident comes from and are an oracle upper bound. Canonical pooled-calibration table; `results/falseflag.md` quotes the same map as one number over all three settings. A single map cannot help the similarity baseline: it never declines, so all its open-world answers are wrong and the map pulls every probability down. The closed-world Brier therefore rises from 0.179 (raw) to 0.315, while the open-world Brier falls to 0.032.

| Setting | Method | Brier (pooled map) | ECE (pooled map) |
|---|---|---|---|
| closed | TTP-similarity baseline | 0.315 | 0.321 |
| closed | OCCAM ACH | 0.189 | 0.174 |
| closed | OCCAM ACH, top-5 similarity shortlist | 0.253 | 0.217 |
| closed | OCCAM ACH, support-aware ranking | 0.171 | 0.108 |
| open | TTP-similarity baseline | 0.032 | 0.139 |
| open | OCCAM ACH | 0.249 | 0.067 |
| open | OCCAM ACH, top-5 similarity shortlist | 0.240 | 0.110 |
| open | OCCAM ACH, support-aware ranking | 0.186 | 0.316 |
| false_flag | TTP-similarity baseline | 0.131 | 0.178 |
| false_flag | OCCAM ACH | 0.205 | 0.158 |
| false_flag | OCCAM ACH, top-5 similarity shortlist | 0.209 | 0.123 |
| false_flag | OCCAM ACH, support-aware ranking | 0.252 | 0.394 |

#### Learned grade -> probability map, fitted per setting (oracle upper bound)

Stated probability per ACH grade, learned (Beta-smoothed, monotone) instead of fixed ICD-203 midpoints. Brier with the learned map is cross-fitted over a 2-fold group split.

| Setting | Method | Brier (ICD-203 midpoints) | Brier (learned grades) | ECE (learned grades) |
|---|---|---|---|---|
| closed | OCCAM ACH | 0.238 | 0.156 | 0.012 |
| closed | OCCAM ACH, top-5 similarity shortlist | 0.264 | 0.201 | 0.073 |
| closed | OCCAM ACH, support-aware ranking | 0.223 | 0.161 | 0.072 |
| open | OCCAM ACH | 0.248 | 0.245 | 0.064 |
| open | OCCAM ACH, top-5 similarity shortlist | 0.234 | 0.227 | 0.038 |
| open | OCCAM ACH, support-aware ranking | 0.303 | 0.053 | 0.017 |
| false_flag | OCCAM ACH | 0.199 | 0.177 | 0.033 |
| false_flag | OCCAM ACH, top-5 similarity shortlist | 0.206 | 0.192 | 0.040 |
| false_flag | OCCAM ACH, support-aware ranking | 0.170 | 0.094 | 0.066 |

Shipped map (fit on all settings of plain ACH, `results/grade_calibration.json`): low = 0.370 (n=568), moderate = 0.777 (n=245), high = 0.818 (n=9)

#### False-flag setting across framing seeds [7, 11, 13, 17, 19]

| Method | Correct, mean ± sample SD | Names framed group, mean ± sample SD | Brier, mean ± sample SD |
|---|---|---|---|
| TTP-similarity baseline | 0.119 ± 0.009 | 0.875 ± 0.009 | 0.699 ± 0.006 |
| OCCAM ACH | 0.718 ± 0.017 | 0.008 ± 0.006 | 0.196 ± 0.004 |
| OCCAM ACH, top-5 similarity shortlist | 0.680 ± 0.014 | 0.008 ± 0.006 | 0.203 ± 0.003 |
| OCCAM ACH, support-aware ranking | 0.894 ± 0.009 | 0.020 ± 0.008 | 0.169 ± 0.003 |
