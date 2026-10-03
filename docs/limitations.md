# Limitations and roadmap

## Limitations
- **Closed-world accuracy is modest.** Pure Heuer ACH names the right group less often than naive similarity when there is no deception (29.9% vs 53.3%). The support-aware variant reaches 40.1% but gives up declining on untracked actors: correct declines fall from 46.0% to 5.5%.
- **Calibration is not better.** Under one setting-agnostic calibration map, ACH's pooled Brier score is worse than the similarity matcher's: 0.214 vs 0.160, paired difference +0.031 to +0.080 (`results/falseflag.md`). ACH is better only in the closed world.
- **Planted-marker resistance is not specific to ACH.** A baseline that ignores spoofable rows is never framed either, and a consistency gate is correct more often (`results/falseflag.md`).
- **Mimicry is only partly resisted.** Under TTP mimicry, ACH is framed less often than IDF coverage but is correct less often (17.9% vs 28.8%), and the ablation does not tie the difference to its weighting.
- **Declining is better done by a threshold.** A thresholded similarity baseline matched to ACH's closed-world accuracy declines on untracked actors more often than ACH (93.4% vs 46.0%).
- **Auditability is not measured.** ACH's remaining advantage, an inspectable matrix with span-anchored evidence, is a design property; no user study measures it.
- **The cell-rule thresholds were set by hand** (30% of groups for "common", at most 3 groups for "rare"). `results/sensitivity.md` shows how the rates move over a 3 x 3 grid. A cross-fitted choice trades closed-world accuracy for false alarms and mimicry framing.
- **Genuine overlap is sometimes called a frame-up** (18.6% with 3 authentic markers), and ACH rarely names the true actor behind a detected frame (2.2%).
- **The false-flag evaluation uses synthetic markers.** Planted markers and mimicked items are evidence rows, not forged artefacts.
- **Incidents are reported slices of ATT&CK, not telemetry.**
- **APTnotes is small and partly leaky.** It has 75 scored reports. Labels come from file names and titles, and the leak control is a title-matching heuristic.
- **Keyword extractor recall is low.** The classifier over-fires on long reports unless it is capped per report (`--top-k`). Even capped, it lowers ACH's APTnotes accuracy.
- **The API is a lab tool.** It binds to loopback and has an optional bearer token and a Host allow-list, but no users or roles.
- **The static demo** recomputes the ACH ranking in the browser but not the confidence grade, which needs the Python API.

## Not done, and why
- **Real case studies** (Olympic Destroyer, WannaCry, NotPetya, VPNFilter) built from cited public reporting with Admiralty grades. ATT&CK 19.2 has the labels (Sandworm G0034 uses S0365, S0368 and S1010; Lazarus G0032 uses S0366), but every evidence row needs a verified source. The bundled `false_flag_games` scenario only follows the *structure* of Olympic Destroyer.
- **A false-flag hypothesis raised by hard evidence** (mimicry detection): measured as a gap, not implemented.
- **ICS and Mobile ATT&CK.** Every benchmark uses the Enterprise domain only. The ICS and Mobile bundles are not downloaded or evaluated, so no claim is made about them.
- **spaCy entity and relation extraction.** It is a heavy dependency with uncertain wheels for Python 3.14 on this machine, and it needs a labelled relation set to evaluate. The regex and classifier extractors cover IOCs and techniques.
- **LLM extractor.** It needs a hosted or local model and a human-judged set of span-grounded extractions, which cannot be reproduced in CI.
- **Live Neo4j / OpenCTI.** OCCAM emits an idempotent Cypher script (`occam cluster --cypher`). It has not been load-tested against a running Neo4j or OpenCTI instance.
- **Workbench graph view and `/cluster` API endpoint.** Clustering is available from the CLI (`occam cluster`) and the Python API only; the workbench has no graph view yet.
- **Old published artefacts.** Artefacts published before 1.1.0 (the v1.0.0 wheel and the `1.0.0` / `1.0` image tags) lack the packaged demo data and later fixes. Use 1.1.0 or newer; `:latest` is 1.1.0.
- **Persistent TAXII collection.** The TAXII endpoint stays read-only and in-memory until authentication exists.

## Done since 1.1.0
- **Reference verification.** `scripts/check_refs.py` resolves every DOI, arXiv id and URL in `paper/refs.bib` and writes `paper/refs_check.log`. All 13 entries resolve and match.
- **Benchmark re-runs in CI.** The manual `bench` workflow downloads the pinned data on a GitHub-hosted runner, reruns every benchmark and records the run id in each result file. It also lists every value that differs from the committed files.

## Roadmap
- Learn the support weight per setting with an explicit abstention threshold, so the support-aware ranking can still decline.
- spaCy and LLM extractors held to the span contract, evaluated on TRAM2.
- A Neo4j/OpenCTI adapter tested against a container in CI.
- An authenticated, persistent TAXII collection.
