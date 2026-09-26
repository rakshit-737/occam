# Limitations and roadmap

## Limitations
- **Closed-world accuracy is modest.** Pure Heuer ACH names the right group less often than naive similarity when there is no deception (30% vs 53%). The support-aware variant reaches 40% but gives up declining on untracked actors (46% to 5.5%).
- **The false-flag evaluation uses synthetic markers.** Planted markers are evidence rows, not forged artefacts.
- **Incidents are reported slices of ATT&CK, not telemetry.**
- **APTnotes numbers are optimistic.** Profiles are partly built from these reports, labels come from filenames, and there are only 54-57 reports.
- **Keyword extractor recall is low.** The classifier over-fires on long reports unless it is capped per report (`--top-k`).
- **The API has no authentication.** It is for local lab use only, and docker-compose binds it to 127.0.0.1.
- **The static demo** recomputes the ACH ranking in the browser but not the confidence grade, which needs the Python API.

## Not done, and why
- **spaCy entity and relation extraction.** It is a heavy dependency with uncertain wheels for Python 3.14 on this machine, and it needs a labelled relation set to evaluate. The regex and classifier extractors cover IOCs and techniques.
- **LLM extractor.** It needs a hosted or local model and a human-judged set of span-grounded extractions, which cannot be reproduced in CI.
- **Live Neo4j / OpenCTI.** OCCAM now emits an idempotent Cypher script (`occam cluster --cypher`). It has not been load-tested against a running Neo4j or OpenCTI instance.
- **Persistent TAXII collection.** The TAXII endpoint stays read-only and in-memory until authentication exists.

## Roadmap
- Learn the support weight per setting with an explicit abstention threshold, so the support-aware ranking can still decline.
- spaCy and LLM extractors held to the span contract, evaluated on TRAM2.
- A Neo4j/OpenCTI adapter tested against a container in CI.
- An authenticated, persistent TAXII collection.
