### End-to-end on APTnotes (72 real reports, 32 groups; extractor: keyword + classifier, top-10 per report)

Mean per report: 12.4 techniques, 2.4 software, 103.0 IOCs (all span-anchored). Evidence used: all. 0 reports with nothing extracted are scored as declines. 22 of 72 reports matched an ATT&CK citation of their own group (held out in the leak-controlled rows).

| Attributor | Profiles | Top-1 [Wilson 95%] | Top-5 | Names someone | Brier | Wrong at p>=0.8 |
|---|---|---|---|---|---|---|
| TTP-similarity baseline | as-is (upper bound) | 0.306 [0.21-0.42] | 0.486 | 1.000 | 0.197 | 0/72 |
| OCCAM ACH | as-is (upper bound) | 0.194 [0.12-0.30] | 0.389 | 0.583 | 0.248 | 0/72 |
| OCCAM ACH, top-5 shortlist | as-is (upper bound) | 0.194 [0.12-0.30] | 0.486 | 0.292 | 0.327 | 0/72 |
| TTP-similarity baseline | leak-controlled | 0.278 [0.19-0.39] | 0.458 | 1.000 | 0.217 | 0/72 |
| OCCAM ACH | leak-controlled | 0.167 [0.10-0.27] | 0.347 | 0.569 | 0.255 | 0/72 |
| OCCAM ACH, top-5 shortlist | leak-controlled | 0.125 [0.07-0.22] | 0.458 | 0.222 | 0.338 | 0/72 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.917 | 0.869 | 0.237 | 55 |
| single-linkage (t=0.3) | 1.000 | 0.867 | 0.042 | 70 |
