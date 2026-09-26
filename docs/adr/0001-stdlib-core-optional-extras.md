# ADR 0001: Standard-library core, heavy features behind optional extras

- Status: accepted
- Date: 2026-09-26

## Context
OCCAM is aimed at students and analysts on modest machines, and it has to be easy to audit. The reasoning core (extraction, ACH, confidence grading, STIX export) needs no numerical libraries. The newer features do: the TF-IDF classifier needs scikit-learn, Louvain clustering needs networkx, the API needs FastAPI, and validation needs python-stix2. Some of these are slow to install, or do not yet ship wheels for new Python versions.

## Decision
- `occam` core modules import only the standard library: `models`, `attack`, `knowledge`, `extract`, `ach`, `attribution`, `evaluation`, `metrics`, `stix` (export), `cluster`, `cli`.
- Optional extras are declared in `pyproject.toml`: `ml`, `graph`, `stix`, `api`, `pdf` and `bench`. Any module that needs one imports it lazily, inside the function that uses it.
- A dedicated CI job (`core-stdlib-only`) runs the core tests with nothing installed except pytest.

## Consequences
- `pip install occam` gives you the working ACH engine with zero transitive dependencies. The reasoning layer is small enough to read in one sitting.
- Metrics such as P/R/F1, Brier, ECE, NMI and ARI are implemented by hand in `metrics.py`. They are unit-tested against known values, not against scikit-learn.
- Optional-feature tests use `pytest.importorskip`, so missing extras skip tests instead of failing them.
