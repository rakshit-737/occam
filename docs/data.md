# Datasets

Nothing in this table is committed to git. `scripts/download_data.py` fetches every item into `../../datasets/occam` (or `$OCCAM_DATA`), pinned to immutable commits and verified by checksum. The total is about 400 MB. The counts below are written to `results/datasets.json` by `scripts/dataset_stats.py`.

| Dataset | What OCCAM uses it for | Size | Pinned at | Licence / terms |
| --- | --- | --- | --- | --- |
| [MITRE ATT&CK Enterprise 19.2](https://github.com/mitre-attack/attack-stix-data) (STIX 2.1) | 697 techniques, 176 groups, 825 software, 56 campaigns, 18,457 `uses` relationships. Used for actor profiles, rarity statistics, classifier training (17,376 procedure examples) and the leave-one-report-out attribution benchmark | 54 MB | `6cda5ad8`, sha256 `dc1639ca…` | [ATT&CK Terms of Use](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/): royalty-free, attribution required |
| [CTID TRAM2 annotations](https://github.com/center-for-threat-informed-defense/tram) (`multi_label.json`, `single_label.json`) | 19,178 sentences from 151 real CTI reports, labelled with 50 ATT&CK techniques. Used for the TTP-extraction benchmark and extra classifier training | 7 MB | `f29793d8` | Apache-2.0 |
| [MITRE ATT&CK Enterprise 12.1 and 15.1](https://github.com/mitre-attack/attack-stix-data) | Older releases (released Nov 2022 and May 2024) for the temporal split | 39 + 43 MB | same commit, sha256 pinned | ATT&CK Terms of Use |
| [rcATT training data](https://github.com/vlegoy/rcATT) | 1,490 ATT&CK-cited reports with tactic and technique labels, to reproduce Legoy et al. (2020) | 33 MB | `f82f7fd4`, sha256 pinned | MIT |
| [APTnotes](https://github.com/aptnotes/data) index + [kbandla/APTnotes](https://github.com/kbandla/APTnotes) PDFs | 73 public APT reports (2010-2015) whose file name or title names exactly one ATT&CK group or attributed campaign (72 have a text layer). Used for end-to-end text-to-attribution and clustering. Each PDF is checked against its git blob SHA-1 | ~210 MB | `8595fbde` / `586aaa5e` | Reports are © their publishers and publicly released. They are not redistributed here: only the fetch script is committed |

## Safety
- No malware binaries are downloaded. The only file types are JSON, CSV and PDF reports.
- PDFs are parsed as text only (pypdf, in a child process with a 60 s timeout and a 40-page cap). They are never rendered or opened in a viewer.
- Some report texts quote webshell code or IOCs, so local antivirus may quarantine them. On the author's machine Windows Defender blocked one converted text (`h12756-wp-shell-crew`). The benchmark skips unreadable files and records them in `results/aptnotes.json` under `skipped`.

## Labels and their limits
- **ATT&CK incidents** are reported slices of activity, not raw telemetry, and the attribution is MITRE's reading of public reporting.
- **APTnotes labels** come from the file name and title, e.g. `Operation_Molerats` becomes G0021 Molerats; attributed ATT&CK campaign names are a second vocabulary. Files matching zero or several groups are dropped, and aliases under 5 characters are ignored. Labels from "software used by only one ATT&CK group" were tried and rejected: they are circular (the label-defining tool is also evidence) and wrong for commercial tools (FinFisher would have been labelled Dark Caracal).
- ATT&CK group profiles are partly built from reports like the APTnotes ones. `bench_aptnotes.py` therefore also reports *leak-controlled* numbers that hold out ATT&CK citations of the true group whose source name matches the report (a heuristic; 22 of 72 matched). The fully leak-free estimate is the leave-one-report-out benchmark.
