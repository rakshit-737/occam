### End-to-end on APTnotes (75 real reports, 33 groups; extractor: keyword + classifier, top-10 per report)

*Source: GitHub Actions run [37093689060](https://github.com/rakshit-737/occam/actions/runs/37093689060), commit `09cde53`, 2026-10-03T03:42:20+00:00.*

Mean per report: 12.5 techniques, 2.5 software, 102.4 IOCs (all span-anchored). Evidence used: all. 0 reports with nothing extracted are scored as declines. 23 of 75 reports matched an ATT&CK citation of their own group (held out in the leak-controlled rows). 33 groups among the reports with extracted items (clustered below). Skipped: 1 (2014/h12756-wp-shell-crew.pdf: excluded: its converted text quotes webshell code and is quarantined by Windows Defender on the author's machine; skipped everywhere so local and CI runs match).

| Attributor | Profiles | Top-1 [Wilson 95%] | Top-5 | Names someone | Brier | Wrong at p>=0.8 [Wilson 95%] |
|---|---|---|---|---|---|---|
| TTP-similarity baseline | as-is (upper bound) | 0.333 [0.24-0.45] | 0.507 | 1.000 | 0.194 | 0/75 [0.00-0.05] |
| OCCAM ACH | as-is (upper bound) | 0.187 [0.11-0.29] | 0.387 | 0.573 | 0.248 | 0/75 [0.00-0.05] |
| OCCAM ACH, top-5 shortlist | as-is (upper bound) | 0.187 [0.11-0.29] | 0.507 | 0.280 | 0.315 | 0/75 [0.00-0.05] |
| TTP-similarity baseline | leak-controlled | 0.293 [0.20-0.40] | 0.467 | 1.000 | 0.211 | 0/75 [0.00-0.05] |
| OCCAM ACH | leak-controlled | 0.160 [0.09-0.26] | 0.347 | 0.547 | 0.255 | 0/75 [0.00-0.05] |
| OCCAM ACH, top-5 shortlist | leak-controlled | 0.120 [0.06-0.21] | 0.467 | 0.213 | 0.327 | 0/75 [0.00-0.05] |

| Exact McNemar test (same reports) | Correct only first | Correct only second | Both | p (two-sided) |
|---|---|---|---|---|
| ACH vs similarity, as-is | 6 | 17 | 8 | 0.035 |
| ACH vs similarity, leak-controlled | 7 | 17 | 5 | 0.064 |
| ach (this run) vs aptnotes, leak-controlled | 0 | 12 | 12 | 4.9e-04 |
| similarity (this run) vs aptnotes, leak-controlled | 5 | 4 | 17 | 1.000 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.920 | 0.866 | 0.217 | 58 |
| single-linkage (t=0.3) | 1.000 | 0.869 | 0.041 | 73 |
