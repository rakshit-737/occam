# ADR 0003: Every extracted fact carries a source span

- Status: accepted
- Date: 2026-09-26

## Context
Ingested reports are untrusted input. ML and LLM extractors can hallucinate techniques or IOCs, and an attribution resting on a hallucinated fact cannot be audited.

## Decision
Each extractor emits `TechniqueHit` or `Indicator` objects that carry a `SourceSpan(source_id, start, end, text)`, and the invariant `text[start:end] == span.text` holds:
- keyword hits point at the exact match;
- IOC hits point at the (possibly defanged) original text, while the value is refanged;
- classifier hits point at the sentence the prediction came from, and `matched` records the probability.

Any future LLM extractor must satisfy the same contract. Output without a span is rejected. The ACH evidence descriptions produced by `occam attribute` include the span text and offset.

## Consequences
- Tests check the span invariant for every extractor (`test_extract.py`, `test_classifier.py`).
- Sentence-level spans from the classifier are coarser than keyword spans. That is still enough for an analyst to verify the claim.
