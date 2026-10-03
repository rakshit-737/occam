# Security Policy

## Scope
OCCAM is an offline analysis tool. It reads local text, JSON and report PDFs. It does not scan, enrich IOCs, or interact with the infrastructure it describes.

Network access happens in only three places:
- `scripts/download_data.py` fetches public datasets from pinned GitHub commits and verifies their checksums. It never downloads malware.
- `scripts/check_refs.py` resolves the preprint's DOIs, arXiv ids and reference URLs (doi.org, arXiv, the cited publishers' pages).
- The optional FastAPI service listens on 127.0.0.1 by default.

## Reporting a vulnerability
Please use GitHub private vulnerability reporting (Security tab -> "Report a vulnerability", https://github.com/rakshit-737/occam-cti-attribution/security/advisories/new). Do not open a public issue. Include reproduction steps and the input that triggers the problem. We aim to acknowledge reports within 7 days.

## Safe-use guidance
- Treat all ingested reports as untrusted. Keep defanged IOCs defanged in anything you republish.
- Output about real ATT&CK groups is decision support and benchmark material. It is **not** an attribution finding.
- Load classifier `.pkl` files only if you trained them yourself, because pickle can execute code.
- The API has no authentication unless you set `OCCAM_API_TOKEN`. Do not expose it beyond localhost without one. With a token set, only `GET /health` (for container health checks) and the static workbench page stay open; every API call needs `Authorization: Bearer <token>`, which both workbenches send once the token is entered.
- Some public report texts quote webshell code, so local antivirus may quarantine them. That is expected. Do not disable antivirus to work around it.
- Do not feed classified, TLP:RED, or personal data into the tool unless your environment is authorized for it.

## Supported versions
Only the latest `main` receives fixes.
