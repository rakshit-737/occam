# Preprint

`occam.tex` + `refs.bib`: "What Does Analysis of Competing Hypotheses Add to Attack Attribution? A Leakage-Controlled Benchmark with Planted, Authentic and Mimicked False Flags" (Rakshit, VIT Chennai). Not submitted anywhere and not peer reviewed.

**PDF:** <https://rakshit-737.github.io/occam-cti-attribution/preprint.pdf>. The `docs` workflow builds it on every push to `main`. The `paper` workflow also uploads it as the `occam-preprint` artefact, and release builds attach it to the GitHub Release. To build locally: `latexmk -pdf occam.tex`. The figure is read from `../docs/figures/`.

Every number in the text comes from a file in `../results/`, and those files record the bench run that produced them (run 37093689060). Every DOI, arXiv id and URL in `refs.bib` is resolved and compared with its entry by `../scripts/check_refs.py`; the outcome is in [`refs_check.log`](refs_check.log). AI assistance (Claude) is acknowledged in the paper.
