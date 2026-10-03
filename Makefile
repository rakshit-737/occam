PYTHON ?= python
# Datasets live OUTSIDE the repo (default: ../../datasets/occam); override with OCCAM_DATA.

.PHONY: install data test lint bench bench-falseflag bench-sensitivity bench-extraction bench-attribution bench-extended bench-rcatt bench-clustering bench-aptnotes refs demo api docker clean

install:
	$(PYTHON) -m pip install -e ".[dev,pdf,bench]"

data:
	$(PYTHON) scripts/download_data.py

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

# the same set the manual `bench` GitHub workflow runs (it also trains the classifier for the top-10 APTnotes run)
bench: bench-falseflag bench-sensitivity bench-extraction bench-attribution bench-extended bench-rcatt bench-clustering bench-aptnotes

bench-falseflag:
	$(PYTHON) scripts/bench_falseflag.py

bench-sensitivity:
	$(PYTHON) scripts/bench_sensitivity.py

bench-extended:
	$(PYTHON) scripts/bench_attribution_extended.py

bench-rcatt:
	$(PYTHON) scripts/bench_rcatt.py

bench-extraction:
	$(PYTHON) scripts/bench_extraction.py

bench-attribution:
	$(PYTHON) scripts/bench_attribution.py

bench-clustering:
	$(PYTHON) scripts/bench_clustering.py

bench-aptnotes:
	$(PYTHON) scripts/bench_aptnotes.py
	$(PYTHON) scripts/bench_aptnotes.py --evidence software
	$(PYTHON) scripts/bench_aptnotes.py --evidence techniques

refs:
	$(PYTHON) scripts/check_refs.py

demo:
	$(PYTHON) -m occam demo

api:
	$(PYTHON) -m uvicorn occam.api:app --host 127.0.0.1 --port 8000

docker:
	docker compose up --build

clean:
	rm -rf .pytest_cache .ruff_cache build *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
