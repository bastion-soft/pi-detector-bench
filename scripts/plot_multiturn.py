"""Render the multi-turn / cross-step plots from ``results/multiturn.json`` (no GPU).

One figure per family: **detection rate vs the axis that varies for it** —
injection *depth* for cross-step (how far the poison is buried from the end),
conversation *length* for jailbreak (innocent buildup before the payload). A
curve that stays flat = the model's window reaches the poison; a cliff = it
falls out of view. Agent-jailbreak is single-turn, so it has no stratified plot.

Reads the ``stratified`` block written by ``scripts.analyze_multiturn``;
matplotlib is an optional plotting-only dependency.

    python -m scripts.plot_multiturn
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FAMILY_TITLE = {
    "jailbreak": "Multi-turn jailbreak",
    "cross_step": "Cross-step agent injection",
    "agent_jailbreak": "Agent-jailbreak by user",
}
AXIS_LABEL = {
    "depth": "Injection depth — context after the poison (→ deeper / older)",
    "length": "Conversation length (→ longer)",
}
AXIS_TITLE = {
    "depth": "Detection vs injection depth — flat = window reaches the poison",
    "length": "Detection vs conversation length — flat = signal survives dilution",
}


def main() -> int:
    args = _parse_args()
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(
            "matplotlib not installed — `pip install matplotlib` to render plots", file=sys.stderr
        )
        return 1

    data = json.loads(Path(args.multiturn_json).read_text())
    families = data.get("families", {})
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for fam, block in families.items():
        strat = block.get("stratified")
        if not strat or not strat.get("buckets"):
            continue  # e.g. agent-jailbreak (single-turn, nothing to stratify)
        axis = strat.get("axis", "length")
        buckets = strat["buckets"]
        recall = strat["recall"]
        # headline (AUC-sorted) model order if present
        order = [r["model"] for r in block.get("headline", [])] or list(recall)
        models = [m for m in order if m in recall]

        fig, ax = plt.subplots(figsize=(9, 5.5))
        xs = range(len(buckets))
        for m in models:
            ys = [recall[m].get(b) for b in buckets]
            gx = [i for i, y in enumerate(ys) if y is not None]
            gy = [y for y in ys if y is not None]
            if gx:
                ax.plot(gx, gy, marker="o", linewidth=1.8, alpha=0.9, label=m)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(buckets, rotation=20, ha="right", fontsize=8)
        ax.set_ylim(0, 1)
        ax.set_xlabel(AXIS_LABEL.get(axis, axis))
        ax.set_ylabel("Detection rate (recall @0.5)")
        ax.set_title(AXIS_TITLE.get(axis, ""))
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7, loc="lower left")
        fig.suptitle(f"{FAMILY_TITLE.get(fam, fam)} — multi-turn detection", fontsize=13)
        fig.tight_layout()
        p = out_dir / f"multiturn_{fam}.svg"
        fig.savefig(p)
        fig.savefig(p.with_suffix(".png"), dpi=130)  # PNG renders inline on GitHub
        plt.close(fig)
        written.append(p)

    if not written:
        print(
            "no stratified data in multiturn.json — run scripts.eval_multiturn + "
            "scripts.analyze_multiturn first",
            file=sys.stderr,
        )
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
