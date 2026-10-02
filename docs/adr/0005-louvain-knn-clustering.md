# ADR 0005: Louvain on a kNN-sparsified Diamond event graph for campaign clustering

- Status: accepted
- Date: 2026-09-26

## Context
The MVP clustered reports with unweighted Jaccard and single linkage (union-find). On real ATT&CK activity, generic techniques overlap between almost all events. Single linkage then chains unrelated events together at low thresholds and shatters campaigns at high ones. Louvain on the dense similarity graph collapses everything into 2-4 giant communities (test ARI 0.047).

## Decision
- Events live in a Diamond-model graph (`occam.graph.build_diamond_graph`) with event, adversary, capability, infrastructure and victim nodes.
- The event-event similarity is IDF-weighted Jaccard over capabilities and infrastructure. Infrastructure is weighted 3x, and features present in every event are dropped.
- Each event keeps only its **k strongest edges**, then Louvain community detection runs on that graph.
- `k` and the resolution are tuned on dev groups (even ATT&CK G-numbers) and reported on disjoint test groups (odd G-numbers). The selected values are k = 10 and resolution 5.0.
- Single linkage stays in the code as the baseline.

## Consequences
- On the test split (results/clustering.md), ARI goes from 0.107 (single linkage) to 0.249. A dense graph tuned on the same dev data reaches 0.203, and on dev it scores 0.373 vs 0.369 for kNN, so the dev data alone does not justify kNN sparsification; the 0.249 vs 0.203 test gap is one run (input-order spread is reported in the same file). (v0.2 reported 0.242 and, on 57 APTnotes reports, 0.099 -> 0.254.)
- Purity and NMI reward over-segmentation: one cluster per event scores purity 1.0. ARI is therefore the headline metric.
- A similar TTP-similarity shortlist is also offered in front of ACH (`ACHAttributor(shortlist=k)`): "similarity proposes, ACH disposes". Actors that spoofable markers point at are always added, so the false-flag hypothesis is never dropped.
