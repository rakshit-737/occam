# Reproduce

Every result file in [`results/`](https://github.com/rakshit-737/occam/tree/main/results) is written by one script. Runtimes are the `runtime_s` recorded in each JSON, measured on the author's laptop (Intel i5-13500H, 16 GB RAM, Windows 11, Python 3.14), sometimes with other benchmarks running in parallel. All randomness is seeded; dataset commits and SHA-256 hashes are pinned in `scripts/download_data.py`, and `python scripts/dataset_stats.py` writes the dataset counts quoted in the docs to `results/datasets.json`.

## 0. Setup

```bash
git clone https://github.com/rakshit-737/occam && cd occam
python -m pip install -e ".[dev,pdf,bench]" nltk
python scripts/download_data.py          # ~400 MB into ../../datasets/occam (or $OCCAM_DATA), ~15 min
python scripts/dataset_stats.py          # -> results/datasets.json
```

`bench_rcatt.py` also needs the NLTK data packages `stopwords`, `punkt_tab`, `wordnet` and `omw-1.4` in `$OCCAM_DATA/nltk_data` (download them with `nltk.download(name, download_dir=...)`).

## 1. Benchmarks

| Script | Writes | Key expected numbers | Runtime |
| --- | --- | --- | --- |
| `python scripts/bench_falseflag.py` | `results/falseflag.{json,md}` | framed under planted markers: naive 0.880, ACH 0.011, spoofable-blind 0.000; mimicry framed: ACH 0.270 vs 0.763; authentic false alarm 0.186 | 757 s |
| `python scripts/bench_attribution.py` | `results/attribution.{json,md}`, `results/grade_calibration.json`, `docs/figures/attribution_reliability.png` | closed top-1 0.533 vs 0.299; open decline 0.460; false-flag framed 0.880 vs 0.011; pooled-map closed Brier 0.189 | 224 s |
| `python scripts/bench_attribution_extended.py` | `results/attribution_extended.{json,md}` | loro-all 575 incidents: closed 0.478 vs 0.390; temporal-12.1 open decline 0.506 | 765 s (sum of protocols) |
| `python scripts/bench_rcatt.py` | `results/rcatt_reproduction.{json,md}` | tactics micro F0.5: paper 65.38, released pipeline 64.63; techniques 35.02 vs 35.81 | 1320 s |
| `python scripts/bench_extraction.py` | `results/extraction.{json,md}` | TRAM2 doc micro-F1 0.710 ± 0.023 (ATT&CK + TRAM), 0.618 (ATT&CK only), 0.388 (keyword) | 320 s |
| `python scripts/bench_clustering.py` | `results/clustering.{json,md}` | test ARI: kNN-Louvain 0.249, tuned dense 0.203, single linkage 0.107 | 101 s |
| `python scripts/bench_aptnotes.py` | `results/aptnotes.{json,md}` | 72 reports; leak-controlled top-1 ACH 0.319, similarity 0.264; wrong at p >= 0.8: 0 vs 9 | 492 s |
| `python scripts/bench_aptnotes.py --evidence software` | `results/aptnotes_softwareonly.*` | leak-controlled top-1 similarity 0.472, ACH 0.444 | 601 s |
| `python scripts/bench_aptnotes.py --evidence techniques` | `results/aptnotes_techniquesonly.*` | top-1 near 0 for both: techniques alone carry almost no signal | 261 s |
| `python scripts/bench_aptnotes.py --model model.pkl --top-k 10` | `results/aptnotes_clf_top10.*` | leak-controlled top-1 similarity 0.278, ACH 0.167 (the classifier hurts) | 471 s |
| `occam train-classifier --attack ... --tram ... --out model.pkl` | a ~340 MB pickle (never committed) | 48-50 technique classes | ~26 min |

## 2. Tests, lint and docs

```bash
python -m pytest -q                      # 80+ tests; real-data tests run when the datasets exist
python -m ruff check .
python -m mkdocs build --strict
cd ui && npm ci && npm test && npm run build
```

## 3. Preprint

```bash
cd paper && latexmk -pdf occam.tex       # MiKTeX or TeX Live
```
