"""Render the multi-turn / cross-step plots from ``results/multiturn.json`` (no GPU).

One figure per family, two panels each:
  * **Detection rate vs conversation length** — the truncation cliff. A detector
    whose recall falls off as conversations grow past its context window can't
    see the poison; a wide-window detector stays flat. This is the headline
    visual for the "does the window reach the payload" question.
  * **Detection rate by injection position** (early vs late turn) — whether the
    detector catches a payload planted early in a long conversation (the
    cross-step case) as well as a late one.

Reads the stratified block written by ``scripts.analyze_multiturn``; matplotlib
is an optional plotting-only dependency.

    python -m scripts.plot_multiturn
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# canonical order (must match analyze_multiturn.LEN_BUCKETS)
LEN_ORDER = ["≤256tok", "256–512tok", "512–1k tok", ">1k tok"]
POS_ORDER = ["early", "late"]
FAMILY_TITLE = {
    "jailbreak": "Multi-turn jailbreak",
    "cross_step": "Cross-step agent injection",
    "agent_jailbreak": "Agent-jailbreak by user",
}


def main() -> int:
    args = _parse_args()
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed — `pip install matplotlib` to render plots", file=sys.stderr)
        return 1

    data = json.loads(Path(args.multiturn_json).read_text())
    families = data.get("families", {})
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for fam, block in families.items():
        strat = block.get("stratified")
        if not strat:
            continue
        # preserve the headline (AUC-sorted) model order if present
        order = [r["model"] for r in block.get("headline", [])] or list(strat)
        models = [m for m in order if m in strat]

        fig, (ax_len, ax_pos) = plt.subplots(1, 2, figsize=(12, 5))

        # panel 1: recall vs length bucket
        len_labels = [b for b in LEN_ORDER if any(f"len:{b}" in strat[m] for m in models)]
        for m in models:
            ys = [strat[m].get(f"len:{b}") for b in len_labels]
            xs = [i for i, y in enumerate(ys) if y is not None]
            yv = [y for y in ys if y is not None]
            if xs:
                ax_len.plot(xs, yv, marker="o", linewidth=1.8, alpha=0.9, label=m)
        ax_len.set_xticks(range(len(len_labels)))
        ax_len.set_xticklabels(len_labels, rotation=20, ha="right", fontsize=8)
        ax_len.set_ylim(0, 1)
        ax_len.set_ylabel("Detection rate (recall @0.5)")
        ax_len.set_xlabel("Conversation length (→ longer)")
        ax_len.set_title("Detection vs length — flat = window reaches the payload")
        ax_len.grid(True, alpha=0.25)
        ax_len.legend(fontsize=7, loc="lower left")

        # panel 2: recall by injection position (grouped bars)
        pos_labels = [p for p in POS_ORDER if any(f"pos:{p}" in strat[m] for m in models)]
        n = max(len(models), 1)
        width = 0.8 / n
        for i, m in enumerate(models):
            vals = [strat[m].get(f"pos:{p}") or 0 for p in pos_labels]
            xs = [j + i * width for j in range(len(pos_labels))]
            ax_pos.bar(xs, vals, width=width, alpha=0.9, label=m)
        ax_pos.set_xticks([j + (n - 1) * width / 2 for j in range(len(pos_labels))])
        ax_pos.set_xticklabels([f"{p} injection" for p in pos_labels], fontsize=9)
        ax_pos.set_ylim(0, 1)
        ax_pos.set_ylabel("Detection rate (recall @0.5)")
        ax_pos.set_title("Detection by injection position")
        ax_pos.grid(True, alpha=0.25, axis="y")
        ax_pos.legend(fontsize=7, loc="lower left")

        fig.suptitle(f"{FAMILY_TITLE.get(fam, fam)} — multi-turn detection", fontsize=13)
        fig.tight_layout()
        p = out_dir / f"multiturn_{fam}.svg"
        fig.savefig(p)
        fig.savefig(p.with_suffix(".png"), dpi=130)  # PNG renders inline on GitHub
        plt.close(fig)
        written.append(p)

    if not written:
        print("no stratified data in multiturn.json — run scripts.eval_multiturn + "
              "scripts.analyze_multiturn first", file=sys.stderr)
        return 1
    for p in written:
        print(f"✓ wrote {p} (+ .png)")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.plot_multiturn")
    p.add_argument("--multiturn-json", default="results/multiturn.json")
    p.add_argument("--output-dir", default="results")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
