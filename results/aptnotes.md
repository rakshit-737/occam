### End-to-end on APTnotes (75 real reports, 33 groups; extractor: keyword)

*Source: GitHub Actions run [37093689060](https://github.com/rakshit-737/occam/actions/runs/37093689060), commit `09cde53`, 2026-10-03T03:35:45+00:00.*

Mean per report: 3.5 techniques, 2.5 software, 102.4 IOCs (all span-anchored). Evidence used: all. 3 reports with nothing extracted are scored as declines. 23 of 75 reports matched an ATT&CK citation of their own group (held out in the leak-controlled rows). 33 groups among the reports with extracted items (clustered below). Skipped: 1 (2014/h12756-wp-shell-crew.pdf: excluded: its converted text quotes webshell code and is quarantined by Windows Defender on the author's machine; skipped everywhere so local and CI runs match).

| Attributor | Profiles | Top-1 [Wilson 95%] | Top-5 | Names someone | Brier | Wrong at p>=0.8 [Wilson 95%] |
|---|---|---|---|---|---|---|
| TTP-similarity baseline | as-is (upper bound) | 0.320 [0.23-0.43] | 0.533 | 0.960 | 0.332 | 9/75 [0.06-0.21] |
| OCCAM ACH | as-is (upper bound) | 0.360 [0.26-0.47] | 0.493 | 0.840 | 0.216 | 0/75 [0.00-0.05] |
| OCCAM ACH, top-5 shortlist | as-is (upper bound) | 0.347 [0.25-0.46] | 0.533 | 0.640 | 0.225 | 0/75 [0.00-0.05] |
| TTP-similarity baseline | leak-controlled | 0.280 [0.19-0.39] | 0.493 | 0.960 | 0.333 | 9/75 [0.06-0.21] |
| OCCAM ACH | leak-controlled | 0.320 [0.23-0.43] | 0.467 | 0.827 | 0.229 | 0/75 [0.00-0.05] |
| OCCAM ACH, top-5 shortlist | leak-controlled | 0.293 [0.20-0.40] | 0.493 | 0.587 | 0.242 | 0/75 [0.00-0.05] |

| Exact McNemar test (same reports) | Correct only first | Correct only second | Both | p (two-sided) |
|---|---|---|---|---|
| ACH vs similarity, as-is | 12 | 9 | 15 | 0.664 |
| ACH vs similarity, leak-controlled | 12 | 9 | 12 | 0.664 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.972 | 0.890 | 0.242 | 59 |
| single-linkage (t=0.3) | 0.986 | 0.874 | 0.068 | 68 |
