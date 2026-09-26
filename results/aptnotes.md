### End-to-end on APTnotes (57 real reports, 30 groups; extractor: keyword)

Mean per report: 15.4 techniques, 2.4 software, 113.2 IOCs (all span-anchored).

| Attributor | Top-1 | Top-5 | Names someone | Brier | Wrong at p>=0.8 |
|---|---|---|---|---|---|
| TTP-similarity baseline | 0.193 | 0.421 | 1.000 | 0.139 | 0.000 |
| OCCAM ACH | 0.140 | 0.246 | 0.930 | 0.256 | 0.000 |
| OCCAM ACH, top-5 shortlist | 0.158 | 0.421 | 0.491 | 0.308 | 0.018 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.965 | 0.901 | 0.254 | 48 |
| single-linkage (t=0.3) | 0.912 | 0.868 | 0.099 | 48 |
