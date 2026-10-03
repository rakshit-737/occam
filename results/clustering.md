### Campaign clustering on ATT&CK activity (test split: 270 events from 36 groups; capability-only)

Hyper-parameters chosen on 239 dev events from 26 disjoint groups (dev ARI: kNN 0.369, dense 0.373). Brackets: 95% leave-one-group-out jackknife interval with each clustering held fixed (sampling variation of the test set only; estimate +- 1.96 SE).

*Source: GitHub Actions run [37093689060](https://github.com/rakshit-737/occam/actions/runs/37093689060), commit `09cde53`, 2026-10-03T03:35:51+00:00.*

| Method | Purity [95% CI] | NMI [95% CI] | ARI [95% CI] | #clusters |
|---|---|---|---|---|
| Louvain, IDF-weighted Jaccard kNN graph (k=10, res=5.0; dev-tuned) | 0.511 [0.44-0.58] | 0.642 [0.60-0.69] | 0.249 [0.17-0.32] | 37 |
| Louvain, dense graph (no kNN, res=5.0; dev-tuned) | 0.659 [0.57-0.75] | 0.705 [0.66-0.75] | 0.203 [0.14-0.26] | 84 |
| Louvain, dense graph (no kNN, default res=1.0) | 0.178 [0.09-0.26] | 0.255 [0.18-0.33] | 0.047 [-0.00-0.10] | 4 |
| Single-linkage Jaccard (t=0.3; dev-tuned = default) | 0.800 [0.71-0.89] | 0.694 [0.64-0.75] | 0.107 [-0.03-0.25] | 181 |
| Trivial: one cluster per event | 1.000 [1.00-1.00] | 0.753 [0.72-0.79] | 0.000 [0.00-0.00] | 270 |

ARI, kNN minus dense graph (paired jackknife, 95%): [-0.019, +0.110]. Louvain depends on input order: the selected kNN configuration on 10 random permutations of the test events gives ARI 0.248 ± 0.013 (sample SD; range 0.228-0.267).
