### End-to-end on APTnotes (75 real reports, 33 groups; extractor: keyword)

*Source: GitHub Actions run [37093689060](https://github.com/rakshit-737/occam/actions/runs/37093689060), commit `09cde53`, 2026-10-03T03:37:13+00:00.*

Mean per report: 3.5 techniques, 2.5 software, 102.4 IOCs (all span-anchored). Evidence used: software. 15 reports with nothing extracted are scored as declines. 23 of 75 reports matched an ATT&CK citation of their own group (held out in the leak-controlled rows). 28 groups among the reports with extracted items (clustered below). Skipped: 1 (2014/h12756-wp-shell-crew.pdf: excluded: its converted text quotes webshell code and is quarantined by Windows Defender on the author's machine; skipped everywhere so local and CI runs match).

| Attributor | Profiles | Top-1 [Wilson 95%] | Top-5 | Names someone | Brier | Wrong at p>=0.8 [Wilson 95%] |
|---|---|---|---|---|---|---|
| TTP-similarity baseline | as-is (upper bound) | 0.520 [0.41-0.63] | 0.573 | 0.800 | 0.316 | 1/75 [0.00-0.07] |
| OCCAM ACH | as-is (upper bound) | 0.493 [0.38-0.60] | 0.560 | 0.773 | 0.201 | 0/75 [0.00-0.05] |
| OCCAM ACH, top-5 shortlist | as-is (upper bound) | 0.520 [0.41-0.63] | 0.573 | 0.773 | 0.198 | 0/75 [0.00-0.05] |
| TTP-similarity baseline | leak-controlled | 0.480 [0.37-0.59] | 0.547 | 0.800 | 0.325 | 1/75 [0.00-0.07] |
| OCCAM ACH | leak-controlled | 0.453 [0.35-0.57] | 0.533 | 0.760 | 0.214 | 0/75 [0.00-0.05] |
| OCCAM ACH, top-5 shortlist | leak-controlled | 0.480 [0.37-0.59] | 0.547 | 0.760 | 0.211 | 0/75 [0.00-0.05] |

| Exact McNemar test (same reports) | Correct only first | Correct only second | Both | p (two-sided) |
|---|---|---|---|---|
| ACH vs similarity, as-is | 1 | 3 | 36 | 0.625 |
| ACH vs similarity, leak-controlled | 1 | 3 | 33 | 0.625 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.983 | 0.887 | 0.220 | 50 |
| single-linkage (t=0.3) | 1.000 | 0.873 | 0.080 | 57 |
