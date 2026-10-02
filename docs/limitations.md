# Limitations and roadmap

## Limitations
- **Closed-world accuracy is modest.** Pure Heuer ACH names the right group less often than naive similarity when there is no deception (30% vs 53%). The support-aware variant reaches 40% but gives up declining on untracked actors (46% to 5.5%).
- **Planted-marker resistance is not specific to ACH.** A baseline that ignores spoofable rows is never framed either, and a consistency gate is correct more often (`results/falseflag.md`). Under TTP mimicry ACH is framed less often but is correct less often, and the ablation does not tie that to its weighting; a thresholded similarity baseline declines on untracked actors more often than ACH at similar closed-world accuracy.
- **Genuine overlap is sometimes called a frame-up** (18.6% with 3 authentic markers), and ACH rarely names the true actor behind a detected frame (2%).
- **The false-flag evaluation uses synthetic markers.** Planted markers and mimicked items are evidence rows, not forged artefacts.
- **Incidents are reported slices of ATT&CK, not telemetry.**
- **APTnotes is small and partly leaky.** 72 reports; labels come from file names and titles; the leak control is a title-matching heuristic.
- **Keyword extractor recall is low.** The classifier over-fires on long reports unless it is capped per report (`--top-k`).
- **The API is a lab tool.** It binds to loopback and has an optional bearer token and a Host allow-list, but no users or roles.
- **The static demo** recomputes the ACH ranking in the browser but not the confidence grade, which needs the Python API.

## Not done, and why
- **Real case studies** (Olympic Destroyer, WannaCry, NotPetya, VPNFilter) built from cited public reporting with Admiralty grades. ATT&CK 19.2 has the labels (Sandworm G0034 uses S0365, S0368 and S1010; Lazarus G0032 uses S0366), but every evidence row needs a verified source; the bundled `false_flag_games` scenario only follows the *structure* of Olympic Destroyer.
- **A false-flag hypothesis raised by hard evidence** (mimicry detection): measured as a gap, not implemented.
- **ICS and Mobile ATT&CK**: too few held-out incidents (ICS: 1 report incident and 3 campaigns; Mobile: none), so no claim is made.
- **spaCy entity and relation extraction.** It is a heavy dependency with uncertain wheels for Python 3.14 on this machine, and it needs a labelled relation set to evaluate. The regex and classifier extractors cover IOCs and techniques.
- **LLM extractor.** It needs a hosted or local model and a human-judged set of span-grounded extractions, which cannot be reproduced in CI.
- **Live Neo4j / OpenCTI.** OCCAM now emits an idempotent Cypher script (`occam cluster --cypher`). It has not been load-tested against a running Neo4j or OpenCTI instance.
- **Persistent TAXII collection.** The TAXII endpoint stays read-only and in-memory until authentication exists.

## Roadmap
- Learn the support weight per setting with an explicit abstention threshold, so the support-aware ranking can still decline.
- spaCy and LLM extractors held to the span contract, evaluated on TRAM2.
- A Neo4j/OpenCTI adapter tested against a container in CI.
- An authenticated, persistent TAXII collection.
