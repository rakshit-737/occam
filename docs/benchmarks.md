# Benchmarks and results

All numbers come from `python scripts/bench_*.py` on the pinned datasets; the raw JSON is in [`results/`](https://github.com/rakshit-737/occam/tree/main/results). The tables below are included verbatim from those files.

## 1. Attribution on held-out ATT&CK group usage

274 leave-one-report-out incidents from 103 groups ([ADR 0004](adr/0004-leave-one-report-out-evaluation.md)). **closed**: the true group is a candidate. **open**: it is removed, so the right answer is to decline. **false_flag**: 3 spoofable markers frame a random other group. The 95% CIs are bootstrap intervals over incidents.

--8<-- "results/attribution.md"

![Reliability diagram](figures/attribution_reliability.png)

How to read this:

- Under false flags the baseline names the framed group 88% of the time; ACH does so about 1% of the time, and that is stable across 5 framing seeds.
- Without deception, pure-Heuer ACH names the right group less often (30% vs 53%). The **support-aware** ranking narrows this to 40% and names the true group behind a false flag 13% of the time instead of 2%. But it almost never declines when the true group is untracked (5.5% vs 46%), because consistent evidence always favours *some* named actor. That is why it is not the default.
- The **learned grade map** fixes ACH's over-optimistic ICD-203 midpoints: closed-world Brier drops from 0.238 to 0.156 (cross-fitted), better than the baseline's 0.179.

## 2. TTP extraction on TRAM2

--8<-- "results/extraction.md"

## 3. Campaign clustering

--8<-- "results/clustering.md"

## 4. End-to-end on APTnotes

This check is optimistic by construction, because ATT&CK profiles are partly built from these reports.

--8<-- "results/aptnotes.md"

--8<-- "results/aptnotes_clf.md"

--8<-- "results/aptnotes_clf_top10.md"
