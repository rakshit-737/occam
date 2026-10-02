# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-10-02

### Added
- `scripts/bench_falseflag.py`: false-flag benchmark with an **authentic-marker** control, a **TTP-mimicry** attack, marker-aware baselines (spoofable-blind similarity, IDF coverage, cross-fitted abstention and consistency gate), a marker-boost sweep, one-at-a-time ACH ablations and group-cluster paired CIs (`results/falseflag.md`).
- ACH ablation switches (`false_flag_hypotheses`, `unknown_hypothesis`, `spoofable_discount`, `confidence_caps`, `diagnosticity`) and `IDFCoverageAttributor`.
- Extended evaluation: all 575 report incidents, 21 held-out campaigns, unattributed campaigns (and a clean subset), temporal splits from ATT&CK v12.1 / v15.1 with renamed-id mapping (`results/attribution_extended.md`).
- `scripts/bench_rcatt.py`: reproduction of Legoy et al. (2020) on rcATT's own data and folds (tactic micro F0.5 64.63 vs 65.38 published; technique 35.81 vs 35.02).
- APTnotes: 72 reports, leak-controlled profiles, software-only / techniques-only ablations, Wilson CIs.
- Preprint in `paper/` (built by the `paper` workflow), How it works / Evaluation / Reproduce docs pages, workbench screenshot, `results/datasets.json`.
- CI: Python 3.10-3.14, wheel install + `occam demo` outside the checkout, sdist tests, Docker build + health smoke test, pip-audit, weekly schedule; release gated on CI and docs, image smoke-tested before push, SHA256SUMS + build provenance.
- CODEOWNERS, dependabot, issue/PR templates, CITATION.cff.

### Changed
- Headline claims restated against marker-aware baselines: planted-marker resistance is not specific to ACH; its distinct gain is under mimicry and in declining.
- Attribution CIs use a group-cluster bootstrap; the realistic calibration number is a setting-agnostic (pooled) map (closed-world ACH Brier 0.189, not the per-setting 0.156).
- Temporal splits: correct decline 0.677 -> 0.506 (v12.1) after mapping ids unknown to the old release; release dates corrected.
- APTnotes labels from software "exclusive" to one group are no longer used (circular; FinFisher would be labelled Dark Caracal).
- Clustering benchmark tunes the dense-graph Louvain too (test ARI 0.203 vs 0.249 for kNN).
- UI on vite 8; dependency floors raised above known advisories; SPDX licence metadata.

### Fixed
- `occam demo` failed from any non-editable install (fixtures not packaged); demo data now ships in `occam/demo`.
- ReDoS in the domain and email IOC regexes (69 s on 16 KB of crafted text) and quadratic IOC overlap check.
- README research-question answer and preprint now state that ACH is less well calibrated under a pooled map and that its advantage is mainly auditability; rcATT table citations and the reference-check sentence corrected.
- API: Host allow-list (DNS rebinding), body and field size limits, capped TAXII store, 422 instead of 500 on malformed input, docs UI off by default, optional bearer token.

## [1.0.0] - 2026-09-26

### Added
- `occam.calibration.GradeCalibrator`: a learned, monotone grade-to-probability map (calibrated grader). `bench_attribution.py` fits it cross-fitted by group and ships `results/grade_calibration.json`; `occam attribute --calibration` applies it. Closed-world ACH Brier falls from 0.238 to 0.156.
- Opt-in support-aware ACH ranking (`ACHEngine(ranking_rule="balanced")`), benchmarked against pure Heuer: closed-world top-1 rises from 0.299 to 0.401, but correct declines on untracked actors fall from 0.460 to 0.055, so Heuer stays the default (ADR 0007).
- The false-flag benchmark now runs over 5 framing seeds and reports mean and standard deviation.
- `TechniqueClassifier.hits(top_k=...)` caps classifier techniques per report; `bench_aptnotes.py --top-k` measures it.
- `occam.neo4j.to_cypher` and `occam cluster --cypher FILE`: idempotent Neo4j Cypher export of the Diamond graph and campaigns.
- React/Vite analyst workbench in `ui/` with a live-API mode and a static demo mode (browser-side ranking recomputation, tested against the Python engine).
- MkDocs Material documentation site on GitHub Pages with the static workbench under `/demo/`.
- Release workflow: on `v*` tags, pushes `ghcr.io/rakshit-737/occam` and creates a GitHub Release with the wheel and sdist. `.dockerignore`.

### Fixed
- `occam.__version__` reported 0.1.0; it now matches the package version.
- The clustering benchmarks are now deterministic. The dev/test split in `bench_clustering.py` iterated a set of string ids, so graph node order, and therefore the Louvain result, depended on `PYTHONHASHSEED`: test ARI varied between about 0.22 and 0.27 from run to run. `occam.graph` also sorts feature keys and runs Louvain on integer node labels. The README and results now report the deterministic run, where kNN-Louvain ARI is 0.249, and a regression test runs clustering under three hash seeds.

## [0.2.0] - 2026-09-26

### Added
- **Real data.** `scripts/download_data.py` fetches three datasets, pinned and checksummed:
  - MITRE ATT&CK Enterprise 19.2 STIX;
  - CTID TRAM2 annotated sentences;
  - a filename-labelled APTnotes PDF subset (text-only parsing, bounded by a subprocess timeout).
- `occam.knowledge.AttackData` is a full ATT&CK STIX loader covering techniques, groups, software, campaigns, `uses` and `attributed-to` relationships and procedure examples. It builds one actor profile per ATT&CK group and derives usage-based rarity and commonness.
- `occam.classifier` is a sentence-level TF-IDF + logistic-regression technique classifier trained on ATT&CK procedures (and optionally TRAM2). It emits span-anchored hits.
- `occam.attribution` provides a TTP-similarity baseline and an ACH attributor with an optional similarity shortlist.
- `occam.evaluation` runs the leave-one-report-out attribution benchmark in closed-world, open-world and false-flag settings, with cross-fitted recalibration.
- `occam.metrics` implements P/R/F1, Brier, ECE, reliability bins, purity, NMI and ARI using only the standard library.
- `occam.graph` builds a Diamond-model graph and runs Louvain campaign clustering on a kNN-sparsified IDF-weighted Jaccard graph.
- `occam.api` is a FastAPI service for extraction and for ACH with live cell overrides. It also offers STIX export, a read-only TAXII 2.1 collection and the analyst workbench UI (`occam/web`).
- `occam.stix.validate` performs strict python-stix2 validation of exported bundles.
- New CLI commands: `occam attribute`, `occam train-classifier`, and `--classifier` for `extract`.
- Benchmarks: `scripts/bench_extraction.py`, `bench_attribution.py`, `bench_clustering.py` and `bench_aptnotes.py`. Their results are in `results/`, with a reliability figure in `docs/figures/`.
- Dockerfile and docker-compose (loopback only), optional extras in `pyproject.toml`, ruff linting, a stdlib-only CI job, and tests that run only when the real datasets are present.
- Docs: ADRs in `docs/adr/`, a dataset and licence notes page in `docs/data.md`, CONTRIBUTING and an MIT LICENSE.

### Changed
- ACH diagnosticity now uses real ATT&CK usage statistics:
  - techniques used by ≥30% of groups are rated N (non-diagnostic);
  - techniques used by ≤3 groups are rated CC when they match;
  - a technique that matches only at the parent level is rated N.
- The keyword extractor matches ATT&CK software names case-sensitively, and generic one-word technique names ("At", "Server", "Malware") are no longer used as keywords.
- STIX export escapes pattern values correctly and stores the ACH note content as JSON.

## [0.1.0] - 2026-09-26

### Added
- MVP: span-anchored keyword and regex extraction, union-find campaign clustering, a Heuer ACH engine with mandatory unknown and false-flag hypotheses and confidence caps, STIX 2.1 export, a CLI, and synthetic demo scenarios (clean attribution, Olympic-Destroyer-style false flag, thin evidence).
