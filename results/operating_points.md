## Operating points — false positives at a fixed detection rate

Each detector's threshold is set to catch the same share of attacks; we then report how much **real benign traffic** (WildChat + LMSYS) it flags at that catch rate. This holds detection constant and shows the false-alarm cost, so the comparison does not depend on where any detector's 0.5 happens to fall.

| Detector | AUC | EER | FPR @ 95% catch | FPR @ 99% catch |
|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.991 | 4.6% | 7.81% | 23.35% |
| meta prompt-guard v2 (86M) | 0.909 | 17.6% | 24.22% | 53.11% |
| wolf-defender (0.3B) | 0.988 | 5.2% | 34.56% | 54.92% |
| meta prompt-guard v2 (22M) | 0.825 | 26.2% | 40.66% | 68.26% |
| wolf-defender-small (0.1B) | 0.981 | 6.9% | 43.51% | 68.86% |
| sentinel (qualifire, 395M) | 0.981 | 5.0% | 44.18% | 100.00% |
| protectai v2 (184M) | 0.896 | 18.8% | 54.78% | 100.00% |
| deepset injection (184M) | 0.714 | 36.8% | 68.31% | 84.47% |
| fmops distilbert (67M) | 0.680 | 40.5% | 75.12% | 86.77% |
| hlyn judge (70M) | 0.963 | 10.6% | 77.04% | 85.63% |
| proventra mdeberta (280M) | 0.864 | 19.9% | 82.22% | 96.92% |
| meta prompt-guard (86M) | 0.307 | 63.2% | 85.83% | 98.12% |

## Fixed thresholds — 0.5 and each model's declared threshold

FPR on real benign traffic and recall on the pooled attack sets at the common 0.5 and at the threshold each model's maintainer declares (`threshold:` in models.yaml; 0.5 when none is declared).

| Detector | FPR @0.5 | recall @0.5 | declared thr | FPR @thr | recall @thr |
|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 1.24% | 88.9% | 0.5 | 1.24% | 88.9% |
| meta prompt-guard v2 (86M) | 4.88% | 51.8% | 0.5 | 4.88% | 51.8% |
| wolf-defender (0.3B) | 24.03% | 89.3% | 0.5 | 24.03% | 89.3% |
| meta prompt-guard v2 (22M) | 0.77% | 16.3% | 0.5 | 0.77% | 16.3% |
| wolf-defender-small (0.1B) | 28.79% | 89.4% | 0.5 | 28.79% | 89.4% |
| sentinel (qualifire, 395M) | 23.60% | 88.3% | 0.5 | 23.60% | 88.3% |
| protectai v2 (184M) | 8.82% | 70.4% | 0.5 | 8.82% | 70.4% |
| deepset injection (184M) | 65.89% | 94.0% | 0.5 | 65.89% | 94.0% |
| fmops distilbert (67M) | 64.98% | 90.1% | 0.5 | 64.98% | 90.1% |
| hlyn judge (70M) | 21.53% | 58.0% | 0.5 | 21.53% | 58.0% |
| proventra mdeberta (280M) | 21.83% | 69.0% | 0.5 | 21.83% | 69.0% |
| meta prompt-guard (86M) | 88.30% | 95.8% | 0.5 | 88.30% | 95.8% |

## Threshold sweep — FPR on real benign traffic (lower = better)

| Detector | 0.2 | 0.45 | 0.5 | 0.55 | 0.8 |
|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 2.44% | 1.27% | 1.24% | 1.22% | 0.89% |
| meta prompt-guard v2 (86M) | 5.71% | 4.92% | 4.88% | 4.84% | 4.52% |
| wolf-defender (0.3B) | 25.78% | 24.27% | 24.03% | 23.84% | 22.52% |
| meta prompt-guard v2 (22M) | 3.05% | 0.91% | 0.77% | 0.74% | 0.47% |
| wolf-defender-small (0.1B) | 33.43% | 29.21% | 28.79% | 28.58% | 25.29% |
| sentinel (qualifire, 395M) | 26.62% | 24.15% | 23.60% | 23.11% | 20.65% |
| protectai v2 (184M) | 9.74% | 8.98% | 8.82% | 8.70% | 7.96% |
| deepset injection (184M) | 68.73% | 67.14% | 65.89% | 65.65% | 64.25% |
| fmops distilbert (67M) | 66.81% | 65.28% | 64.98% | 64.64% | 63.28% |
| hlyn judge (70M) | 49.96% | 34.33% | 21.53% | 5.60% | 0.00% |
| proventra mdeberta (280M) | 22.99% | 21.93% | 21.83% | 21.75% | 20.65% |
| meta prompt-guard (86M) | 89.10% | 88.43% | 88.30% | 88.13% | 85.83% |

## Threshold sweep — recall on attacks (higher = better)

| Detector | 0.2 | 0.45 | 0.5 | 0.55 | 0.8 |
|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 90.7% | 89.0% | 88.9% | 88.7% | 87.1% |
| meta prompt-guard v2 (86M) | 58.5% | 52.9% | 51.8% | 51.0% | 47.4% |
| wolf-defender (0.3B) | 90.6% | 89.5% | 89.3% | 89.3% | 88.6% |
| meta prompt-guard v2 (22M) | 35.7% | 17.4% | 16.3% | 15.3% | 11.5% |
| wolf-defender-small (0.1B) | 91.0% | 89.7% | 89.4% | 89.3% | 88.3% |
| sentinel (qualifire, 395M) | 89.9% | 88.5% | 88.3% | 88.0% | 86.5% |
| protectai v2 (184M) | 71.7% | 70.6% | 70.4% | 70.1% | 68.9% |
| deepset injection (184M) | 95.0% | 94.2% | 94.0% | 93.7% | 92.8% |
| fmops distilbert (67M) | 91.5% | 90.4% | 90.1% | 89.8% | 88.5% |
| hlyn judge (70M) | 83.8% | 75.2% | 58.0% | 29.7% | 0.0% |
| proventra mdeberta (280M) | 70.8% | 69.2% | 69.0% | 68.8% | 67.1% |
| meta prompt-guard (86M) | 96.5% | 95.9% | 95.8% | 95.7% | 95.0% |

_Generated 2026-10-19 via `python -m scripts.analyze_operating_points` from dumped per-prompt scores. No model inference; reproducible offline._
