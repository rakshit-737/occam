# CLI and HTTP reference

```text
occam extract FILE [--navigator | --stix] [--classifier MODEL]
occam cluster DIR [--threshold 0.3] [--cypher FILE]
occam ach SCENARIO.json [--override EID:HID=RATING ...] [--json | --stix]
occam attribute FILE --attack enterprise-attack.json [--shortlist 8] [--classifier MODEL] [--calibration MAP.json] [--json]
occam train-classifier --attack enterprise-attack.json [--tram multi_label.json] [--threshold 0.8] [--out MODEL]
occam load-attack BUNDLE [--out attack_kb.json]
occam demo
```

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | version and KB size |
| POST | `/extract` | span-anchored IOC and TTP extraction, plus a Navigator layer |
| GET | `/scenarios` | bundled scenario names |
| POST | `/ach` | ACH on a scenario or on inline actors + evidence, with `overrides` |
| POST | `/stix` | STIX 2.1 bundle of an assessment |
| GET | `/taxii2/...` | read-only TAXII 2.1 discovery, API root, collections and objects |

Interactive OpenAPI docs are served at `/docs` while the API runs.
