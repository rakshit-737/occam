### End-to-end on APTnotes (72 real reports, 31 groups; extractor: keyword)

Mean per report: 3.5 techniques, 2.4 software, 103.0 IOCs (all span-anchored). Evidence used: all. 3 reports with nothing extracted are scored as declines. 22 of 72 reports matched an ATT&CK citation of their own group (held out in the leak-controlled rows).

| Attributor | Profiles | Top-1 [Wilson 95%] | Top-5 | Names someone | Brier | Wrong at p>=0.8 |
|---|---|---|---|---|---|---|
| TTP-similarity baseline | as-is (upper bound) | 0.292 [0.20-0.41] | 0.514 | 0.958 | 0.345 | 9/72 |
| OCCAM ACH | as-is (upper bound) | 0.361 [0.26-0.48] | 0.486 | 0.847 | 0.216 | 0/72 |
| OCCAM ACH, top-5 shortlist | as-is (upper bound) | 0.347 [0.25-0.46] | 0.514 | 0.639 | 0.226 | 0/72 |
| TTP-similarity baseline | leak-controlled | 0.264 [0.18-0.38] | 0.486 | 0.958 | 0.347 | 9/72 |
| OCCAM ACH | leak-controlled | 0.319 [0.22-0.43] | 0.458 | 0.833 | 0.230 | 0/72 |
| OCCAM ACH, top-5 shortlist | leak-controlled | 0.292 [0.20-0.41] | 0.486 | 0.583 | 0.244 | 0/72 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.971 | 0.886 | 0.244 | 56 |
| single-linkage (t=0.3) | 0.986 | 0.870 | 0.068 | 65 |
