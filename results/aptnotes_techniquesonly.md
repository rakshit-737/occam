### End-to-end on APTnotes (72 real reports, 30 groups; extractor: keyword)

Mean per report: 3.5 techniques, 2.4 software, 103.0 IOCs (all span-anchored). Evidence used: techniques. 6 reports with nothing extracted are scored as declines. 22 of 72 reports matched an ATT&CK citation of their own group (held out in the leak-controlled rows).

| Attributor | Profiles | Top-1 [Wilson 95%] | Top-5 | Names someone | Brier | Wrong at p>=0.8 |
|---|---|---|---|---|---|---|
| TTP-similarity baseline | as-is (upper bound) | 0.000 [0.00-0.05] | 0.028 | 0.917 | 0.410 | 22/72 |
| OCCAM ACH | as-is (upper bound) | 0.014 [0.00-0.07] | 0.097 | 0.556 | 0.287 | 0/72 |
| OCCAM ACH, top-5 shortlist | as-is (upper bound) | 0.000 [0.00-0.05] | 0.028 | 0.389 | 0.301 | 0/72 |
| TTP-similarity baseline | leak-controlled | 0.000 [0.00-0.05] | 0.014 | 0.917 | 0.410 | 22/72 |
| OCCAM ACH | leak-controlled | 0.014 [0.00-0.07] | 0.097 | 0.556 | 0.287 | 0/72 |
| OCCAM ACH, top-5 shortlist | leak-controlled | 0.000 [0.00-0.05] | 0.014 | 0.389 | 0.301 | 0/72 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.970 | 0.890 | 0.264 | 54 |
| single-linkage (t=0.3) | 0.985 | 0.872 | 0.054 | 63 |
