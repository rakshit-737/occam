# Getting started

## Install

```bash
git clone https://github.com/rakshit-737/occam && cd occam
python -m pip install -e ".[dev,pdf,bench]"   # the core alone (pip install -e .) has zero dependencies
python -m pytest -q                            # real-data tests skip when the datasets are absent
python -m occam demo                           # synthetic scenarios, incl. an Olympic-Destroyer-style false flag
```

Or run the API and workbench in a container. It is published on loopback only, because the API has no authentication:

```bash
docker compose up --build                      # http://127.0.0.1:8000/
docker run --rm -p 127.0.0.1:8000:8000 ghcr.io/rakshit-737/occam:latest
```

## Synthetic scenarios

```bash
python -m occam ach occam/demo/scenarios/false_flag_games.json
python -m occam ach occam/demo/scenarios/clean_attribution.json --override E1:H-QUILL=II --json
python -m occam ach occam/demo/scenarios/false_flag_games.json --stix
python -m occam extract occam/demo/reports/r3_tide_energy.txt --navigator > layer.json   # layer.json is git-ignored
python -m occam cluster occam/demo/reports --cypher graph.cypher   # Neo4j import script
```

## Real data

```bash
python scripts/download_data.py        # ~400 MB into ../../datasets/occam (or $OCCAM_DATA), pinned + checksummed
D=../../datasets/occam
python -m occam train-classifier --attack $D/enterprise-attack-19.2.json --tram $D/tram/multi_label.json --out model.pkl
python -m occam attribute occam/demo/reports/r3_tide_energy.txt --attack $D/enterprise-attack-19.2.json \
    --classifier model.pkl --calibration results/grade_calibration.json
```

## React workbench

```bash
uvicorn occam.api:app --host 127.0.0.1 --port 8000
cd ui && npm ci && npm run dev         # proxies /ach, /scenarios, /stix, /extract to the API
```

Without an API, as in this site's [demo](https://rakshit-737.github.io/occam/demo/), the workbench loads snapshots of the bundled scenarios (`python scripts/export_demo.py`) and recomputes the ranking in the browser when you edit a cell.

## Reproduce the benchmarks

See [Reproduce](reproduce.md) for every command, its output files, the expected numbers and measured runtimes.
