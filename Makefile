PYTHON ?= python

.PHONY: install test demo clean

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

demo:
	$(PYTHON) -m occam demo

clean:
	rm -rf .pytest_cache build *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
