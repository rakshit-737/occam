### End-to-end on APTnotes (75 real reports, 33 groups; extractor: keyword)

*Source: GitHub Actions run [37093689060](https://github.com/rakshit-737/occam-cti-attribution/actions/runs/37093689060), commit `09cde53`, 2026-10-03T03:38:43+00:00.*

Mean per report: 3.5 techniques, 2.5 software, 102.4 IOCs (all span-anchored). Evidence used: techniques. 6 reports with nothing extracted are scored as declines. 23 of 75 reports matched an ATT&CK citation of their own group (held out in the leak-controlled rows). 32 groups among the reports with extracted items (clustered below). Skipped: 1 (2014/h12756-wp-shell-crew.pdf: excluded: its converted text quotes webshell code and is quarantined by Windows Defender on the author's machine; skipped everywhere so local and CI runs match).

| Attributor | Profiles | Top-1 [Wilson 95%] | Top-5 | Names someone | Brier | Wrong at p>=0.8 [Wilson 95%] |
|---|---|---|---|---|---|---|
| TTP-similarity baseline | as-is (upper bound) | 0.000 [0.00-0.05] | 0.027 | 0.920 | 0.408 | 23/75 [0.21-0.42] |
| OCCAM ACH | as-is (upper bound) | 0.013 [0.00-0.07] | 0.093 | 0.560 | 0.288 | 0/75 [0.00-0.05] |
| OCCAM ACH, top-5 shortlist | as-is (upper bound) | 0.000 [0.00-0.05] | 0.027 | 0.387 | 0.305 | 0/75 [0.00-0.05] |
| TTP-similarity baseline | leak-controlled | 0.000 [0.00-0.05] | 0.013 | 0.920 | 0.408 | 23/75 [0.21-0.42] |
| OCCAM ACH | leak-controlled | 0.013 [0.00-0.07] | 0.093 | 0.560 | 0.288 | 0/75 [0.00-0.05] |
| OCCAM ACH, top-5 shortlist | leak-controlled | 0.000 [0.00-0.05] | 0.013 | 0.387 | 0.305 | 0/75 [0.00-0.05] |

| Exact McNemar test (same reports) | Correct only first | Correct only second | Both | p (two-sided) |
|---|---|---|---|---|
| ACH vs similarity, as-is | 1 | 0 | 0 | 1.000 |
| ACH vs similarity, leak-controlled | 1 | 0 | 0 | 1.000 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.971 | 0.894 | 0.261 | 57 |
| single-linkage (t=0.3) | 0.986 | 0.877 | 0.053 | 66 |
