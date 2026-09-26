# Security Policy

## Scope
OCCAM is an offline analysis tool. It reads local text and JSON and makes no network requests. It does not scan, enrich IOCs, or interact with the infrastructure it describes.

## Reporting a vulnerability
Please open a private security advisory on the repository or email the maintainer. Do not open a public issue. Include reproduction steps and the input that triggers the problem. We aim to acknowledge reports within 7 days.

## Safe-use guidance
- Treat all ingested reports as untrusted. Keep defanged IOCs defanged in anything you republish.
- The bundled actor profiles are **fictional**. OCCAM output is decision support. It is not an attribution finding.
- Do not feed classified, TLP:RED, or personal data into the tool unless your environment is authorized for it.

## Supported versions
Only the latest `main` receives fixes.
