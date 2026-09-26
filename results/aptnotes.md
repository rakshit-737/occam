### End-to-end on APTnotes (54 real reports, 29 groups; extractor: keyword)

Mean per report: 3.7 techniques, 2.5 software, 119.3 IOCs (all span-anchored).

| Attributor | Top-1 | Top-5 | Names someone | Brier | Wrong at p>=0.8 |
|---|---|---|---|---|---|
| TTP-similarity baseline | 0.370 | 0.574 | 1.000 | 0.371 | 0.111 |
| OCCAM ACH | 0.370 | 0.481 | 0.852 | 0.214 | 0.000 |
| OCCAM ACH, top-5 shortlist | 0.352 | 0.574 | 0.667 | 0.222 | 0.000 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 1.000 | 0.910 | 0.258 | 48 |
| single-linkage (t=0.3) | 1.000 | 0.896 | 0.081 | 52 |
