"""List the committed score files that need a GPU re-score, and the commands to do it.

A score file is *pending* when it predates a loader/scoring change for its
dataset (``pidbench.scores_io.ROWS_CHANGED``): its scores no longer align with
the rows the current loaders produce, so every table shows those cells as
"pending re-score" instead of using them. This script reads the committed score
directories (no GPU, no dataset download) and prints, per scoring script, the
exact command that re-scores every pending set for every model in models.yaml.

    python -m scripts.rescore_plan            # human-readable plan
    python -m scripts.rescore_plan --json     # machine-readable (used by the notebook)
    python -m scripts.rescore_plan --check    # exit 1 while anything is pending

Re-scoring never reuses a subset of models: each command scores ALL registry
entries on the changed set, so every model's cell comes from the same run and
the same protocol.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pidbench.scores_io import check_alignment, load_all_scores

# EvalSet name -> (scoring script, its --dataset key, score dir, extra flags)
_RESCORE = {
    "bipia/indirect": ("scripts.eval_indirect", "bipia", "results/scores_indirect", []),
    "injecagent/enhanced": ("scripts.eval_indirect", "injecagent", "results/scores_indirect", []),
    "injecagent_mt/all_enhanced": (
        "scripts.eval_multiturn",
        "injecagent",
        "results/scores_multiturn",
        ["--chunk"],
    ),
    "agentdojo_mt": (
        "scripts.eval_multiturn",
        "agentdojo",
        "results/scores_multiturn",
        ["--chunk"],
    ),
    "asb_mt": ("scripts.eval_multiturn", "asb", "results/scores_multiturn", ["--chunk"]),
    "mhj_mt": ("scripts.eval_multiturn", "mhj", "results/scores_multiturn", ["--chunk"]),
}
SCORE_DIRS = ["results/scores", "results/scores_indirect", "results/scores_multiturn"]


def pending_cells(dirs: list[str] = SCORE_DIRS) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for d in dirs:
        if Path(d).exists():
            out.update(check_alignment(load_all_scores(d))[1])
    return out


def plan(pending: dict[tuple[str, str], str]) -> list[list[str]]:
    """One command per scoring script, covering every pending dataset it owns."""
    by_script: dict[tuple[str, str, tuple[str, ...]], list[str]] = {}
    unknown = sorted({ds for _, ds in pending if ds not in _RESCORE})
    if unknown:
        raise SystemExit(f"no re-score recipe for pending set(s): {', '.join(unknown)}")
    for ds in sorted({ds for _, ds in pending}):
        script, key, out_dir, flags = _RESCORE[ds]
        by_script.setdefault((script, out_dir, tuple(flags)), []).append(key)
    cmds = []
    for (script, out_dir, flags), keys in sorted(by_script.items()):
        cmd = ["python", "-m", script]
        for k in keys:
            cmd += ["--dataset", k]
        cmd += [*flags, "--dump-scores", out_dir]
        if script == "scripts.eval_indirect":
            # write the partial run's tables aside; the published tables are rebuilt
            # from the scores by rebuild_results_from_scores afterwards
            cmd += ["--output-dir", "rescore_tmp"]
        cmds.append(cmd)
    return cmds


def main() -> int:
    p = argparse.ArgumentParser(prog="scripts.rescore_plan")
    p.add_argument("--json", action="store_true")
    p.add_argument("--check", action="store_true", help="exit 1 while anything is pending")
    args = p.parse_args()
    pending = pending_cells()
    cmds = plan(pending)
    if args.json:
        print(
            json.dumps(
                {
                    "pending": [
                        {"runner": r, "dataset": d, "reason": w}
                        for (r, d), w in sorted(pending.items())
                    ],
                    "commands": cmds,
                },
                indent=2,
            )
        )
    else:
        if not pending:
            print("nothing pending — every committed score file aligns with the current loaders")
        for ds in sorted({d for _, d in pending}):
            runners = sorted(r for r, d in pending if d == ds)
            why = next(w for (r, d), w in pending.items() if d == ds)
            print(f"pending  {ds:<28} {len(runners):>2} model(s) — {why}")
        for cmd in cmds:
            print("  " + " ".join(cmd))
    return 1 if (args.check and pending) else 0


if __name__ == "__main__":
    sys.exit(main())
