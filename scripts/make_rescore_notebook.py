"""Generate ``notebooks/rescore_revision_2026_11.ipynb`` — the Colab re-score path
for the 2026-11 benchmark revision.

The revision changed the rows (or the scoring protocol) of some sets, so their
committed per-prompt scores no longer align and the tables show those cells as
"pending re-score". The notebook re-scores exactly those sets for every model in
models.yaml (multi-turn with ``--chunk``), rebuilds every table from the scores,
verifies nothing is left pending, and packages ``results/`` for commit.

The set list is NOT baked in: the notebook asks ``scripts.rescore_plan`` at run
time, so it stays correct if more sets become pending later.

    python -m scripts.make_rescore_notebook
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path("notebooks/rescore_revision_2026_11.ipynb")


def _md(i: int, text: str) -> dict:
    return {"cell_type": "markdown", "id": f"md{i:02d}", "metadata": {}, "source": _lines(text)}


def _code(i: int, text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": f"code{i:02d}",
        "metadata": {},
        "outputs": [],
        "source": _lines(text),
    }


def _lines(text: str) -> list[str]:
    text = text.strip("\n")
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + [parts[-1]]


CELLS = [
    _md(
        0,
        """
# Re-score for the 2026-11 benchmark revision

The 2026-11 revision (see `METHODOLOGY.md` → *Benchmark revision 2026-11*) changed the rows or
the scoring protocol of some sets:

- **multi-turn (all sets)** — scored with `--chunk` (overlapping token windows) instead of
  keep-recent truncation;
- **MHJ** — benign negatives rendered user-turns-only, like the MHJ attacks;
- **InjecAgent / BIPIA loaders** — file order now sorted (was filesystem `glob` order), where
  the committed scores could not be shown to match the sorted order.

Their committed per-prompt scores no longer align with the rows, so the published tables show
those cells as **pending re-score**. This notebook re-scores exactly those sets for **all
models in `models.yaml`** in one run (every model on the same rows and the same protocol),
rebuilds every table from the scores, and checks that nothing is left pending.

**Runtime:** GPU (*Runtime → Change runtime type → T4 GPU*). Multi-turn with `--chunk` is the
slow part (long conversations become several windows): budget ~1–2 h on a T4.
""",
    ),
    _md(1, "## 1. Code (the revision branch) + install"),
    _code(
        2,
        """
# The revision lives on a branch until it is merged; switch to "main" afterwards.
BRANCH = "revision-2026-11"
!git clone --quiet --branch {BRANCH} https://github.com/bastion-soft/pi-detector-bench.git
%cd pi-detector-bench
!git log --oneline -1
# agentdojo: one of the cross-step sources; matplotlib: plots
!pip install -q -e . agentdojo matplotlib
""",
    ),
    _md(
        3,
        """
## 2. Hugging Face token (required here)

Unlike the main notebook, this run **needs** a token: MHJ (`ScaleAI/mhj`) is gated and
`eval_multiturn` refuses a partial run, and the gated Meta Prompt-Guard models must be
re-scored too or their multi-turn cells stay pending. Accept the terms on each page first.
`hlyn-labs/prompt-injection-judge-deberta-70m` became gated after it was first scored; without
access its cells stay *pending* (reported in §5), they are never filled from old scores.
""",
    ),
    _code(
        4,
        """
from huggingface_hub import login
from google.colab import userdata

login(userdata.get("HF_TOKEN"))
""",
    ),
    _md(5, "## 3. What is pending (read from the committed score files — no GPU)"),
    _code(
        6,
        """
import json, subprocess

plan = json.loads(subprocess.check_output(["python", "-m", "scripts.rescore_plan", "--json"]))
print(f"{len(plan['pending'])} pending (model, set) cells")
for cmd in plan["commands"]:
    print("  " + " ".join(cmd))
""",
    ),
    _md(
        7,
        """
## 4. Re-score every pending set for every model

Runs the commands printed above: `eval_multiturn ... --chunk` for the multi-turn sets and, if
any indirect set is pending, `eval_indirect --dataset ...` (its partial tables go to
`rescore_tmp/`; the published tables are rebuilt from the scores in §5). Each new score file
is stamped with the loader revision and a fingerprint of its rows, which is what clears the
*pending* state.
""",
    ),
    _code(
        8,
        """
for cmd in plan["commands"]:
    print("\\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
""",
    ),
    _md(
        9,
        """
## 5. Rebuild every table from the scores (no GPU) and verify

`rebuild_results_from_scores` refuses to run if any score files disagree about their rows.
`rescore_plan --check` fails if anything is still pending (e.g. a gated model you have no
access to) — fix access and re-run §4 rather than publishing a partial table.
""",
    ),
    _code(
        10,
        """
!python -m scripts.rebuild_results_from_scores
!python -m scripts.analyze_operating_points
!python -m scripts.analyze_operating_points --scores-dir results/scores_indirect --within-set --label indirect
!python -m scripts.analyze_multiturn > /dev/null && echo "multiturn tables rebuilt"
!python -m scripts.plot_operating_points && python -m scripts.plot_multiturn
!python -m scripts.rescore_plan --check && echo "nothing pending"
""",
    ),
    _md(
        11,
        """
## 6. Take the results home

Download the archive, unpack it over the repo's `results/` on the `revision-2026-11` branch,
review `git diff --stat results/`, then update the numbers quoted in `README.md` and
`results/FINDINGS.md` (the multi-turn section) and commit. The pytest suite checks that every
committed score file aligns.
""",
    ),
    _code(
        12,
        """
!zip -qr results_revision_2026_11.zip results
from google.colab import files

files.download("results_revision_2026_11.zip")
""",
    ),
]


def build() -> dict:
    return {
        "cells": CELLS,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n")
    print(f"✓ wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
