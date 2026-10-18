## Indirect / structured injection — AUC

| Model | Z-Edgar | BIPIA | InjecAgent | AgentDojo | HackAPrompt | TensorTrust | **Avg** |
|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 1.000 | pending re-score | 0.999 | 0.861 | 0.999 | 0.982 | **0.968** |
| wolf-defender (0.3B) | 0.968 | pending re-score | 0.909 | 0.736 | 1.000 | 0.972 | **0.917** |
| protectai v2 (184M) | 0.880 | pending re-score | 0.819 | 0.799 | 1.000 | 0.983 | **0.896** |
| sentinel (qualifire, 395M) | 0.910 | pending re-score | 0.800 | 0.730 | 0.977 | 0.923 | **0.868** |
| wolf-defender-small (0.1B) | 0.910 | pending re-score | 0.724 | 0.727 | 1.000 | 0.975 | **0.867** |
| proventra mdeberta (280M) | 0.970 | pending re-score | 0.825 | 0.535 | 0.996 | 0.929 | **0.851** |
| deepset injection (184M) | 0.881 | pending re-score | 0.732 | 0.595 | 1.000 | 0.917 | **0.825** |
| meta prompt-guard v2 (86M) | 0.963 | pending re-score | 0.599 | 0.532 | 1.000 | 0.970 | **0.813** |
| hlyn judge (70M) | 0.867 | pending re-score | 0.835 | 0.615 | 0.999 | 0.727 | **0.809** |
| meta prompt-guard v2 (22M) | 0.928 | pending re-score | 0.717 | 0.383 | 0.996 | 0.965 | **0.798** |
| fmops distilbert (67M) | 0.860 | pending re-score | 0.579 | 0.523 | 1.000 | 0.977 | **0.788** |
| meta prompt-guard (86M) | 0.756 | pending re-score | 0.656 | 0.404 | 0.690 | 0.809 | **0.663** |

## Indirect / structured injection — F1 @ threshold=0.5

| Model | Z-Edgar | BIPIA | InjecAgent | AgentDojo | HackAPrompt | TensorTrust | **Avg** |
|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.998 | pending re-score | 0.971 | 0.604 | 0.981 | 0.703 | **0.851** |
| wolf-defender (0.3B) | 0.940 | pending re-score | 0.616 | 0.630 | 1.000 | 0.910 | **0.819** |
| protectai v2 (184M) | 0.846 | pending re-score | 0.316 | 0.378 | 0.991 | 0.946 | **0.696** |
| sentinel (qualifire, 395M) | 0.836 | pending re-score | 0.276 | 0.526 | 0.841 | 0.830 | **0.662** |
| wolf-defender-small (0.1B) | 0.840 | pending re-score | 0.337 | 0.409 | 1.000 | 0.892 | **0.695** |
| proventra mdeberta (280M) | 0.891 | pending re-score | 0.486 | 0.267 | 0.919 | 0.771 | **0.667** |
| deepset injection (184M) | 0.667 | pending re-score | 0.667 | 0.394 | 1.000 | 0.832 | **0.712** |
| meta prompt-guard v2 (86M) | 0.593 | pending re-score | 0.005 | 0.000 | 0.996 | 0.747 | **0.468** |
| hlyn judge (70M) | 0.300 | pending re-score | 0.000 | 0.000 | 0.917 | 0.651 | **0.374** |
| meta prompt-guard v2 (22M) | 0.119 | pending re-score | 0.000 | 0.000 | 0.639 | 0.523 | **0.256** |
| fmops distilbert (67M) | 0.667 | pending re-score | 0.667 | 0.378 | 1.000 | 0.897 | **0.722** |
| meta prompt-guard (86M) | 0.570 | pending re-score | 0.399 | 0.358 | 0.947 | 0.738 | **0.602** |

_pending re-score_: this set's loader changed in the 2026-11 revision (row order is now deterministic), so its committed scores no longer align with its rows. **Avg** is over the remaining sets until the re-score lands.

Held-out indirect/structured sets, scored pure-model. Reported separately from the direct leaderboard — competitors target plain-prose injection, so this is a distinct capability axis, not folded into the main average.

_Generated 2026-10-19 via `python -m scripts.eval_indirect`._
