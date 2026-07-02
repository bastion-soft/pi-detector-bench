## Indirect / structured injection — AUC

| Model | Z-Edgar | BIPIA | InjecAgent | AgentDojo | HackAPrompt | TensorTrust | **Avg** |
|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 1.000 | 0.869 | 0.999 | 0.861 | 0.999 | 0.982 | **0.952** |
| wolf-defender (0.3B) | 0.968 | 0.608 | 0.909 | 0.736 | 1.000 | 0.972 | **0.865** |
| wolf-defender-small (0.1B) | 0.910 | 0.615 | 0.724 | 0.727 | 1.000 | 0.975 | **0.825** |
| sentinel (qualifire, 395M) | 0.910 | 0.598 | 0.800 | 0.730 | 0.977 | 0.923 | **0.823** |
| proventra mdeberta (280M) | 0.970 | 0.669 | 0.825 | 0.535 | 0.996 | 0.929 | **0.821** |
| protectai v2 (184M) | 0.880 | 0.412 | 0.819 | 0.799 | 1.000 | 0.983 | **0.816** |
| meta prompt-guard v2 (86M) | 0.963 | 0.671 | 0.599 | 0.532 | 1.000 | 0.970 | **0.789** |
| deepset injection (184M) | 0.881 | 0.597 | 0.732 | 0.595 | 1.000 | 0.917 | **0.787** |
| meta prompt-guard v2 (22M) | 0.928 | 0.639 | 0.717 | 0.383 | 0.996 | 0.965 | **0.771** |
| fmops distilbert (67M) | 0.860 | 0.647 | 0.579 | 0.523 | 1.000 | 0.977 | **0.765** |
| meta prompt-guard (86M) | 0.756 | 0.917 | 0.656 | 0.404 | 0.690 | 0.809 | **0.705** |

## Indirect / structured injection — F1 @ threshold=0.5

| Model | Z-Edgar | BIPIA | InjecAgent | AgentDojo | HackAPrompt | TensorTrust | **Avg** |
|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.998 | 0.751 | 0.971 | 0.604 | 0.981 | 0.703 | **0.835** |
| wolf-defender (0.3B) | 0.940 | 0.274 | 0.616 | 0.630 | 1.000 | 0.910 | **0.728** |
| wolf-defender-small (0.1B) | 0.840 | 0.430 | 0.337 | 0.409 | 1.000 | 0.892 | **0.651** |
| sentinel (qualifire, 395M) | 0.836 | 0.307 | 0.276 | 0.526 | 0.841 | 0.830 | **0.603** |
| proventra mdeberta (280M) | 0.891 | 0.326 | 0.486 | 0.267 | 0.919 | 0.771 | **0.610** |
| protectai v2 (184M) | 0.846 | 0.206 | 0.316 | 0.378 | 0.991 | 0.946 | **0.614** |
| meta prompt-guard v2 (86M) | 0.593 | 0.020 | 0.005 | 0.000 | 0.996 | 0.747 | **0.393** |
| deepset injection (184M) | 0.667 | 0.667 | 0.667 | 0.394 | 1.000 | 0.832 | **0.704** |
| meta prompt-guard v2 (22M) | 0.119 | 0.000 | 0.000 | 0.000 | 0.639 | 0.523 | **0.214** |
| fmops distilbert (67M) | 0.667 | 0.667 | 0.667 | 0.378 | 1.000 | 0.897 | **0.712** |
| meta prompt-guard (86M) | 0.570 | 0.827 | 0.399 | 0.358 | 0.947 | 0.738 | **0.640** |

Held-out indirect/structured sets, scored pure-model. Reported separately from the direct leaderboard — competitors target plain-prose injection, so this is a distinct capability axis, not folded into the main average.

_Generated 2026-07-02 via `python -m scripts.eval_indirect`._
