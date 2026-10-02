### Extended attribution evaluation (profiles/incidents from ATT&CK, current release v19.2)

| Protocol | Incidents | Groups | Candidate profiles |
|---|---|---|---|
| `loro-all`: Leave-one-report-out, every (group, report) pair, no per-group cap | 575 (0 campaigns) | 103 | 176 |
| `campaigns`: ATT&CK campaigns attributed to a group, held out with all their references | 21 (21 campaigns) | 15 | 176 |
| `unattributed`: ATT&CK campaigns with no attributed group (correct = decline) | 31 (31 campaigns) | 0 | 176 |
| `unattributed-clean`: As unattributed, minus campaigns whose ATT&CK description names a tracked group | 21 (21 campaigns) | 0 | 176 |
| `temporal-12.1`: Profiles from ATT&CK v12.1 (released Nov 2022); incidents added to ATT&CK after it (in v19.2) | 89 (15 campaigns) | 26 | 133 |
| `temporal-15.1`: Profiles from ATT&CK v15.1 (released May 2024); incidents added to ATT&CK after it (in v19.2) | 69 (9 campaigns) | 22 | 148 |

`unattributed`: 10 campaigns name a tracked group in their own description (excluded in `unattributed-clean`).

`temporal-12.1` id mapping: 1506 items, 1327 known to the old release, 17 mapped via revoked-by, 54 to the parent technique, 108 dropped (7.2%); 81 of 96 incidents had an unknown id; 89 kept (>= 4 items).

`temporal-15.1` id mapping: 1133 items, 1009 known to the old release, 23 mapped via revoked-by, 22 to the parent technique, 79 dropped (7.0%); 61 of 77 incidents had an unknown id; 69 kept (>= 4 items).

| Protocol | Setting | Method | Correct [95% CI] | Names true group | Framed | Brier | Overconfident errors |
|---|---|---|---|---|---|---|---|
| loro-all | closed | TTP-similarity baseline | 0.478 [0.40-0.56] | 0.478 | 0.000 | 0.205 | 0.019 |
| loro-all | closed | OCCAM ACH | 0.390 [0.31-0.45] | 0.390 | 0.000 | 0.228 | 0.000 |
| loro-all | closed | OCCAM ACH, top-5 similarity shortlist | 0.402 [0.33-0.47] | 0.402 | 0.000 | 0.250 | 0.005 |
| loro-all | closed | OCCAM ACH, support-aware ranking | 0.503 [0.42-0.56] | 0.503 | 0.000 | 0.204 | 0.003 |
| loro-all | open | TTP-similarity baseline | 0.000 [0.00-0.00] | 0.000 | 0.000 | 0.089 | 0.024 |
| loro-all | open | OCCAM ACH | 0.473 [0.42-0.53] | 0.000 | 0.000 | 0.247 | 0.002 |
| loro-all | open | OCCAM ACH, top-5 similarity shortlist | 0.642 [0.59-0.69] | 0.000 | 0.000 | 0.233 | 0.014 |
| loro-all | open | OCCAM ACH, support-aware ranking | 0.064 [0.04-0.09] | 0.000 | 0.000 | 0.314 | 0.028 |
| loro-all | false_flag | TTP-similarity baseline | 0.073 [0.04-0.11] | 0.073 | 0.918 | 0.736 | 0.736 |
| loro-all | false_flag | OCCAM ACH | 0.739 [0.69-0.79] | 0.023 | 0.009 | 0.195 | 0.000 |
| loro-all | false_flag | OCCAM ACH, top-5 similarity shortlist | 0.697 [0.64-0.75] | 0.021 | 0.009 | 0.203 | 0.000 |
| loro-all | false_flag | OCCAM ACH, support-aware ranking | 0.894 [0.86-0.92] | 0.160 | 0.028 | 0.176 | 0.000 |
| campaigns | closed | TTP-similarity baseline | 0.286 [0.14-0.50] | 0.286 | 0.000 | 0.155 | 0.000 |
| campaigns | closed | OCCAM ACH | 0.238 [0.11-0.45] | 0.238 | 0.000 | 0.253 | 0.000 |
| campaigns | closed | OCCAM ACH, top-5 similarity shortlist | 0.238 [0.11-0.45] | 0.238 | 0.000 | 0.269 | 0.000 |
| campaigns | closed | OCCAM ACH, support-aware ranking | 0.429 [0.24-0.63] | 0.429 | 0.000 | 0.217 | 0.000 |
| campaigns | open | TTP-similarity baseline | 0.000 [0.00-0.15] | 0.000 | 0.000 | 0.027 | 0.000 |
| campaigns | open | OCCAM ACH | 0.619 [0.41-0.79] | 0.000 | 0.000 | 0.243 | 0.000 |
| campaigns | open | OCCAM ACH, top-5 similarity shortlist | 0.857 [0.65-0.95] | 0.000 | 0.000 | 0.181 | 0.000 |
| campaigns | open | OCCAM ACH, support-aware ranking | 0.048 [0.01-0.23] | 0.000 | 0.000 | 0.253 | 0.000 |
| campaigns | false_flag | TTP-similarity baseline | 0.000 [0.00-0.15] | 0.000 | 1.000 | 0.873 | 1.000 |
| campaigns | false_flag | OCCAM ACH | 0.667 [0.45-0.83] | 0.000 | 0.000 | 0.205 | 0.000 |
| campaigns | false_flag | OCCAM ACH, top-5 similarity shortlist | 0.571 [0.37-0.76] | 0.000 | 0.000 | 0.205 | 0.000 |
| campaigns | false_flag | OCCAM ACH, support-aware ranking | 1.000 [0.85-1.00] | 0.143 | 0.000 | 0.147 | 0.000 |
| unattributed | open | TTP-similarity baseline | 0.000 [0.00-0.11] | 0.000 | 0.000 | 0.096 | 0.065 |
| unattributed | open | OCCAM ACH | 0.484 [0.32-0.65] | 0.000 | 0.000 | 0.259 | 0.000 |
| unattributed | open | OCCAM ACH, top-5 similarity shortlist | 0.742 [0.57-0.86] | 0.000 | 0.000 | 0.228 | 0.000 |
| unattributed | open | OCCAM ACH, support-aware ranking | 0.000 [0.00-0.11] | 0.000 | 0.000 | 0.306 | 0.032 |
| unattributed-clean | open | TTP-similarity baseline | 0.000 [0.00-0.15] | 0.000 | 0.000 | 0.070 | 0.048 |
| unattributed-clean | open | OCCAM ACH | 0.571 [0.37-0.76] | 0.000 | 0.000 | 0.260 | 0.000 |
| unattributed-clean | open | OCCAM ACH, top-5 similarity shortlist | 0.762 [0.55-0.89] | 0.000 | 0.000 | 0.215 | 0.000 |
| unattributed-clean | open | OCCAM ACH, support-aware ranking | 0.000 [0.00-0.15] | 0.000 | 0.000 | 0.299 | 0.000 |
| temporal-12.1 | closed | TTP-similarity baseline | 0.202 [0.10-0.35] | 0.202 | 0.000 | 0.162 | 0.034 |
| temporal-12.1 | closed | OCCAM ACH | 0.213 [0.11-0.36] | 0.213 | 0.000 | 0.262 | 0.000 |
| temporal-12.1 | closed | OCCAM ACH, top-5 similarity shortlist | 0.213 [0.10-0.37] | 0.213 | 0.000 | 0.312 | 0.000 |
| temporal-12.1 | closed | OCCAM ACH, support-aware ranking | 0.270 [0.16-0.43] | 0.270 | 0.000 | 0.269 | 0.022 |
| temporal-12.1 | open | TTP-similarity baseline | 0.000 [0.00-0.00] | 0.000 | 0.000 | 0.099 | 0.034 |
| temporal-12.1 | open | OCCAM ACH | 0.506 [0.43-0.58] | 0.000 | 0.000 | 0.262 | 0.000 |
| temporal-12.1 | open | OCCAM ACH, top-5 similarity shortlist | 0.764 [0.68-0.84] | 0.000 | 0.000 | 0.205 | 0.000 |
| temporal-12.1 | open | OCCAM ACH, support-aware ranking | 0.011 [0.00-0.04] | 0.000 | 0.000 | 0.338 | 0.045 |
| temporal-12.1 | false_flag | TTP-similarity baseline | 0.034 [0.00-0.08] | 0.034 | 0.966 | 0.835 | 0.910 |
| temporal-12.1 | false_flag | OCCAM ACH | 0.708 [0.62-0.83] | 0.011 | 0.000 | 0.190 | 0.000 |
| temporal-12.1 | false_flag | OCCAM ACH, top-5 similarity shortlist | 0.629 [0.53-0.75] | 0.011 | 0.000 | 0.211 | 0.000 |
| temporal-12.1 | false_flag | OCCAM ACH, support-aware ranking | 0.899 [0.84-0.95] | 0.056 | 0.045 | 0.161 | 0.000 |
| temporal-15.1 | closed | TTP-similarity baseline | 0.116 [0.03-0.25] | 0.116 | 0.000 | 0.123 | 0.014 |
| temporal-15.1 | closed | OCCAM ACH | 0.130 [0.06-0.23] | 0.130 | 0.000 | 0.274 | 0.000 |
| temporal-15.1 | closed | OCCAM ACH, top-5 similarity shortlist | 0.116 [0.04-0.22] | 0.116 | 0.000 | 0.326 | 0.000 |
| temporal-15.1 | closed | OCCAM ACH, support-aware ranking | 0.159 [0.06-0.29] | 0.159 | 0.000 | 0.282 | 0.014 |
| temporal-15.1 | open | TTP-similarity baseline | 0.000 [0.00-0.00] | 0.000 | 0.000 | 0.087 | 0.014 |
| temporal-15.1 | open | OCCAM ACH | 0.493 [0.31-0.60] | 0.000 | 0.000 | 0.237 | 0.000 |
| temporal-15.1 | open | OCCAM ACH, top-5 similarity shortlist | 0.725 [0.60-0.82] | 0.000 | 0.000 | 0.197 | 0.000 |
| temporal-15.1 | open | OCCAM ACH, support-aware ranking | 0.014 [0.00-0.05] | 0.000 | 0.000 | 0.299 | 0.014 |
| temporal-15.1 | false_flag | TTP-similarity baseline | 0.014 [0.00-0.05] | 0.014 | 0.986 | 0.832 | 0.870 |
| temporal-15.1 | false_flag | OCCAM ACH | 0.681 [0.57-0.86] | 0.000 | 0.000 | 0.199 | 0.000 |
| temporal-15.1 | false_flag | OCCAM ACH, top-5 similarity shortlist | 0.609 [0.49-0.79] | 0.000 | 0.000 | 0.213 | 0.000 |
| temporal-15.1 | false_flag | OCCAM ACH, support-aware ranking | 0.928 [0.88-0.98] | 0.014 | 0.000 | 0.147 | 0.000 |

False-flag setting over framing seeds (mean ± sample SD):

| Protocol | Method | Correct | Names framed group | Names true group |
|---|---|---|---|---|
| loro-all | TTP-similarity baseline | 0.077 ± 0.003 | 0.914 ± 0.004 | 0.077 ± 0.003 |
| loro-all | OCCAM ACH | 0.736 ± 0.015 | 0.011 ± 0.004 | 0.019 ± 0.005 |
| loro-all | OCCAM ACH, top-5 similarity shortlist | 0.699 ± 0.015 | 0.010 ± 0.004 | 0.016 ± 0.005 |
| loro-all | OCCAM ACH, support-aware ranking | 0.894 ± 0.001 | 0.024 ± 0.007 | 0.145 ± 0.015 |
| campaigns | TTP-similarity baseline | 0.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 |
| campaigns | OCCAM ACH | 0.733 ± 0.054 | 0.010 ± 0.021 | 0.000 ± 0.000 |
| campaigns | OCCAM ACH, top-5 similarity shortlist | 0.667 ± 0.075 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| campaigns | OCCAM ACH, support-aware ranking | 0.943 ± 0.062 | 0.019 ± 0.026 | 0.057 ± 0.062 |
| temporal-12.1 | TTP-similarity baseline | 0.025 ± 0.005 | 0.973 ± 0.006 | 0.025 ± 0.005 |
| temporal-12.1 | OCCAM ACH | 0.730 ± 0.018 | 0.007 ± 0.010 | 0.018 ± 0.006 |
| temporal-12.1 | OCCAM ACH, top-5 similarity shortlist | 0.645 ± 0.022 | 0.004 ± 0.010 | 0.018 ± 0.006 |
| temporal-12.1 | OCCAM ACH, support-aware ranking | 0.926 ± 0.023 | 0.016 ± 0.019 | 0.061 ± 0.013 |
| temporal-15.1 | TTP-similarity baseline | 0.003 ± 0.006 | 0.997 ± 0.006 | 0.003 ± 0.006 |
| temporal-15.1 | OCCAM ACH | 0.713 ± 0.024 | 0.000 ± 0.000 | 0.003 ± 0.006 |
| temporal-15.1 | OCCAM ACH, top-5 similarity shortlist | 0.617 ± 0.022 | 0.000 ± 0.000 | 0.003 ± 0.006 |
| temporal-15.1 | OCCAM ACH, support-aware ranking | 0.933 ± 0.039 | 0.012 ± 0.016 | 0.014 ± 0.010 |

*Correct*: closed = names the true group; open = declines to name; false_flag = names the true group or concludes the framed group was framed. Temporal protocols use the old release's profiles and KB and hold nothing out. Intervals: group-cluster bootstrap (n >= 50), else Wilson score interval. A rate of exactly 0 (the similarity baseline never declines) has a degenerate bootstrap interval [0.00-0.00]; its Wilson upper bound is about 3.8/n (e.g. 0.007 for n = 575).
