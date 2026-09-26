### TTP extraction on TRAM2 (151 reports, 19178 sentences, 50 techniques)

Protocol: 5-fold CV grouped by document, seed 13; thresholds tuned on inner 20% doc split. ATT&CK v19.2.

| Method | Sent. P | Sent. R | Sent. micro-F1 | Sent. macro-F1 | Doc P | Doc R | Doc micro-F1 | Doc macro-F1 |
|---|---|---|---|---|---|---|---|---|
| Keyword baseline (ATT&CK technique names) | 0.395 | 0.071 | 0.121 | 0.134 | 0.686 | 0.270 | 0.387 | 0.355 |
| TF-IDF+LR trained on ATT&CK procedures only | 0.376 | 0.387 | 0.381 | 0.353 | 0.552 | 0.703 | 0.618 | 0.579 |
| TF-IDF+LR trained on ATT&CK + TRAM train folds | 0.471 | 0.518 | 0.493 | 0.446 | 0.647 | 0.787 | 0.710 | 0.663 |

Best / worst techniques (sentence F1, ATT&CK+TRAM model):

| Technique | Support | F1 |
|---|---|---|
| T1140 Deobfuscate/Decode Files or Information | 466 | 0.712 |
| T1021.001 Remote Desktop Protocol | 99 | 0.688 |
| T1056.001 Keylogging | 62 | 0.673 |
| T1053.005 Scheduled Task | 118 | 0.664 |
| T1003.001 LSASS Memory | 112 | 0.662 |
| T1557.001 Name Resolution Poisoning and SMB Relay | 7 | 0.222 |
| T1074.001 Local Data Staging | 26 | 0.211 |
| T1005 Data from Local System | 61 | 0.196 |
| T1552.001 Credentials In Files | 22 | 0.182 |
| T1569.002 Service Execution | 22 | 0.176 |
