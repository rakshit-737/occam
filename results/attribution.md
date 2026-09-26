### Attribution on held-out ATT&CK group usage (ATT&CK v19.2)

274 leave-one-report-out incidents from 103 groups; 176 candidate group profiles; 3 planted markers in the false-flag setting.

| Setting | Method | Correct [95% CI] | Names true group | Framed | Brier [95% CI] | ECE | Overconfident errors | Brier (recal.) | ECE (recal.) |
|---|---|---|---|---|---|---|---|---|---|
| closed | TTP-similarity baseline | 0.533 [0.47-0.59] | 0.533 | 0.000 | 0.179 [0.15-0.21] | 0.102 | 0.011 | 0.180 | 0.068 |
| closed | OCCAM ACH | 0.299 [0.25-0.35] | 0.299 | 0.000 | 0.238 [0.23-0.25] | 0.257 | 0.000 | 0.156 | 0.007 |
| closed | OCCAM ACH, top-5 similarity shortlist | 0.339 [0.28-0.40] | 0.339 | 0.000 | 0.264 [0.25-0.28] | 0.253 | 0.007 | 0.201 | 0.075 |
| open | TTP-similarity baseline | 0.000 [0.00-0.00] | 0.000 | 0.000 | 0.077 [0.06-0.10] | 0.206 | 0.015 | 0.000 | 0.000 |
| open | OCCAM ACH | 0.460 [0.41-0.52] | 0.000 | 0.000 | 0.248 [0.24-0.26] | 0.071 | 0.004 | 0.245 | 0.064 |
| open | OCCAM ACH, top-5 similarity shortlist | 0.642 [0.59-0.70] | 0.000 | 0.000 | 0.234 [0.22-0.25] | 0.086 | 0.011 | 0.222 | 0.036 |
| false_flag | TTP-similarity baseline | 0.113 [0.08-0.15] | 0.113 | 0.880 | 0.700 [0.67-0.74] | 0.755 | 0.708 | 0.100 | 0.054 |
| false_flag | OCCAM ACH | 0.734 [0.68-0.78] | 0.022 | 0.011 | 0.199 [0.19-0.21] | 0.144 | 0.000 | 0.176 | 0.023 |
| false_flag | OCCAM ACH, top-5 similarity shortlist | 0.679 [0.62-0.73] | 0.018 | 0.011 | 0.206 [0.20-0.22] | 0.096 | 0.000 | 0.192 | 0.032 |

*Correct*: closed = names the true group; open = declines to name (true group absent); false_flag = names the true group or concludes the framed group was framed. *Overconfident errors*: wrong with stated probability >= 0.8. *recal.*: histogram binning cross-fitted over a 2-fold group split.
