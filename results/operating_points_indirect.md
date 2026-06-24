## Indirect / structured — false positives at a fixed 95% catch rate

Each set is matched injected-vs-benign structured data. The threshold is set per detector to catch 95% of that set's injections; the cell is the share of **benign structured records** wrongly flagged at that catch rate. Low = catches the injection without tripping on legitimate structured data. Threshold-agnostic (per-set tuned).

| Detector | agentdojo/agent | bipia/indirect | hackaprompt/direct | injecagent/enhanced | tensortrust/direct | zedgar/structured | **Avg** |
|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 43.30% | 68.50% | 0.00% | 0.00% | 10.25% | 0.00% | **20.34%** |
| wolf-defender (0.3B) | 91.75% | 90.50% | 0.00% | 58.75% | 13.50% | 23.67% | **46.36%** |
| deepset injection (184M) | 77.32% | 81.50% | 0.00% | 64.75% | 23.25% | 46.00% | **48.80%** |
| wolf-defender-small (0.1B) | 73.20% | 93.50% | 0.00% | 88.25% | 17.00% | 46.33% | **53.05%** |
| fmops distilbert (67M) | 87.63% | 83.50% | 0.00% | 100.00% | 11.75% | 37.00% | **53.31%** |
| proventra mdeberta (280M) | 85.57% | 85.00% | 3.57% | 76.50% | 58.00% | 12.33% | **53.50%** |
| protectai v2 (184M) | 100.00% | 96.50% | 0.00% | 59.00% | 2.75% | 67.33% | **54.26%** |
| sentinel (qualifire, 395M) | 77.32% | 100.00% | 10.71% | 100.00% | 30.00% | 39.83% | **59.64%** |
| hlyn judge (70M) | 87.63% | 98.50% | 0.00% | 53.00% | 69.50% | 51.50% | **60.02%** |
| meta prompt-guard (86M) | 75.26% | 28.50% | 46.43% | 88.00% | 53.50% | 73.00% | **60.78%** |

## Indirect / structured — summary (averaged across sets)

| Detector | Avg AUC | Avg EER | Avg FPR @ 95% catch |
|---|---|---|---|
| bastion-prompt-protection (70M) | 0.945 | 9.7% | 20.34% |
| wolf-defender (0.3B) | 0.866 | 18.9% | 46.36% |
| deepset injection (184M) | 0.787 | 29.0% | 48.80% |
| wolf-defender-small (0.1B) | 0.827 | 21.9% | 53.05% |
| fmops distilbert (67M) | 0.766 | 26.7% | 53.31% |
| proventra mdeberta (280M) | 0.822 | 22.9% | 53.50% |
| protectai v2 (184M) | 0.816 | 21.5% | 54.26% |
| sentinel (qualifire, 395M) | 0.818 | 24.1% | 59.64% |
| hlyn judge (70M) | 0.762 | 28.2% | 60.02% |
| meta prompt-guard (86M) | 0.704 | 32.6% | 60.78% |

_Generated 2026-06-24 via `python -m scripts.analyze_operating_points --within-set` from dumped per-prompt scores. No model inference; reproducible offline._
