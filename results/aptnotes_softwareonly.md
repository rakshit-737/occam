### End-to-end on APTnotes (72 real reports, 25 groups; extractor: keyword)

Mean per report: 3.5 techniques, 2.4 software, 103.0 IOCs (all span-anchored). Evidence used: software. 15 reports with nothing extracted are scored as declines. 22 of 72 reports matched an ATT&CK citation of their own group (held out in the leak-controlled rows).

| Attributor | Profiles | Top-1 [Wilson 95%] | Top-5 | Names someone | Brier | Wrong at p>=0.8 |
|---|---|---|---|---|---|---|
| TTP-similarity baseline | as-is (upper bound) | 0.500 [0.39-0.61] | 0.556 | 0.792 | 0.329 | 1/72 |
| OCCAM ACH | as-is (upper bound) | 0.472 [0.36-0.59] | 0.542 | 0.764 | 0.206 | 0/72 |
| OCCAM ACH, top-5 shortlist | as-is (upper bound) | 0.500 [0.39-0.61] | 0.556 | 0.764 | 0.203 | 0/72 |
| TTP-similarity baseline | leak-controlled | 0.472 [0.36-0.59] | 0.542 | 0.792 | 0.338 | 1/72 |
| OCCAM ACH | leak-controlled | 0.444 [0.34-0.56] | 0.528 | 0.750 | 0.218 | 0/72 |
| OCCAM ACH, top-5 shortlist | leak-controlled | 0.472 [0.36-0.59] | 0.542 | 0.750 | 0.215 | 0/72 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.982 | 0.878 | 0.219 | 47 |
| single-linkage (t=0.3) | 1.000 | 0.864 | 0.080 | 54 |
