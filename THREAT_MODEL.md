# OCCAM Threat Model

## Assets
- Assessments: the conclusion, its confidence grade, and the ACH matrix
- Evidence sets and actor profiles, whether synthetic or derived from ATT&CK
- Exported STIX bundles and the TAXII collection consumed downstream
- Trained classifier artefacts (`*.pkl`)

## Trust boundaries
| Boundary | Treatment |
| --- | --- |
| Ingested reports / IOC text | **Untrusted data.** Parsed only by regex, keyword matching and a linear classifier. Never executed, fetched, or rendered as HTML |
| Report PDFs (APTnotes) | **Untrusted files.** Text is extracted with pypdf in a child process that has a 60 s timeout and a 40-page cap. PDFs are never rendered or opened in a viewer. Files are checked against their git blob SHA-1 before parsing |
| Evidence / scenario JSON, API bodies | Semi-trusted analyst input. Validation covers Admiralty grades, unknown `points_to` actors, and duplicate IDs. API text is capped at 2 MB, and scenario names are confined to the fixtures directory (a traversal test covers this) |
| ATT&CK bundle / KB file | Pinned commit plus SHA-256. Parsed as JSON data only |
| Classifier artefacts | Stored with pickle, so **only load models you trained yourself**. `TechniqueClassifier.load` also checks the loaded object's type, but that is not a security boundary |
| Downstream STIX consumers | The confidence grade and full matrix are embedded so the uncertainty cannot be silently dropped. Bundles validate strictly against python-stix2 |

## Adversaries and abuse cases
| # | Threat | Mitigation |
| --- | --- | --- |
| T1 | **False-flag operator** plants code, language, or metadata markers to frame another actor | Spoofable evidence types are down-weighted ×0.5. Each framed actor gets an automatic false-flag hypothesis. False-flag indicators cap confidence at MODERATE, and support that is mostly spoofable caps it at LOW. *Measured:* with 3 planted markers on 274 held-out ATT&CK incidents, the framed group is named 1.1% of the time (baseline 88%), with no errors at ≥0.8 stated probability |
| T2 | **Overconfident analyst or tool** names an actor on thin evidence | A mandatory unknown hypothesis, conservative tie-breaking, a minimum number of diagnostic items before HIGH is allowed, and leave-one-out sensitivity output. Calibration is measured (Brier/ECE) in `results/attribution.md` |
| T3 | **Poisoned report** injects fake TTPs or IOCs | Every hit carries a source span so it can be audited, and Admiralty reliability weighting applies. *Residual risk:* there is no source-reputation store yet |
| T4 | **Hallucinated extraction** from an ML or LLM extractor | The contract requires a `SourceSpan` on every fact, and classifier hits carry the sentence span. Tests check that the span text matches the source |
| T5 | **ReDoS / resource exhaustion** from crafted text or PDFs | Regexes are linear, API input is size-capped, and PDF parsing runs in a child process with a timeout |
| T6 | **Misuse of output** as a public accusation about a real group | Every output carries a decision-support disclaimer. Benchmark results about ATT&CK groups are evaluation artefacts, and the README gives ethics guidance |
| T7 | **Malicious KB or scenario JSON** | Parsed with `json.loads` only (no YAML), and values are validated |
| T8 | **Exposed API** (no authentication) | Binds to 127.0.0.1 by default. docker-compose publishes only on loopback, runs as a non-root user and uses a read-only root filesystem. TAXII is read-only |

## Out of scope
Multi-user auth, a hosted deployment, and storage encryption. The API is a lab and workbench tool; for shared use, put OCCAM behind an authenticating reverse proxy or a real TAXII server.
