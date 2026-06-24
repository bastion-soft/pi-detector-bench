## False-positive rate (benign flagged as attack, lower = better)

| Model | WildChat | LMSYS | **Avg** |
|---|---|---|---|
| bastion-prompt-protection (70M) | 1.18% | 1.30% | **1.24%** |
| protectai v2 (184M) | 7.60% | 10.04% | **8.82%** |
| hlyn judge (70M) | 23.00% | 20.34% | **21.67%** |
| proventra mdeberta (280M) | 18.18% | 25.48% | **21.83%** |
| sentinel (qualifire, 395M) | 23.82% | 23.38% | **23.60%** |
| wolf-defender (0.3B) | 18.80% | 29.26% | **24.03%** |
| wolf-defender-small (0.1B) | 23.76% | 33.82% | **28.79%** |
| fmops distilbert (67M) | 65.14% | 64.82% | **64.98%** |
| deepset injection (184M) | 67.20% | 64.58% | **65.89%** |
| meta prompt-guard (86M) | 85.60% | 91.00% | **88.30%** |

Benign real-user openers (WildChat / LMSYS first-user turns); the share each model wrongly flags as an attack. Lower is better.

_Generated 2026-06-22 via `python -m scripts.measure_false_positives`._
