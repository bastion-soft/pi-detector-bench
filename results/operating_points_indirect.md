## Indirect / structured — false positives at a fixed 95% catch rate

Each set is matched injected-vs-benign structured data. The threshold is set per detector to catch 95% of that set's injections; the cell is the share of **benign structured records** wrongly flagged at that catch rate. Low = catches the injection without tripping on legitimate structured data. Threshold-agnostic (per-set tuned).

| Detector | agentdojo/agent | bipia/indirect | hackaprompt/direct | injecagent/enhanced | tensortrust/direct | zedgar/structured | **Avg** |
|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 43.30% | 68.50% | 0.00% | 0.00% | 10.25% | 0.00% | **20.34%** |
| meta prompt-guard v2 (86M) | 83.50% | 90.50% | 0.00% | 76.25% | 6.50% | 11.33% | **44.68%** |
| wolf-defender (0.3B) | 91.75% | 100.00% | 0.00% | 58.75% | 13.50% | 23.67% | **47.95%** |
| deepset injection (184M) | 77.32% | 81.50% | 0.00% | 64.75% | 23.25% | 46.00% | **48.80%** |
| meta prompt-guard v2 (22M) | 96.91% | 88.00% | 1.79% | 76.50% | 20.25% | 29.67% | **52.19%** |
| fmops distilbert (67M) | 87.63% | 83.50% | 0.00% | 100.00% | 11.75% | 37.00% | **53.31%** |
| proventra mdeberta (280M) | 85.57% | 85.00% | 3.57% | 76.50% | 58.00% | 12.33% | **53.50%** |
| wolf-defender-small (0.1B) | 73.20% | 100.00% | 0.00% | 88.25% | 17.00% | 46.33% | **54.13%** |
| protectai v2 (184M) | 100.00% | 96.50% | 0.00% | 59.00% | 2.75% | 67.33% | **54.26%** |
| sentinel (qualifire, 395M) | 77.32% | 100.00% | 10.71% | 100.00% | 30.00% | 39.83% | **59.64%** |
| hlyn judge (70M) | 87.63% | 98.50% | 0.00% | 53.00% | 69.50% | 51.33% | **59.99%** |
| meta prompt-guard (86M) | 75.26% | 28.50% | 46.43% | 88.00% | 53.50% | 73.00% | **60.78%** |

## Indirect / structured — summary (averaged across sets)

| Detector | Avg AUC | Avg EER | Avg FPR @ 95% catch | Avg FPR @0.5 | Avg recall @0.5 | declared thr | Avg FPR @thr | Avg recall @thr |
|---|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.945 | 9.7% | 20.34% | 19.58% | 86.7% | 0.5 | 19.58% | 86.7% |
| meta prompt-guard v2 (86M) | 0.788 | 25.1% | 44.68% | 0.36% | 34.0% | 0.5 | 0.36% | 34.0% |
| wolf-defender (0.3B) | 0.855 | 19.5% | 47.95% | 6.08% | 68.5% | 0.5 | 6.08% | 68.5% |
| deepset injection (184M) | 0.787 | 29.0% | 48.80% | 69.66% | 98.9% | 0.5 | 69.66% | 98.9% |
| meta prompt-guard v2 (22M) | 0.772 | 26.0% | 52.19% | 0.07% | 14.8% | 0.5 | 0.07% | 14.8% |
| fmops distilbert (67M) | 0.766 | 26.7% | 53.31% | 68.63% | 99.6% | 0.5 | 68.63% | 99.6% |
| proventra mdeberta (280M) | 0.822 | 22.9% | 53.50% | 4.45% | 51.7% | 0.5 | 4.45% | 51.7% |
| wolf-defender-small (0.1B) | 0.813 | 22.9% | 54.13% | 6.18% | 55.9% | 0.5 | 6.18% | 55.9% |
| protectai v2 (184M) | 0.816 | 21.5% | 54.26% | 7.03% | 56.2% | 0.5 | 7.03% | 56.2% |
| sentinel (qualifire, 395M) | 0.818 | 24.1% | 59.64% | 8.77% | 54.0% | 0.5 | 8.77% | 54.0% |
| hlyn judge (70M) | 0.763 | 28.3% | 59.99% | 5.09% | 28.0% | 0.5 | 5.09% | 28.0% |
| meta prompt-guard (86M) | 0.704 | 32.6% | 60.78% | 43.48% | 72.2% | 0.5 | 43.48% | 72.2% |

_Generated 2026-10-19 via `python -m scripts.analyze_operating_points --within-set` from dumped per-prompt scores. No model inference; reproducible offline._
