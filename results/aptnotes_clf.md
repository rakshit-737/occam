### End-to-end on APTnotes (57 real reports, 30 groups; extractor: keyword + classifier)

Mean per report: 44.0 techniques, 2.4 software, 113.2 IOCs (all span-anchored).

| Attributor | Top-1 | Top-5 | Names someone | Brier | Wrong at p>=0.8 |
|---|---|---|---|---|---|
| TTP-similarity baseline | 0.123 | 0.281 | 1.000 | 0.066 | 0.000 |
| OCCAM ACH | 0.053 | 0.228 | 0.228 | 0.280 | 0.000 |
| OCCAM ACH, top-5 shortlist | 0.053 | 0.281 | 0.088 | 0.370 | 0.000 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.877 | 0.888 | 0.344 | 41 |
| single-linkage (t=0.3) | 1.000 | 0.889 | 0.037 | 56 |
