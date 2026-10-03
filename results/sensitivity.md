### Sensitivity of ACH to its cell-rule thresholds (ATT&CK v19.2)

274 held-out incidents from 103 groups, 3 markers. `cX-rY`: a technique used by at least X of all groups is non-diagnostic, one used by at most Y groups is rare (CC on a match). Shipped: `c0.3-r3` (hand-set). *Cross-fitted*: each group fold uses the configuration with the best mean accuracy over the five settings on the other fold (chosen: {0: 'c0.2-r5', 1: 'c0.2-r3'}).

*Source: GitHub Actions run [37093689060](https://github.com/rakshit-737/occam-cti-attribution/actions/runs/37093689060), commit `09cde53`, 2026-10-03T03:35:51+00:00.*

| Thresholds | Closed correct | Open correct decline | False flag correct | False flag names framed | Authentic: calls it a frame | Mimicry correct | Mimicry names framed |
|---|---|---|---|---|---|---|---|
| c0.2-r2 | 0.310 | 0.591 | 0.701 | 0.007 | 0.212 | 0.168 | 0.354 |
| c0.2-r3 | 0.332 | 0.489 | 0.752 | 0.007 | 0.245 | 0.186 | 0.350 |
| c0.2-r5 | 0.354 | 0.391 | 0.803 | 0.011 | 0.274 | 0.201 | 0.361 |
| c0.3-r2 | 0.285 | 0.577 | 0.668 | 0.007 | 0.157 | 0.164 | 0.274 |
| c0.3-r3 (shipped) | 0.299 | 0.460 | 0.734 | 0.011 | 0.186 | 0.179 | 0.270 |
| c0.3-r5 | 0.325 | 0.369 | 0.766 | 0.011 | 0.230 | 0.201 | 0.292 |
| c0.4-r2 | 0.270 | 0.588 | 0.642 | 0.007 | 0.150 | 0.172 | 0.248 |
| c0.4-r3 | 0.285 | 0.482 | 0.708 | 0.007 | 0.172 | 0.186 | 0.248 |
| c0.4-r5 | 0.310 | 0.380 | 0.759 | 0.007 | 0.215 | 0.212 | 0.263 |
| cross-fitted choice | 0.339 | 0.420 | 0.774 | 0.011 | 0.259 | 0.190 | 0.358 |

Paired difference, configuration minus shipped (95% cluster-bootstrap interval):

| Thresholds | Closed correct | Open correct decline | False flag correct | False flag names framed | Authentic: calls it a frame | Mimicry correct | Mimicry names framed |
|---|---|---|---|---|---|---|---|
| c0.2-r2 | [-0.019, +0.040] | [+0.084, +0.183] | [-0.073, +0.007] | [-0.018, +0.007] | [-0.004, +0.057] | [-0.043, +0.019] | [+0.050, +0.120] |
| c0.2-r3 | [+0.011, +0.058] | [-0.004, +0.065] | [-0.007, +0.042] | [-0.018, +0.007] | [+0.030, +0.088] | [-0.022, +0.037] | [+0.046, +0.116] |
| c0.2-r5 | [+0.026, +0.085] | [-0.117, -0.022] | [+0.033, +0.111] | [-0.011, +0.011] | [+0.055, +0.122] | [-0.007, +0.055] | [+0.055, +0.130] |
| c0.3-r2 | [-0.036, +0.000] | [+0.077, +0.159] | [-0.098, -0.036] | [-0.011, +0.000] | [-0.051, -0.011] | [-0.030, -0.004] | [-0.007, +0.018] |
| c0.3-r5 | [+0.004, +0.052] | [-0.133, -0.056] | [+0.007, +0.067] | [+0.000, +0.000] | [+0.022, +0.068] | [+0.004, +0.041] | [+0.004, +0.043] |
| c0.4-r2 | [-0.054, -0.007] | [+0.084, +0.175] | [-0.130, -0.053] | [-0.011, +0.000] | [-0.059, -0.015] | [-0.026, +0.008] | [-0.043, -0.004] |
| c0.4-r3 | [-0.029, -0.004] | [+0.007, +0.044] | [-0.048, -0.007] | [-0.011, +0.000] | [-0.030, -0.004] | [+0.000, +0.019] | [-0.040, -0.007] |
| c0.4-r5 | [-0.015, +0.040] | [-0.124, -0.041] | [+0.000, +0.059] | [-0.011, +0.000] | [+0.004, +0.055] | [+0.011, +0.059] | [-0.030, +0.015] |
| cross-fitted choice | [+0.015, +0.069] | [-0.091, +0.007] | [+0.015, +0.068] | [-0.011, +0.011] | [+0.042, +0.108] | [-0.018, +0.041] | [+0.053, +0.124] |
