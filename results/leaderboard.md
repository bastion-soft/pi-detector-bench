## Leaderboard — AUC

| Model | rogue (5k) | xTRam1 test (2k) | S-Labs test (2k) | **Avg** |
|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.986 | 0.998 | 0.996 | **0.993** |
| wolf-defender (0.3B) | 0.988 | 0.996 | 0.986 | **0.990** |
| wolf-defender-small (0.1B) | 0.977 | 0.994 | 0.982 | **0.984** |
| sentinel (qualifire, 395M) | 0.995 | 0.988 | 0.944 | **0.975** |
| hlyn judge (70M) | 0.980 | 0.995 | 0.891 | **0.956** |
| meta prompt-guard v2 (86M) | 0.882 | 0.973 | 0.922 | **0.926** |
| protectai v2 (184M) | 0.821 | 0.988 | 0.960 | **0.923** |
| proventra mdeberta (280M) | 0.867 | 0.906 | 0.954 | **0.909** |
| meta prompt-guard v2 (22M) | 0.820 | 0.893 | 0.772 | **0.828** |
| deepset injection (184M) | 0.787 | 0.666 | 0.961 | **0.805** |
| fmops distilbert (67M) | 0.788 | 0.514 | 0.907 | **0.736** |
| meta prompt-guard (86M) | 0.319 | 0.215 | 0.369 | **0.301** |

## Leaderboard — F1 @ threshold=0.5

| Model | rogue (5k) | xTRam1 test (2k) | S-Labs test (2k) | **Avg** |
|---|---|---|---|---|
| bastion-prompt-protection (70M) | 0.916 | 0.941 | 0.955 | **0.937** |
| wolf-defender (0.3B) | 0.940 | 0.976 | 0.865 | **0.927** |
| wolf-defender-small (0.1B) | 0.911 | 0.957 | 0.896 | **0.921** |
| sentinel (qualifire, 395M) | 0.976 | 0.927 | 0.810 | **0.904** |
| hlyn judge (70M) | 0.833 | 0.844 | 0.326 | **0.668** |
| meta prompt-guard v2 (86M) | 0.657 | 0.681 | 0.597 | **0.645** |
| protectai v2 (184M) | 0.656 | 0.912 | 0.826 | **0.798** |
| proventra mdeberta (280M) | 0.734 | 0.814 | 0.641 | **0.730** |
| meta prompt-guard v2 (22M) | 0.185 | 0.439 | 0.340 | **0.321** |
| deepset injection (184M) | 0.659 | 0.547 | 0.877 | **0.694** |
| fmops distilbert (67M) | 0.660 | 0.533 | 0.776 | **0.656** |
| meta prompt-guard (86M) | 0.555 | 0.484 | 0.671 | **0.570** |

## Latency (p50 ms / sample, batched inference)

| Model | rogue (5k) | xTRam1 test (2k) | S-Labs test (2k) |
|---|---|---|---|
| bastion-prompt-protection (70M) | 4.2 | 4.1 | 0.8 |
| wolf-defender (0.3B) | 8.5 | 8.5 | 0.7 |
| wolf-defender-small (0.1B) | 4.1 | 4.1 | 0.7 |
| sentinel (qualifire, 395M) | 22.4 | 22.4 | 1.2 |
| hlyn judge (70M) | 4.1 | 4.1 | 0.8 |
| meta prompt-guard v2 (86M) | 9.7 | 9.6 | 0.8 |
| protectai v2 (184M) | 9.6 | 9.6 | 0.8 |
| proventra mdeberta (280M) | 9.7 | 9.6 | 0.8 |
| meta prompt-guard v2 (22M) | 4.1 | 4.1 | 0.8 |
| deepset injection (184M) | 9.6 | 9.6 | 0.8 |
| fmops distilbert (67M) | 3.3 | 3.2 | 0.2 |
| meta prompt-guard (86M) | 9.7 | 9.7 | 0.8 |

_Generated 2026-10-19 via `python -m scripts.run_leaderboard`._
