### Campaign clustering on ATT&CK activity (test split: 270 events from 36 groups; capability-only)

Hyper-parameters chosen on 239 dev events from 26 disjoint groups.

| Method | Purity | NMI | ARI | #clusters |
|---|---|---|---|---|
| Louvain, IDF-weighted Jaccard kNN graph (k=10, res=5.0; dev-tuned) | 0.522 | 0.657 | 0.242 | 38 |
| Louvain, dense graph (no kNN, res=1.0) | 0.167 | 0.245 | 0.047 | 4 |
| Single-linkage Jaccard (t=0.3; dev-tuned) | 0.800 | 0.694 | 0.107 | 181 |
| Single-linkage Jaccard (default t=0.3) | 0.800 | 0.694 | 0.107 | 181 |
| Trivial: one cluster per event | 1.000 | 0.753 | 0.000 | 270 |
