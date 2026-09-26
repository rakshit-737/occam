### End-to-end on APTnotes (57 real reports, 30 groups; extractor: keyword + classifier, top-10 per report)

Mean per report: 12.3 techniques, 2.4 software, 113.2 IOCs (all span-anchored).

| Attributor | Top-1 | Top-5 | Names someone | Brier | Wrong at p>=0.8 |
|---|---|---|---|---|---|
| TTP-similarity baseline | 0.333 | 0.544 | 1.000 | 0.208 | 0.000 |
| OCCAM ACH | 0.193 | 0.368 | 0.579 | 0.255 | 0.000 |
| OCCAM ACH, top-5 shortlist | 0.193 | 0.544 | 0.316 | 0.320 | 0.000 |

| Clustering of the reports | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| louvain (k=10, res=5.0) | 0.965 | 0.898 | 0.226 | 49 |
| single-linkage (t=0.3) | 1.000 | 0.889 | 0.037 | 56 |
