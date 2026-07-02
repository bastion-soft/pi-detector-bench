## Indirect / structured — false positives at a fixed 95% catch rate

Each set is matched injected-vs-benign structured data. The threshold is set per detector to catch 95% of that set's injections; the cell is the share of **benign structured records** wrongly flagged at that catch rate. Low = catches the injection without tripping on legitimate structured data. Threshold-agnostic (per-set tuned).

| Detector | agentdojo/agent | bipia/indirect | hackaprompt/direct | injecagent/enhanced | tensortrust/direct | zedgar/structured | **Avg** |
|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 43.30% | 46.00% | 0.00% | 0.00% | 10.25% | 0.00% | **16.59%** |
| meta prompt-guard v2 (86M) | 83.50% | 81.00% | 0.00% | 76.25% | 6.50% | 11.33% | **43.10%** |
| wolf-defender (0.3B) | 91.75% | 87.00% | 0.00% | 58.75% | 13.50% | 23.67% | **45.78%** |
| deepset injection (184M) | 77.32% | 83.00% | 0.00% | 64.75% | 23.25% | 46.00% | **49.05%** |
| wolf-defender-small (0.1B) | 73.20% | 86.00% | 0.00% | 88.25% | 17.00% | 46.33% | **51.80%** |
| meta prompt-guard v2 (22M) | 96.91% | 90.00% | 1.79% | 76.50% | 20.25% | 29.67% | **52.52%** |
| fmops distilbert (67M) | 87.63% | 81.50% | 0.00% | 100.00% | 11.75% | 37.00% | **52.98%** |
| proventra mdeberta (280M) | 85.57% | 87.00% | 3.57% | 76.50% | 58.00% | 12.33% | **53.83%** |
| protectai v2 (184M) | 100.00% | 96.50% | 0.00% | 59.00% | 2.75% | 67.33% | **54.26%** |
| sentinel (qualifire, 395M) | 77.32% | 100.00% | 10.71% | 100.00% | 30.00% | 39.83% | **59.64%** |
| hlyn judge (70M) | 87.63% | 98.50% | 0.00% | 53.00% | 69.50% | 51.50% | **60.02%** |
| meta prompt-guard (86M) | 75.26% | 28.00% | 46.43% | 88.00% | 53.50% | 73.00% | **60.70%** |

## Indirect / structured — summary (averaged across sets)

| Detector | Avg AUC | Avg EER | Avg FPR @ 95% catch |
|---|---|---|---|
| bastion-prompt-protection (70M) | 0.952 | 9.2% | 16.59% |
| meta prompt-guard v2 (86M) | 0.789 | 25.4% | 43.10% |
| wolf-defender (0.3B) | 0.865 | 19.1% | 45.78% |
| deepset injection (184M) | 0.787 | 29.0% | 49.05% |
| wolf-defender-small (0.1B) | 0.825 | 22.2% | 51.80% |
| meta prompt-guard v2 (22M) | 0.771 | 25.9% | 52.52% |
| fmops distilbert (67M) | 0.765 | 26.7% | 52.98% |
| proventra mdeberta (280M) | 0.821 | 22.8% | 53.83% |
| protectai v2 (184M) | 0.816 | 21.6% | 54.26% |
| sentinel (qualifire, 395M) | 0.823 | 23.6% | 59.64% |
| hlyn judge (70M) | 0.762 | 28.2% | 60.02% |
| meta prompt-guard (86M) | 0.705 | 32.5% | 60.70% |

_Generated 2026-07-02 via `python -m scripts.analyze_operating_points --within-set` from dumped per-prompt scores. No model inference; reproducible offline._
