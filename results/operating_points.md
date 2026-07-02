## Operating points — false positives at a fixed detection rate

Each detector's threshold is set to catch the same share of attacks; we then report how much **real benign traffic** (WildChat + LMSYS) it flags at that catch rate. This holds detection constant and shows the false-alarm cost, so the comparison does not depend on where any detector's 0.5 happens to fall.

| Detector | AUC | EER | FPR @ 95% catch | FPR @ 99% catch |
|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.991 | 4.7% | 7.71% | 23.13% |
| meta prompt-guard v2 (86M) | 0.906 | 17.9% | 25.52% | 54.37% |
| wolf-defender (0.3B) | 0.986 | 5.7% | 34.63% | 54.97% |
| meta prompt-guard v2 (22M) | 0.823 | 26.3% | 40.39% | 67.88% |
| wolf-defender-small (0.1B) | 0.978 | 7.2% | 43.79% | 69.21% |
| sentinel (qualifire, 395M) | 0.980 | 5.4% | 46.30% | 100.00% |
| deepset injection (184M) | 0.710 | 37.2% | 69.44% | 84.29% |
| fmops distilbert (67M) | 0.677 | 40.9% | 74.64% | 86.64% |
| hlyn judge (70M) | 0.961 | 11.1% | 77.12% | 85.66% |
| proventra mdeberta (280M) | 0.860 | 20.4% | 82.22% | 96.92% |
| meta prompt-guard (86M) | 0.309 | 63.1% | 85.77% | 97.96% |
| protectai v2 (184M) | 0.884 | 19.1% | 100.00% | 100.00% |

## Threshold sweep — FPR on real benign traffic (lower = better)

| Detector | 0.2 | 0.45 | 0.5 | 0.55 | 0.8 |
|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 2.44% | 1.27% | 1.24% | 1.22% | 0.89% |
| meta prompt-guard v2 (86M) | 5.71% | 4.92% | 4.88% | 4.84% | 4.52% |
| wolf-defender (0.3B) | 25.78% | 24.27% | 24.03% | 23.84% | 22.52% |
| meta prompt-guard v2 (22M) | 3.05% | 0.91% | 0.77% | 0.74% | 0.47% |
| wolf-defender-small (0.1B) | 33.43% | 29.21% | 28.79% | 28.58% | 25.29% |
| sentinel (qualifire, 395M) | 26.62% | 24.15% | 23.60% | 23.11% | 20.65% |
| deepset injection (184M) | 68.73% | 67.14% | 65.89% | 65.65% | 64.25% |
| fmops distilbert (67M) | 66.81% | 65.28% | 64.98% | 64.64% | 63.28% |
| hlyn judge (70M) | 50.58% | 34.76% | 21.67% | 5.61% | 0.00% |
| proventra mdeberta (280M) | 22.99% | 21.93% | 21.83% | 21.75% | 20.65% |
| meta prompt-guard (86M) | 89.10% | 88.43% | 88.30% | 88.13% | 85.83% |
| protectai v2 (184M) | 9.74% | 8.98% | 8.82% | 8.70% | 7.96% |

## Threshold sweep — recall on attacks (higher = better)

| Detector | 0.2 | 0.45 | 0.5 | 0.55 | 0.8 |
|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 90.8% | 89.2% | 89.1% | 88.9% | 86.7% |
| meta prompt-guard v2 (86M) | 57.9% | 52.3% | 51.2% | 50.4% | 46.7% |
| wolf-defender (0.3B) | 90.5% | 89.4% | 89.3% | 89.2% | 88.6% |
| meta prompt-guard v2 (22M) | 35.6% | 17.5% | 16.3% | 15.4% | 11.4% |
| wolf-defender-small (0.1B) | 90.9% | 89.5% | 89.2% | 89.1% | 88.1% |
| sentinel (qualifire, 395M) | 89.3% | 87.8% | 87.5% | 87.2% | 85.6% |
| deepset injection (184M) | 94.7% | 93.9% | 93.7% | 93.4% | 92.4% |
| fmops distilbert (67M) | 91.6% | 90.5% | 90.2% | 90.0% | 88.6% |
| hlyn judge (70M) | 84.0% | 75.8% | 58.7% | 29.6% | 0.0% |
| proventra mdeberta (280M) | 69.8% | 68.2% | 68.0% | 67.8% | 66.0% |
| meta prompt-guard (86M) | 96.6% | 96.0% | 95.9% | 95.8% | 95.1% |
| protectai v2 (184M) | 69.8% | 68.8% | 68.5% | 68.3% | 67.1% |

_Generated 2026-07-02 via `python -m scripts.analyze_operating_points` from dumped per-prompt scores. No model inference; reproducible offline._
