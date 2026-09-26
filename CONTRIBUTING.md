# Contributing to OCCAM

Thanks for your interest. OCCAM is a small, auditable reasoning engine, and contributions should keep it that way.

## Ground rules
- **The core stays standard-library only** ([ADR 0001](docs/adr/0001-stdlib-core-optional-extras.md)). New heavy dependencies go behind an optional extra and a lazy import.
- **Every extracted fact needs a source span** ([ADR 0003](docs/adr/0003-span-anchored-provenance.md)). This applies to new extractors too, including any LLM-based ones.
- **ACH ranks by least inconsistency and never by support** ([ADR 0002](docs/adr/0002-ach-least-inconsistency.md)). Changes to rating rules or confidence caps must come with benchmark numbers from before and after the change.
- **No live malware, exploit code or scanning.** Data scripts may only fetch reports, STIX/JSON and CSV, and they must verify checksums.
- Never commit datasets or files larger than 1 MB. Add a download step to `scripts/download_data.py` instead.

## Development setup
```bash
python -m pip install -e ".[dev,pdf,bench]"
python -m pytest -q          # real-data tests skip automatically when datasets are absent
python -m ruff check .
python scripts/download_data.py            # optional: ~180 MB into ../../datasets/occam
python -m pytest -q -m realdata            # then run the real-data tests
```

## Benchmarks
If a change touches extraction, attribution or clustering, rerun the relevant script and commit the updated `results/*.md` and `results/*.json`:

| Area | Command |
| --- | --- |
| TTP extraction (TRAM2) | `python scripts/bench_extraction.py` |
| Attribution (ATT&CK leave-one-report-out) | `python scripts/bench_attribution.py` |
| Campaign clustering | `python scripts/bench_clustering.py` |
| End-to-end on APTnotes | `python scripts/bench_aptnotes.py [--model occam_classifier.pkl]` |

Report results honestly, including regressions. Explain any trade-off in the PR description.

## Commits and pull requests
- Use conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `perf:`, `refactor:`, `ci:`, `data:`, `build:`.
- Keep commits small and logical. Every PR must pass CI (ruff, tests on Python 3.10, 3.12 and 3.13, and the stdlib-only core job).
- For significant design changes, add an ADR under `docs/adr/`.

## Reporting security issues
See [SECURITY.md](SECURITY.md). Please do not open public issues for vulnerabilities.
