# Reproduce

Each result file in [`results/`](https://github.com/rakshit-737/occam/tree/main/results) is written by one script. Every JSON has a `provenance` block with the code commit, a dirty flag, the command, package versions, input checksums and, when it ran in GitHub Actions, the run id and URL. Each Markdown table names that run on its source line.

The committed results come from bench run [37093689060](https://github.com/rakshit-737/occam/actions/runs/37093689060), an ubuntu-24.04 GitHub-hosted runner with Python 3.12. All randomness is seeded. Dataset commits and SHA-256 hashes are pinned in `scripts/download_data.py`, and `python scripts/dataset_stats.py` writes the dataset counts quoted in the docs to `results/datasets.json`.

## 0. Rerun everything in GitHub Actions

Actions -> **bench** -> *Run workflow*, or:

```bash
gh workflow run bench.yml                       # all benchmarks
gh workflow run bench.yml -f only="falseflag sensitivity"
```

The workflow:

1. downloads the pinned data once (cached between runs);
2. runs each benchmark in its own job;
3. uploads the outputs as the `bench-results` artefact;
4. writes a job summary listing every value that differs from the committed `results/` files.

## 1. Setup for a local run

```bash
git clone https://github.com/rakshit-737/occam && cd occam
python -m pip install -e ".[dev,pdf,bench]" nltk
python scripts/download_data.py          # ~400 MB into ../../datasets/occam (or $OCCAM_DATA), ~15 min
python scripts/dataset_stats.py          # -> results/datasets.json
```

`bench_rcatt.py` also needs the NLTK data packages `stopwords`, `punkt_tab`, `wordnet` and `omw-1.4` in `$OCCAM_DATA/nltk_data`. Download them with `nltk.download(name, download_dir=...)`.

## 2. Benchmarks

Runtimes are the `runtime_s` recorded in each JSON on the GitHub runner. On the author's laptop (i5-13500H, 16 GB, Windows 11, Python 3.14, often shared with other jobs) they were 3-8 times longer.

| Script | Writes | Key expected numbers | Runtime |
| --- | --- | --- | --- |
| `python scripts/bench_falseflag.py` | `results/falseflag.{json,md}`, `docs/figures/abstention_frontier.png` | framed under planted markers: naive 0.880, ACH 0.011, spoofable-blind 0.000; mimicry framed 0.270 vs 0.763; pooled Brier 0.214 vs 0.160 (paired +0.031 to +0.080) | 106 s |
| `python scripts/bench_sensitivity.py` | `results/sensitivity.{json,md}` | shipped thresholds closed 0.299 / open 0.460; cross-fitted choice c0.2 | 42 s |
| `python scripts/bench_attribution.py` | `results/attribution.{json,md}`, `results/grade_calibration.json`, `docs/figures/attribution_reliability.png` | closed top-1 0.533 vs 0.299; open decline 0.460; pooled-map closed Brier 0.189 | 40 s |
| `python scripts/bench_attribution_extended.py` | `results/attribution_extended.{json,md}` | loro-all 575 incidents: closed 0.478 vs 0.390; temporal-12.1 open decline 0.506 | 103 s (sum of protocols) |
| `python scripts/bench_rcatt.py` | `results/rcatt_reproduction.{json,md}` | tactics micro F0.5: paper 65.38, released code 64.82; techniques 35.02 vs 36.33 | 442 s |
| `python scripts/bench_extraction.py` | `results/extraction.{json,md}` | TRAM2 doc micro-F1 0.710 (CI 0.680-0.738), 0.618 (ATT&CK only), 0.388 (keyword) | 63 s |
| `python scripts/bench_clustering.py` | `results/clustering.{json,md}` | test ARI: kNN-Louvain 0.249, tuned dense 0.203, single linkage 0.107 | 12 s |
| `python scripts/bench_aptnotes.py` | `results/aptnotes.{json,md}` | 75 reports; leak-controlled top-1 ACH 0.320, similarity 0.280 (McNemar p = 0.66); wrong at p >= 0.8: 0 vs 9 | 88 s |
| `python scripts/bench_aptnotes.py --evidence software` | `results/aptnotes_softwareonly.*` | leak-controlled top-1 similarity 0.480, ACH 0.453 | 88 s |
| `python scripts/bench_aptnotes.py --evidence techniques` | `results/aptnotes_techniquesonly.*` | top-1 near 0 for both: techniques alone carry almost no signal | 88 s |
| `occam train-classifier --attack ... --tram ... --out model.pkl` | a ~340 MB pickle (never committed) | 48-50 technique classes | ~26 min on the laptop |
| `python scripts/bench_aptnotes.py --model model.pkl --top-k 10 --paired-with results/aptnotes.json` | `results/aptnotes_clf_top10.*` | leak-controlled top-1 similarity 0.293, ACH 0.160; ACH vs keyword ACH: 0 gained, 12 lost (McNemar p = 0.0005) | 91 s |

`bench_falseflag.py --render` and `bench_aptnotes.py --render results/aptnotes.json` rebuild the Markdown (and the frontier figure) from an existing JSON without rerunning. `python scripts/compare_results.py NEW_DIR results` diffs a fresh run against the committed files.

## 3. References

```bash
python scripts/check_refs.py             # resolves every DOI / arXiv id / URL in paper/refs.bib -> paper/refs_check.log
```

## 4. Tests, lint and docs

```bash
python -m pytest -q                      # 80+ tests; real-data tests run when the datasets exist
python -m ruff check .
python -m mkdocs build --strict
cd ui && npm ci && npm test && npm run build
```

## 5. Preprint

```bash
cd paper && latexmk -pdf occam.tex       # MiKTeX or TeX Live
```

The docs workflow builds the same PDF and publishes it at <https://rakshit-737.github.io/occam/preprint.pdf>.
