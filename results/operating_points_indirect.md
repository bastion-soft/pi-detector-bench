## Indirect / structured — false positives at a fixed 95% catch rate

Each set is matched injected-vs-benign structured data. The threshold is set per detector to catch 95% of that set's injections; the cell is the share of **benign structured records** wrongly flagged at that catch rate. Low = catches the injection without tripping on legitimate structured data. Threshold-agnostic (per-set tuned).

| Detector | agentdojo/agent | bipia/indirect | hackaprompt/direct | injecagent/enhanced | tensortrust/direct | zedgar/structured | **Avg** |
|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 43.30% | pending re-score | 0.00% | 0.00% | 10.25% | 0.00% | **10.71%** |
| meta prompt-guard v2 (86M) | 83.50% | pending re-score | 0.00% | 76.25% | 6.50% | 11.33% | **35.52%** |
| wolf-defender (0.3B) | 91.75% | pending re-score | 0.00% | 58.75% | 13.50% | 23.67% | **37.53%** |
| deepset injection (184M) | 77.32% | pending re-score | 0.00% | 64.75% | 23.25% | 46.00% | **42.26%** |
| wolf-defender-small (0.1B) | 73.20% | pending re-score | 0.00% | 88.25% | 17.00% | 46.33% | **44.96%** |
| meta prompt-guard v2 (22M) | 96.91% | pending re-score | 1.79% | 76.50% | 20.25% | 29.67% | **45.02%** |
| protectai v2 (184M) | 100.00% | pending re-score | 0.00% | 59.00% | 2.75% | 67.33% | **45.82%** |
| proventra mdeberta (280M) | 85.57% | pending re-score | 3.57% | 76.50% | 58.00% | 12.33% | **47.19%** |
| fmops distilbert (67M) | 87.63% | pending re-score | 0.00% | 100.00% | 11.75% | 37.00% | **47.28%** |
| sentinel (qualifire, 395M) | 77.32% | pending re-score | 10.71% | 100.00% | 30.00% | 39.83% | **51.57%** |
| hlyn judge (70M) | 87.63% | pending re-score | 0.00% | 53.00% | 69.50% | 51.33% | **52.29%** |
| meta prompt-guard (86M) | 75.26% | pending re-score | 46.43% | 88.00% | 53.50% | 73.00% | **67.24%** |

_pending re-score_: the loader for these sets changed in the 2026-11 revision (row order is now deterministic), so the committed scores no longer align with the rows; averages are over the remaining sets until the re-score lands.

## Indirect / structured — summary (averaged across sets)

| Detector | Avg AUC | Avg EER | Avg FPR @ 95% catch | Avg FPR @0.5 | Avg recall @0.5 | declared thr | Avg FPR @thr | Avg recall @thr |
|---|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.968 | 6.8% | 10.71% | 20.20% | 91.1% | 0.5 | 20.20% | 91.1% |
| meta prompt-guard v2 (86M) | 0.813 | 22.7% | 35.52% | 0.43% | 40.5% | 0.5 | 0.43% | 40.5% |
| wolf-defender (0.3B) | 0.917 | 14.0% | 37.53% | 5.90% | 79.1% | 0.5 | 5.90% | 79.1% |
| deepset injection (184M) | 0.825 | 25.3% | 42.26% | 63.59% | 98.7% | 0.5 | 63.59% | 98.7% |
| wolf-defender-small (0.1B) | 0.867 | 18.1% | 44.96% | 7.32% | 65.7% | 0.5 | 7.32% | 65.7% |
| meta prompt-guard v2 (22M) | 0.798 | 23.2% | 45.02% | 0.08% | 17.8% | 0.5 | 0.08% | 17.8% |
| protectai v2 (184M) | 0.896 | 14.2% | 45.82% | 4.94% | 64.7% | 0.5 | 4.94% | 64.7% |
| proventra mdeberta (280M) | 0.851 | 19.4% | 47.19% | 5.34% | 58.1% | 0.5 | 5.34% | 58.1% |
| fmops distilbert (67M) | 0.788 | 24.4% | 47.28% | 62.35% | 99.5% | 0.5 | 62.35% | 99.5% |
| sentinel (qualifire, 395M) | 0.868 | 20.1% | 51.57% | 6.83% | 60.0% | 0.5 | 6.83% | 60.0% |
| hlyn judge (70M) | 0.809 | 24.6% | 52.29% | 6.11% | 33.0% | 0.5 | 6.11% | 33.0% |
| meta prompt-guard (86M) | 0.663 | 35.5% | 67.24% | 48.47% | 70.1% | 0.5 | 48.47% | 70.1% |

_Generated 2026-10-19 via `python -m scripts.analyze_operating_points --within-set` from dumped per-prompt scores. No model inference; reproducible offline._
