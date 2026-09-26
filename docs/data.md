# Datasets

Nothing in this table is committed to git. `scripts/download_data.py` fetches every item into `../../datasets/occam` (or `$OCCAM_DATA`), pinned to immutable commits and verified by checksum. The total is about 180 MB.

| Dataset | What OCCAM uses it for | Size | Pinned at | Licence / terms |
| --- | --- | --- | --- | --- |
| [MITRE ATT&CK Enterprise 19.2](https://github.com/mitre-attack/attack-stix-data) (STIX 2.1) | 697 techniques, 176 groups, 825 software, 56 campaigns, 18,457 `uses` relationships. Used for actor profiles, rarity statistics, classifier training (17,136 procedure examples) and the leave-one-report-out attribution benchmark | 54 MB | `6cda5ad8`, sha256 `dc1639ca…` | [ATT&CK Terms of Use](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/): royalty-free, attribution required |
| [CTID TRAM2 annotations](https://github.com/center-for-threat-informed-defense/tram) (`multi_label.json`, `single_label.json`) | 19,178 sentences from 151 real CTI reports, labelled with 50 ATT&CK techniques. Used for the TTP-extraction benchmark and extra classifier training | 7 MB | `f29793d8` | Apache-2.0 |
| [APTnotes](https://github.com/aptnotes/data) index + [kbandla/APTnotes](https://github.com/kbandla/APTnotes) PDFs | 58 public APT reports (2010-2015) whose filename names exactly one ATT&CK group. Used for end-to-end text-to-attribution and clustering. Each PDF is checked against its git blob SHA-1 | ~120 MB | `8595fbde` / `586aaa5e` | Reports are © their publishers and publicly released. They are not redistributed here: only the fetch script is committed |

## Safety
- No malware binaries are downloaded. The only file types are JSON, CSV and PDF reports.
- PDFs are parsed as text only (pypdf, in a child process with a 60 s timeout and a 40-page cap). They are never rendered or opened in a viewer.
- Some report texts quote webshell code or IOCs, so local antivirus may quarantine them. On the author's machine Windows Defender blocked one converted text (`h12756-wp-shell-crew`). The benchmark skips unreadable files and records them in `results/aptnotes.json` under `skipped`.

## Labels and their limits
- **ATT&CK incidents** are reported slices of activity, not raw telemetry, and the attribution is MITRE's reading of public reporting.
- **APTnotes labels** come from filenames, e.g. `Operation_Molerats` becomes G0021 Molerats. Files that match zero groups or several groups are dropped. Short aliases (under 5 characters) are ignored to avoid false matches.
- ATT&CK group profiles are partly built from reports like the APTnotes ones. The APTnotes attribution numbers are therefore an *optimistic* end-to-end check. The leak-free estimate is the leave-one-report-out benchmark.
