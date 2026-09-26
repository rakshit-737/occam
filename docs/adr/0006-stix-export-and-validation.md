# ADR 0006: Hand-built STIX 2.1 export, strictly validated with python-stix2

- Status: accepted
- Date: 2026-09-26

## Context
Assessments have to be shareable with downstream tools such as SIEMs, OpenCTI and MISP, without losing their uncertainty. python-stix2 is the reference implementation, but the core must stay dependency-free (ADR 0001).

## Decision
- `occam.stix.export` builds STIX 2.1 dicts by hand:
  - indicators with escaped patterns;
  - `attack-pattern` objects with ATT&CK external references;
  - a `note` whose `content` is the full JSON assessment (ACH matrix, rationale, false-flag indicators) and whose `confidence` is the numeric grade.
- `occam.stix.validate` round-trips a bundle through `stix2.parse(..., allow_custom=False)` when the `stix` extra is installed. Tests validate every demo scenario and a real-ATT&CK export.
- The API exposes a minimal **read-only TAXII 2.1** collection (discovery, API root, collections, objects) holding published assessments.

## Consequences
- A consumer cannot keep the conclusion and strip out the confidence and the matrix, because they travel together in one `note`.
- The TAXII endpoint is in-memory and unauthenticated. It is a demo of the sharing path and is bound to localhost in docker-compose. A production deployment would sit behind a real TAXII server such as OpenCTI or Medallion.
