# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.1] - 2026-10-03

### Added
- `scripts/check_refs.py` resolves every DOI, arXiv id and URL in `paper/refs.bib` and writes `paper/refs_check.log` (13 of 13 resolve and match). It adds a DOI or URL for Brier, Guo, Heuer, Caltagirone and Strom, and cites Nunes et al. (2015, 2016) on attribution under deception.
- Every result JSON has a `provenance` block (commit, dirty flag, command, package versions, input sha256, GitHub run id), and every table names its source run. A manual `bench` workflow regenerates all results on a GitHub runner and diffs them against the committed files. All committed results now come from bench run 37093689060.
- `bench_falseflag.py` adds:
  - paired group-cluster intervals for the pooled-map Brier score (ACH minus each method, pooled and per setting);
  - overconfident errors under the pooled map;
  - abstention baselines cross-fitted to ACH's decline rate and to its closed-world accuracy, plus the abstention-frontier figure;
  - every paired column, and calibration columns in the ablation table;
  - the marker-boost 0.3 row.
- `scripts/bench_sensitivity.py`: a 3 x 3 grid of the hand-set cell-rule thresholds, plus a cross-fitted choice.
- rcATT 2 x 2 ablation of tokenisation and class weighting; exact McNemar tests in the APTnotes results (including classifier vs keyword extraction); group-jackknife intervals for clustering.
- Preprint: a Discussion and conclusion that answer the research question, intervals and a mimicry-correct column in Table 1, the abstention figure, and threshold sensitivity. The PDF is published at <https://rakshit-737.github.io/occam/preprint.pdf> and attached to future releases.
- Both workbenches have an API-token field; `POST /stix` accepts inline actors and evidence.

### Changed
- The docs home, Evaluation page, threat model and the 1.1.0 entry below no longer claim that ACH's advantage lies in resisting mimicry and in declining. Under mimicry ACH is correct less often than IDF coverage (17.9% vs 28.8%). An abstaining baseline declines more at the same closed-world accuracy (93.4% vs 46.0%). ACH's remaining advantage is mainly auditability.
- The README answers the overconfidence half of the research question separately for raw outputs (0/274 vs 194/274 wrong at p >= 0.8 under planted markers) and recalibrated ones (1/822 vs 0/822), and names the comparator for every claim.
- rcATT: the "released pipeline" row now matches rcATT's `train()` exactly (one chi2 selection over all labels, rcATT's extra stop words, no tactics `min_df`). Tactics change from 64.63 to 64.82 and techniques from 35.81 to 36.33. Paper numbers are cited as arXiv:2004.14322v1 Table 4, "Inde." rows.
- APTnotes results now come from a GitHub runner, where three PDFs that timed out locally converted: 75 reports instead of 72. Leak-controlled top-1 is ACH 0.320 vs similarity 0.280 (was 0.319 vs 0.264), and McNemar p is 0.66 (was 0.50). ACH's margin is smaller.
- Rates of exactly 0 or 1 get a Wilson interval with the number of groups as the sample size, instead of a degenerate [0.00-0.00]. Fold SDs are labelled as dispersion.

### Fixed
- With `OCCAM_API_TOKEN` set, `GET /health` and the workbench page returned 401, so the Docker HEALTHCHECK failed. Both now stay open; every API call still needs the token.
- Assessment-only STIX bundles referenced a report object that was not in the bundle.
- `dataset_stats.py --help` and `export_demo.py --help` ran the scripts.
- Docs builds for pull requests shared the Pages concurrency group and cancelled each other.
- setuptools warned about undeclared demo-data packages. The release image job now attests the pushed image.
- Numbers without a committed source were removed: the old temporal-split decline rate ("0.68" / "67.7%") and the ReDoS timings ("69 s on 16 KB", "8 s per MB").
### Build
- `make bench` runs the same set as the `bench` workflow; new `make refs`.
- Dependency floors raised: httpx 0.28.1, networkx 3.4.2, matplotlib 3.10.9, mkdocstrings 1.0.6, setuptools 84.

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
- Headline claims restated against marker-aware baselines: planted-marker resistance is not specific to ACH. Under mimicry ACH is framed less often but is correct less often, and an abstaining baseline declines more often (wording corrected after release; see 1.1.1).
- Attribution CIs use a group-cluster bootstrap; the realistic calibration number is a setting-agnostic (pooled) map (closed-world ACH Brier 0.189, not the per-setting 0.156).
- Temporal splits: correct decline is 0.506 (v12.1) after mapping ids unknown to the old release; release dates corrected.
- APTnotes labels from software "exclusive" to one group are no longer used (circular; FinFisher would be labelled Dark Caracal).
- Clustering benchmark tunes the dense-graph Louvain too (test ARI 0.203 vs 0.249 for kNN).
- UI on vite 8; dependency floors raised above known advisories; SPDX licence metadata.

### Fixed
- `occam demo` failed from any non-editable install (fixtures not packaged); demo data now ships in `occam/demo`.
- ReDoS in the domain and email IOC regexes (nested unbounded repeats) and quadratic IOC overlap check.
- The README research-question answer states that ACH is less well calibrated under a pooled map and that its advantage is mainly auditability (the preprint only gained this in 1.1.1). The unverified rcATT table number was removed (Table 4 is cited from 1.1.1 on), and the preprint's reference-check sentence was softened.
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
