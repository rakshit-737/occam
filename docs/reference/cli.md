# CLI and HTTP reference

```text
occam [--kb KB.json] [--version] <command> ...
occam extract FILE [--navigator | --stix] [--classifier MODEL]
occam cluster DIR [--threshold 0.3] [--cypher FILE]
occam ach SCENARIO.json|BUNDLED_NAME [--override EID:HID=RATING ...] [--json | --stix]
occam attribute FILE --attack enterprise-attack.json [--shortlist 8] [--classifier MODEL] [--calibration MAP.json] [--json]
occam train-classifier --attack enterprise-attack.json [--tram multi_label.json] [--threshold 0.8] [--out MODEL]
occam load-attack BUNDLE [--out attack_kb.json]
occam demo
```

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | version and KB size (open even when a token is set, for health checks) |
| POST | `/extract` | span-anchored IOC and TTP extraction, plus a Navigator layer |
| GET | `/scenarios` | bundled scenario names |
| POST | `/ach` | ACH on a scenario or on inline actors + evidence, with `overrides` |
| POST | `/stix` | STIX 2.1 bundle of an assessment (bundled `scenario` or inline `actors` + `evidence`, with `overrides`) |
| GET | `/taxii2/...` | read-only TAXII 2.1 discovery, API root, collections and objects |

Interactive OpenAPI docs (`/docs`) are off by default because they load third-party CDN JavaScript; set `OCCAM_API_DOCS=1` to enable them. Other environment variables: `OCCAM_API_TOKEN` (require `Authorization: Bearer <token>` on every call except `GET /health` and the workbench page; both workbenches have a token field), `OCCAM_ALLOWED_HOSTS` (Host allow-list, default loopback names), `OCCAM_FIXTURES` (alternative demo scenarios), `OCCAM_KB`. Limits: 1 MB request body, 500,000 characters of text.
