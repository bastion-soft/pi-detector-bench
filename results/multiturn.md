# Multi-turn / cross-step prompt-injection results

Conversations are model-agnostic (fixed absolute lengths/depths); each model reads them through its own window (**max_len** column) — chunked into overlapping windows when scored with `--chunk` (the published protocol since the 2026-11 revision), otherwise keeping the most recent turns. Families are reported separately — different threat models, never averaged. Recall is then stratified along the axis that varies per family: injection **depth** (cross-step) or conversation **length** (jailbreak).

> The cross-step headline AUC pools all injection depths, so it blends easy (recent) and hard (deeply-buried) cases — read it alongside the depth table.

> **Pending re-score.** Cells marked _pending re-score_ belong to sets whose rows or scoring protocol changed in the 2026-11 revision (MHJ benign negatives rendered user-turns-only, deterministic InjecAgent file order, chunked multi-turn scoring). The committed scores predate that change, so they are not shown. Re-score with `notebooks/rescore_revision_2026_11.ipynb`.

## Cross-step agent injection (poisoned tool output)

| Model | max_len | AUC | FPR@95%-catch | EER | FPR @0.5 | recall @0.5 | declared thr | FPR @thr | recall @thr |
|---|---|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| deepset injection (184M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| fmops distilbert (67M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| hlyn judge (70M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| meta prompt-guard (86M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| meta prompt-guard v2 (22M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| meta prompt-guard v2 (86M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| protectai v2 (184M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| proventra mdeberta (280M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| sentinel (qualifire, 395M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| wolf-defender (0.3B) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| wolf-defender-small (0.1B) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |

## Multi-turn jailbreak (conversational)

| Model | max_len | AUC | FPR@95%-catch | EER | FPR @0.5 | recall @0.5 | declared thr | FPR @thr | recall @thr |
|---|---|---|---|---|---|---|---|---|---|
| bastion-prompt-protection (70M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| deepset injection (184M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| fmops distilbert (67M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| hlyn judge (70M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| meta prompt-guard (86M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| meta prompt-guard v2 (22M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| meta prompt-guard v2 (86M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| protectai v2 (184M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| proventra mdeberta (280M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| sentinel (qualifire, 395M) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| wolf-defender (0.3B) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |
| wolf-defender-small (0.1B) | — | pending re-score | pending re-score | pending re-score | pending re-score | pending re-score | 0.5 | pending re-score | pending re-score |

Held-out public benchmarks (held out by construction for detectors that didn't train on them). Static assembly — no agent execution. Scored pure-model via the same path as every other leaderboard.

_Generated 2026-10-19 via `python -m scripts.analyze_multiturn`._
