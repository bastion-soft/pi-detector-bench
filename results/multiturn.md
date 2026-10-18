# Multi-turn / cross-step prompt-injection results

Conversations are model-agnostic (fixed absolute lengths/depths); each model reads them through its own window, keeping the most recent turns (**max_len** column). Families are reported separately — different threat models, never averaged. Recall is then stratified along the axis that varies per family: injection **depth** (cross-step) or conversation **length** (jailbreak).

> The cross-step headline AUC pools all injection depths, so it blends easy (recent) and hard (deeply-buried) cases — read it alongside the depth table, where a short-window model can be excellent at shallow injections yet collapse on deep ones.

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

**Detection rate (recall @0.5) by injection depth** — chars of context after the poison (keep-recent truncation). A cliff = the poison fell outside the model's window ('step-1 poisons step-4'); a flat line = the window reaches it.

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
| wolf-defender (0.3B) | 8192 | 0.871 | 0.412 | 0.193 |
| sentinel (qualifire, 395M) | 8192 | 0.859 | 0.605 | 0.210 |
| wolf-defender-small (0.1B) | 8192 | 0.829 | 0.555 | 0.256 |
| meta prompt-guard (86M) | 512 | 0.821 | 0.480 | 0.244 |
| bastion-prompt-protection (70M) | 512 | 0.814 | 0.682 | 0.275 |
| proventra mdeberta (280M) | 512 | 0.789 | 0.532 | 0.268 |
| deepset injection (184M) | 512 | 0.761 | 0.667 | 0.349 |
| fmops distilbert (67M) | 512 | 0.735 | 0.738 | 0.333 |
| protectai v2 (184M) | 512 | 0.664 | 0.767 | 0.376 |
| hlyn judge (70M) | 512 | 0.661 | 0.925 | 0.368 |
| meta prompt-guard v2 (86M) | 512 | 0.542 | 0.983 | 0.421 |
| meta prompt-guard v2 (22M) | 512 | 0.459 | 0.905 | 0.541 |

**Detection rate (recall @0.5) by conversation length** — total innocent buildup before the payload. These crescendo/coreference attacks place the payload in the most recent turn (kept under keep-recent truncation), so more buildup tends to mean *more* accumulated attack signal — recall usually rises, not falls, with length.

| Model | ≤256tok | 256–512tok | 512–1k tok | 1k–2k tok |
|---|---|---|---|---|
| wolf-defender (0.3B) | 0.76 | 0.82 | 0.87 | 0.84 |
| sentinel (qualifire, 395M) | 0.79 | 0.87 | 0.80 | 0.84 |
| wolf-defender-small (0.1B) | 0.76 | 0.72 | 0.71 | 0.76 |
| meta prompt-guard (86M) | 0.94 | 0.89 | 0.95 | 1.00 |
| bastion-prompt-protection (70M) | 0.32 | 0.44 | 0.76 | 0.72 |
| proventra mdeberta (280M) | 0.68 | 0.70 | 0.83 | 0.92 |
| deepset injection (184M) | 1.00 | 1.00 | 1.00 | 1.00 |
| fmops distilbert (67M) | 1.00 | 1.00 | 1.00 | 1.00 |
| protectai v2 (184M) | 0.37 | 0.31 | 0.32 | 0.44 |
| hlyn judge (70M) | 0.25 | 0.23 | 0.26 | 0.48 |
| meta prompt-guard v2 (86M) | 0.27 | 0.25 | 0.38 | 0.48 |
| meta prompt-guard v2 (22M) | 0.00 | 0.00 | 0.00 | 0.00 |

Held-out public benchmarks (held out by construction for detectors that didn't train on them). Static assembly — no agent execution. Scored pure-model via the same path as every other leaderboard.

_Generated 2026-10-19 via `python -m scripts.analyze_multiturn`._
