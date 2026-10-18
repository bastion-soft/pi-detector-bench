## False-positive rate (benign flagged as attack, lower = better)

| Model | WildChat @0.5 | LMSYS @0.5 | **Avg @0.5** | declared thr | WildChat @thr | LMSYS @thr | **Avg @thr** |
|---|---|---|---|---|---|---|---|
| meta prompt-guard v2 (22M) | 0.86% | 0.68% | **0.77%** | 0.5 | 0.86% | 0.68% | **0.77%** |
| bastion-prompt-protection (70M) | 1.18% | 1.30% | **1.24%** | 0.5 | 1.18% | 1.30% | **1.24%** |
| meta prompt-guard v2 (86M) | 1.80% | 7.96% | **4.88%** | 0.5 | 1.80% | 7.96% | **4.88%** |
| protectai v2 (184M) | 7.60% | 10.04% | **8.82%** | 0.5 | 7.60% | 10.04% | **8.82%** |
| hlyn judge (70M) | 22.76% | 20.30% | **21.53%** | 0.5 | 22.76% | 20.30% | **21.53%** |
| proventra mdeberta (280M) | 18.18% | 25.48% | **21.83%** | 0.5 | 18.18% | 25.48% | **21.83%** |
| sentinel (qualifire, 395M) | 23.82% | 23.38% | **23.60%** | 0.5 | 23.82% | 23.38% | **23.60%** |
| wolf-defender (0.3B) | 18.80% | 29.26% | **24.03%** | 0.5 | 18.80% | 29.26% | **24.03%** |
| wolf-defender-small (0.1B) | 23.76% | 33.82% | **28.79%** | 0.5 | 23.76% | 33.82% | **28.79%** |
| fmops distilbert (67M) | 65.14% | 64.82% | **64.98%** | 0.5 | 65.14% | 64.82% | **64.98%** |
| deepset injection (184M) | 67.20% | 64.58% | **65.89%** | 0.5 | 67.20% | 64.58% | **65.89%** |
| meta prompt-guard (86M) | 85.60% | 91.00% | **88.30%** | 0.5 | 85.60% | 91.00% | **88.30%** |

Benign real-user openers (WildChat / LMSYS first-user turns); the share each model wrongly flags as an attack. Lower is better. **@thr** is the threshold the model's maintainer declares (`threshold:` in models.yaml; 0.5 when none is declared, in which case both column groups agree).

_Generated 2026-10-19 via `python -m scripts.measure_false_positives` / `scripts.rebuild_results_from_scores`._
