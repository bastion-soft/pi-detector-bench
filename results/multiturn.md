# Multi-turn / cross-step prompt-injection results

Conversations are model-agnostic (fixed absolute lengths/depths); each model reads them through its own window, keeping the most recent turns (**max_len** column). Families are reported separately — different threat models, never averaged. Recall is then stratified along the axis that varies per family: injection **depth** (cross-step) or conversation **length** (jailbreak).

## Cross-step agent injection (poisoned tool output)

| Model | max_len | AUC | FPR@95%-catch | EER |
|---|---|---|---|---|
| wolf-defender (0.3B) | 8192 | 0.869 | 0.402 | 0.197 |
| wolf-defender-small (0.1B) | 8192 | 0.827 | 0.422 | 0.212 |
| sentinel (qualifire, 395M) | 8192 | 0.688 | 0.871 | 0.364 |
| meta prompt-guard (86M) | 512 | 0.580 | 0.925 | 0.451 |
| hlyn judge (70M) | 512 | 0.579 | 0.936 | 0.454 |
| protectai v2 (184M) | 512 | 0.577 | 1.000 | 0.449 |
| meta prompt-guard v2 (86M) | 512 | 0.576 | 0.938 | 0.459 |
| bastion-prompt-protection (70M) | 512 | 0.569 | 0.936 | 0.460 |
| meta prompt-guard v2 (22M) | 512 | 0.564 | 0.864 | 0.467 |
| deepset injection (184M) | 512 | 0.558 | 0.958 | 0.474 |
| proventra mdeberta (280M) | 512 | 0.532 | 0.966 | 0.495 |
| fmops distilbert (67M) | 512 | 0.521 | 0.939 | 0.489 |

**Detection rate (recall @0.5) by injection depth** — chars of context after the poison (keep-recent truncation). A cliff = the poison fell outside the model's window ('step-1 poisons step-4').

| Model | 0 (last turn) | ≤256tok deep | 256–512tok | 512–1k tok | >1k tok deep |
|---|---|---|---|---|---|
| wolf-defender (0.3B) | 0.92 | 1.00 | 0.83 | 0.82 | 0.80 |
| wolf-defender-small (0.1B) | 0.81 | 1.00 | 0.77 | 0.77 | 0.75 |
| sentinel (qualifire, 395M) | 0.80 | 1.00 | 0.43 | 0.30 | 0.23 |
| meta prompt-guard (86M) | 0.61 | 0.50 | 0.56 | 0.43 | 0.43 |
| hlyn judge (70M) | 0.41 | 0.00 | 0.17 | 0.06 | 0.13 |
| protectai v2 (184M) | 0.39 | 0.00 | 0.26 | 0.12 | 0.13 |
| meta prompt-guard v2 (86M) | 0.65 | 1.00 | 0.58 | 0.08 | 0.15 |
| bastion-prompt-protection (70M) | 0.97 | 1.00 | 0.47 | 0.16 | 0.08 |
| meta prompt-guard v2 (22M) | 0.02 | 0.00 | 0.06 | 0.02 | 0.07 |
| deepset injection (184M) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| proventra mdeberta (280M) | 1.00 | 1.00 | 0.63 | 0.06 | 0.23 |
| fmops distilbert (67M) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## Multi-turn jailbreak (conversational)

| Model | max_len | AUC | FPR@95%-catch | EER |
|---|---|---|---|---|
| bastion-prompt-protection (70M) | 512 | 0.795 | 0.699 | 0.281 |
| wolf-defender (0.3B) | 8192 | 0.732 | 0.539 | 0.314 |
| wolf-defender-small (0.1B) | 8192 | 0.683 | 0.594 | 0.379 |
| sentinel (qualifire, 395M) | 8192 | 0.652 | 0.802 | 0.383 |
| protectai v2 (184M) | 512 | 0.647 | 0.779 | 0.381 |
| fmops distilbert (67M) | 512 | 0.580 | 0.806 | 0.451 |
| meta prompt-guard (86M) | 512 | 0.571 | 0.730 | 0.421 |
| proventra mdeberta (280M) | 512 | 0.538 | 0.766 | 0.468 |
| deepset injection (184M) | 512 | 0.499 | 0.811 | 0.522 |
| hlyn judge (70M) | 512 | 0.443 | 0.961 | 0.539 |
| meta prompt-guard v2 (22M) | 512 | 0.439 | 0.838 | 0.561 |
| meta prompt-guard v2 (86M) | 512 | 0.389 | 0.989 | 0.556 |

**Detection rate (recall @0.5) by conversation length** — innocent buildup before the payload. A cliff = length dilutes or truncates the attack signal.

| Model | ≤256tok | 256–512tok | 512–1k tok | 1k–2k tok |
|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.29 | 0.35 | 0.75 | 0.72 |
| wolf-defender (0.3B) | 0.38 | 0.38 | 0.86 | 0.84 |
| wolf-defender-small (0.1B) | 0.37 | 0.32 | 0.71 | 0.76 |
| sentinel (qualifire, 395M) | 0.46 | 0.46 | 0.79 | 0.84 |
| protectai v2 (184M) | 0.34 | 0.16 | 0.32 | 0.44 |
| fmops distilbert (67M) | 1.00 | 1.00 | 1.00 | 1.00 |
| meta prompt-guard (86M) | 0.55 | 0.52 | 0.95 | 1.00 |
| proventra mdeberta (280M) | 0.39 | 0.35 | 0.82 | 0.92 |
| deepset injection (184M) | 1.00 | 1.00 | 1.00 | 1.00 |
| hlyn judge (70M) | 0.11 | 0.10 | 0.26 | 0.48 |
| meta prompt-guard v2 (22M) | 0.00 | 0.00 | 0.00 | 0.00 |
| meta prompt-guard v2 (86M) | 0.20 | 0.16 | 0.38 | 0.48 |

## Agent-jailbreak by user (separate threat model)

| Model | max_len | AUC | FPR@95%-catch | EER |
|---|---|---|---|---|
| hlyn judge (70M) | 512 | 0.869 | 0.716 | 0.202 |
| wolf-defender (0.3B) | 8192 | 0.852 | 0.670 | 0.236 |
| wolf-defender-small (0.1B) | 8192 | 0.782 | 0.812 | 0.267 |
| sentinel (qualifire, 395M) | 8192 | 0.779 | 0.795 | 0.256 |
| meta prompt-guard v2 (86M) | 512 | 0.731 | 0.818 | 0.315 |
| bastion-prompt-protection (70M) | 512 | 0.698 | 0.886 | 0.341 |
| deepset injection (184M) | 512 | 0.641 | 0.909 | 0.381 |
| meta prompt-guard v2 (22M) | 512 | 0.639 | 0.875 | 0.409 |
| proventra mdeberta (280M) | 512 | 0.624 | 0.824 | 0.423 |
| protectai v2 (184M) | 512 | 0.574 | 1.000 | 0.435 |
| fmops distilbert (67M) | 512 | 0.574 | 0.955 | 0.452 |
| meta prompt-guard (86M) | 512 | 0.548 | 0.903 | 0.463 |

Held-out public benchmarks (held out by construction for detectors that didn't train on them). Static assembly — no agent execution. Scored pure-model via the same path as every other leaderboard.

_Generated 2026-07-03 via `python -m scripts.analyze_multiturn`._
