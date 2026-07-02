# Multi-turn / cross-step prompt-injection results

Conversations scored at natural length; each model truncates to its own window (**max_len** column). Families are reported separately — different threat models, never averaged together.

## Cross-step agent injection (poisoned tool output)

| Model | max_len | AUC | FPR@95%-catch | EER |
|---|---|---|---|---|
| wolf-defender (0.3B) | 512 | 0.881 | 0.245 | 0.154 |
| wolf-defender-small (0.1B) | 512 | 0.848 | 0.323 | 0.154 |
| sentinel (qualifire, 395M) | 512 | 0.839 | 0.530 | 0.241 |
| bastion-prompt-protection (70M) | 512 | 0.837 | 0.512 | 0.192 |
| deepset injection (184M) | 512 | 0.820 | 0.542 | 0.239 |
| meta prompt-guard v2 (86M) | 512 | 0.817 | 0.357 | 0.198 |
| proventra mdeberta (280M) | 512 | 0.809 | 0.340 | 0.194 |
| protectai v2 (184M) | 512 | 0.773 | 0.486 | 0.299 |
| fmops distilbert (67M) | 512 | 0.758 | 0.623 | 0.288 |
| meta prompt-guard (86M) | 512 | 0.758 | 0.507 | 0.230 |
| meta prompt-guard v2 (22M) | 512 | 0.738 | 0.467 | 0.298 |

**Detection rate (recall @0.5) — by conversation length and injection position.** A recall cliff on long conversations or early injections = the model's window can't see the poison.

| Model | ≤256tok | 256–512tok | 512–1k tok | late |
|---|---|---|---|---|
| wolf-defender (0.3B) | 0.77 | 1.00 | 0.83 | 0.77 |
| wolf-defender-small (0.1B) | 0.67 | 1.00 | 0.83 | 0.68 |
| sentinel (qualifire, 395M) | 0.57 | 0.90 | 0.83 | 0.58 |
| bastion-prompt-protection (70M) | 0.86 | 1.00 | 0.67 | 0.86 |
| deepset injection (184M) | 1.00 | 1.00 | 1.00 | 1.00 |
| meta prompt-guard v2 (86M) | 0.56 | 1.00 | 0.67 | 0.57 |
| proventra mdeberta (280M) | 1.00 | 1.00 | 0.83 | 1.00 |
| protectai v2 (184M) | 0.28 | 0.38 | 0.00 | 0.28 |
| fmops distilbert (67M) | 1.00 | 1.00 | 1.00 | 1.00 |
| meta prompt-guard (86M) | 0.55 | 1.00 | 0.67 | 0.56 |
| meta prompt-guard v2 (22M) | 0.03 | 0.00 | 0.00 | 0.03 |

## Multi-turn jailbreak (conversational)

| Model | max_len | AUC | FPR@95%-catch | EER |
|---|---|---|---|---|
| bastion-prompt-protection (70M) | 512 | 0.805 | 0.667 | 0.262 |
| wolf-defender (0.3B) | 512 | 0.664 | 0.760 | 0.353 |
| protectai v2 (184M) | 512 | 0.656 | 0.706 | 0.384 |
| wolf-defender-small (0.1B) | 512 | 0.626 | 0.709 | 0.411 |
| sentinel (qualifire, 395M) | 512 | 0.588 | 0.884 | 0.440 |
| meta prompt-guard v2 (22M) | 512 | 0.558 | 0.762 | 0.459 |
| fmops distilbert (67M) | 512 | 0.505 | 0.924 | 0.496 |
| meta prompt-guard (86M) | 512 | 0.469 | 0.864 | 0.517 |
| deepset injection (184M) | 512 | 0.440 | 0.903 | 0.566 |
| proventra mdeberta (280M) | 512 | 0.438 | 0.979 | 0.547 |
| meta prompt-guard v2 (86M) | 512 | 0.336 | 0.989 | 0.604 |

**Detection rate (recall @0.5) — by conversation length and injection position.** A recall cliff on long conversations or early injections = the model's window can't see the poison.

| Model | ≤256tok | 256–512tok | 512–1k tok | >1k tok | late |
|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.29 | 0.35 | 0.36 | 0.32 | 0.32 |
| wolf-defender (0.3B) | 0.38 | 0.38 | 0.64 | 0.52 | 0.41 |
| protectai v2 (184M) | 0.34 | 0.16 | 0.21 | 0.24 | 0.27 |
| wolf-defender-small (0.1B) | 0.37 | 0.32 | 0.53 | 0.56 | 0.38 |
| sentinel (qualifire, 395M) | 0.46 | 0.46 | 0.62 | 0.56 | 0.48 |
| meta prompt-guard v2 (22M) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| fmops distilbert (67M) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| meta prompt-guard (86M) | 0.55 | 0.52 | 0.68 | 0.84 | 0.56 |
| deepset injection (184M) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| proventra mdeberta (280M) | 0.39 | 0.35 | 0.40 | 0.48 | 0.38 |
| meta prompt-guard v2 (86M) | 0.20 | 0.16 | 0.14 | 0.36 | 0.18 |

## Agent-jailbreak by user (separate threat model)

| Model | max_len | AUC | FPR@95%-catch | EER |
|---|---|---|---|---|
| wolf-defender (0.3B) | 512 | 0.852 | 0.670 | 0.236 |
| wolf-defender-small (0.1B) | 512 | 0.782 | 0.812 | 0.267 |
| sentinel (qualifire, 395M) | 512 | 0.779 | 0.795 | 0.256 |
| meta prompt-guard v2 (86M) | 512 | 0.731 | 0.818 | 0.315 |
| bastion-prompt-protection (70M) | 512 | 0.698 | 0.886 | 0.341 |
| deepset injection (184M) | 512 | 0.641 | 0.909 | 0.381 |
| meta prompt-guard v2 (22M) | 512 | 0.639 | 0.875 | 0.409 |
| proventra mdeberta (280M) | 512 | 0.624 | 0.824 | 0.423 |
| protectai v2 (184M) | 512 | 0.574 | 1.000 | 0.435 |
| fmops distilbert (67M) | 512 | 0.574 | 0.955 | 0.452 |
| meta prompt-guard (86M) | 512 | 0.548 | 0.903 | 0.463 |

**Detection rate (recall @0.5) — by conversation length and injection position.** A recall cliff on long conversations or early injections = the model's window can't see the poison.

| Model | ≤256tok |
|---|---|
| wolf-defender (0.3B) | 0.78 |
| wolf-defender-small (0.1B) | 0.90 |
| sentinel (qualifire, 395M) | 0.93 |
| meta prompt-guard v2 (86M) | 0.04 |
| bastion-prompt-protection (70M) | 0.90 |
| deepset injection (184M) | 1.00 |
| meta prompt-guard v2 (22M) | 0.00 |
| proventra mdeberta (280M) | 0.84 |
| protectai v2 (184M) | 0.06 |
| fmops distilbert (67M) | 1.00 |
| meta prompt-guard (86M) | 0.94 |

Held-out public benchmarks (held out by construction for detectors that didn't train on them). Static assembly — no agent execution. Scored pure-model via the same path as every other leaderboard.

_Generated 2026-07-02 via `python -m scripts.analyze_multiturn`._
