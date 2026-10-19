# Multi-turn / cross-step prompt-injection results

Conversations are model-agnostic (fixed absolute lengths/depths); each model reads them through its own window (**max_len** column) — chunked into overlapping windows when scored with `--chunk` (the published protocol since the 2026-11 revision), otherwise keeping the most recent turns. Families are reported separately — different threat models, never averaged. Recall is then stratified along the axis that varies per family: injection **depth** (cross-step) or conversation **length** (jailbreak).

> The cross-step headline AUC pools all injection depths, so it blends easy (recent) and hard (deeply-buried) cases — read it alongside the depth table.

## Cross-step agent injection (poisoned tool output)

| Model | max_len | AUC | FPR@95%-catch | EER | FPR @0.5 | recall @0.5 | declared thr | FPR @thr | recall @thr |
|---|---|---|---|---|---|---|---|---|---|
| wolf-defender (0.3B) | 8192 | 0.859 | 0.579 | 0.195 | 0.085 | 0.622 | 0.5 | 0.085 | 0.622 |
| wolf-defender-small (0.1B) | 8192 | 0.848 | 0.447 | 0.200 | 0.127 | 0.686 | 0.5 | 0.127 | 0.686 |
| bastion-prompt-protection (70M) | 512 | 0.845 | 0.467 | 0.193 | 0.310 | 0.842 | 0.5 | 0.310 | 0.842 |
| meta prompt-guard v2 (86M) | 512 | 0.770 | 0.434 | 0.267 | 0.422 | 0.848 | 0.5 | 0.422 | 0.848 |
| proventra mdeberta (280M) | 512 | 0.754 | 0.617 | 0.289 | 0.789 | 0.995 | 0.5 | 0.789 | 0.995 |
| meta prompt-guard (86M) | 512 | 0.728 | 0.659 | 0.335 | 0.774 | 0.904 | 0.5 | 0.774 | 0.904 |
| sentinel (qualifire, 395M) | 8192 | 0.688 | 0.871 | 0.364 | 0.180 | 0.408 | 0.5 | 0.180 | 0.408 |
| hlyn judge (70M) | 512 | 0.662 | 0.806 | 0.376 | 0.103 | 0.180 | 0.5 | 0.103 | 0.180 |
| protectai v2 (184M) | 512 | 0.636 | 0.833 | 0.408 | 0.172 | 0.380 | 0.5 | 0.172 | 0.380 |
| deepset injection (184M) | 512 | 0.554 | 0.949 | 0.464 | 1.000 | 1.000 | 0.5 | 1.000 | 1.000 |
| meta prompt-guard v2 (22M) | 512 | 0.550 | 0.851 | 0.468 | 0.057 | 0.085 | 0.5 | 0.057 | 0.085 |
| fmops distilbert (67M) | 512 | 0.518 | 0.952 | 0.482 | 1.000 | 1.000 | 0.5 | 1.000 | 1.000 |

**Detection rate (recall @0.5) by injection depth** — chars of context after the poison. Under keep-recent truncation a cliff means the poison fell outside the model's window ('step-1 poisons step-4'); chunked scoring (`--chunk`) reads every window, so a cliff there is a detection limit.

| Model | 0 (last turn) | ≤256tok deep | 256–512tok | 512–1k tok | >1k tok deep |
|---|---|---|---|---|---|
| wolf-defender (0.3B) | 0.87 | 1.00 | 0.76 | 0.60 | 0.40 |
| wolf-defender-small (0.1B) | 0.86 | 1.00 | 0.79 | 0.67 | 0.49 |
| bastion-prompt-protection (70M) | 0.97 | 1.00 | 0.75 | 0.73 | 0.79 |
| meta prompt-guard v2 (86M) | 0.65 | 1.00 | 0.85 | 0.82 | 0.88 |
| proventra mdeberta (280M) | 1.00 | 1.00 | 1.00 | 0.99 | 0.99 |
| meta prompt-guard (86M) | 0.61 | 0.50 | 0.88 | 0.90 | 1.00 |
| sentinel (qualifire, 395M) | 0.80 | 1.00 | 0.43 | 0.30 | 0.23 |
| hlyn judge (70M) | 0.42 | 0.00 | 0.08 | 0.06 | 0.16 |
| protectai v2 (184M) | 0.38 | 0.00 | 0.25 | 0.25 | 0.42 |
| deepset injection (184M) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| meta prompt-guard v2 (22M) | 0.02 | 0.00 | 0.08 | 0.06 | 0.13 |
| fmops distilbert (67M) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## Multi-turn jailbreak (conversational)

| Model | max_len | AUC | FPR@95%-catch | EER | FPR @0.5 | recall @0.5 | declared thr | FPR @thr | recall @thr |
|---|---|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | 512 | 0.865 | 0.425 | 0.209 | 0.095 | 0.460 | 0.5 | 0.095 | 0.460 |
| wolf-defender (0.3B) | 8192 | 0.806 | 0.665 | 0.246 | 0.145 | 0.640 | 0.5 | 0.145 | 0.640 |
| wolf-defender-small (0.1B) | 8192 | 0.801 | 0.645 | 0.240 | 0.205 | 0.705 | 0.5 | 0.205 | 0.705 |
| sentinel (qualifire, 395M) | 8192 | 0.781 | 0.718 | 0.284 | 0.412 | 0.815 | 0.5 | 0.412 | 0.815 |
| fmops distilbert (67M) | 512 | 0.770 | 0.645 | 0.297 | 1.000 | 1.000 | 0.5 | 1.000 | 1.000 |
| meta prompt-guard v2 (22M) | 512 | 0.723 | 0.640 | 0.320 | 0.065 | 0.000 | 0.5 | 0.065 | 0.000 |
| proventra mdeberta (280M) | 512 | 0.706 | 0.685 | 0.350 | 0.430 | 0.748 | 0.5 | 0.430 | 0.748 |
| meta prompt-guard v2 (86M) | 512 | 0.643 | 0.772 | 0.386 | 0.215 | 0.318 | 0.5 | 0.215 | 0.318 |
| deepset injection (184M) | 512 | 0.576 | 0.848 | 0.451 | 0.998 | 1.000 | 0.5 | 0.998 | 1.000 |
| meta prompt-guard (86M) | 512 | 0.571 | 0.823 | 0.465 | 0.800 | 0.930 | 0.5 | 0.800 | 0.930 |
| hlyn judge (70M) | 512 | 0.553 | 0.910 | 0.458 | 0.188 | 0.260 | 0.5 | 0.188 | 0.260 |
| protectai v2 (184M) | 512 | 0.477 | 0.863 | 0.510 | 0.448 | 0.393 | 0.5 | 0.448 | 0.393 |

**Detection rate (recall @0.5) by conversation length** — total conversation size (attacks only). MHJ places the payload in the most recent user turn, so length mostly measures how much red-team buildup precedes it.

| Model | ≤256tok | 256–512tok | 512–1k tok | 1k–2k tok |
|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.32 | 0.44 | 0.68 | 0.84 |
| wolf-defender (0.3B) | 0.58 | 0.67 | 0.70 | 0.72 |
| wolf-defender-small (0.1B) | 0.66 | 0.71 | 0.75 | 0.88 |
| sentinel (qualifire, 395M) | 0.79 | 0.87 | 0.80 | 0.84 |
| fmops distilbert (67M) | 1.00 | 1.00 | 1.00 | 1.00 |
| meta prompt-guard v2 (22M) | 0.00 | 0.00 | 0.00 | 0.00 |
| proventra mdeberta (280M) | 0.68 | 0.72 | 0.89 | 0.92 |
| meta prompt-guard v2 (86M) | 0.27 | 0.26 | 0.39 | 0.64 |
| deepset injection (184M) | 1.00 | 1.00 | 1.00 | 1.00 |
| meta prompt-guard (86M) | 0.94 | 0.89 | 0.95 | 0.96 |
| hlyn judge (70M) | 0.25 | 0.23 | 0.24 | 0.52 |
| protectai v2 (184M) | 0.37 | 0.31 | 0.51 | 0.52 |

Held-out public benchmarks (held out by construction for detectors that didn't train on them). Static assembly — no agent execution. Scored pure-model via the same path as every other leaderboard.

_Generated 2026-10-19 via `python -m scripts.analyze_multiturn`._
