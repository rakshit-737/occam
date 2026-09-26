# OCCAM Threat Model

## Assets
- Assessments: the conclusion, its confidence grade, and the ACH matrix
- Evidence sets and actor profiles
- Exported STIX bundles consumed downstream

## Trust boundaries
| Boundary | Treatment |
| --- | --- |
| Ingested reports / IOC text | **Untrusted data.** Parsed only by regex and keyword matching. Never executed, fetched, or rendered as HTML |
| Evidence / scenario JSON | Semi-trusted analyst input. Validation covers Admiralty grades, unknown `points_to` actors, and duplicate IDs |
| ATT&CK KB file (`--kb`) | Local file the operator supplies. Parsed as JSON data only |
| Downstream STIX consumers | The confidence grade and full matrix are embedded so the uncertainty cannot be silently dropped |

## Adversaries and abuse cases
| # | Threat | Mitigation in this MVP |
| --- | --- | --- |
| T1 | **False-flag operator** plants code, language, or metadata markers to frame another actor | Spoofable evidence types are down-weighted ×0.5. Each framed actor gets an automatic false-flag hypothesis. False-flag indicators cap confidence at MODERATE. Support that is mostly spoofable caps it at LOW |
| T2 | **Overconfident analyst or tool** names an actor on thin evidence | A mandatory unknown hypothesis, conservative tie-breaking, a minimum number of diagnostic items before HIGH is allowed, and leave-one-out sensitivity output |
| T3 | **Poisoned report** injects fake TTPs or IOCs | Every hit carries a source span so it can be audited, and Admiralty reliability weighting applies. *Residual risk:* there is no source-reputation store yet |
| T4 | **Hallucinated extraction** from a future LLM extractor | The contract requires a `SourceSpan` on every fact, and tests check that the span text matches the source |
| T5 | **ReDoS** from crafted text | Patterns are linear with no nested ambiguous quantifiers. *Residual risk:* input size is not capped yet (TODO) |
| T6 | **Misuse of output** as a public accusation | Fixtures are fictional, every report carries a disclaimer, and the README gives ethics guidance |
| T7 | **Malicious KB or scenario JSON** | Parsed with `json.loads` only (no pickle or YAML), and values are validated |

## Out of scope (CLI MVP)
Multi-user auth, a hosted API, and storage encryption. All three become required once the FastAPI workbench exists.
