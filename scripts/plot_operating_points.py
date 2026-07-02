"""Render operating-point curves from ``det_points.json`` (optional).

Two SVGs, both from the per-detector deployment curves produced by
``scripts.analyze_operating_points`` (no model inference):

  * ``operating_curve.svg`` — TPR on attacks vs FPR on **real benign traffic**,
    one line per detector. The decision-relevant, false-positive-axis companion
    to the detection ROC: how much benign you flag to reach a given catch rate.
  * ``fpr_vs_threshold.svg`` — FPR on real benign vs decision threshold, one
    line per detector. Shows which detectors are threshold-robust (flat) vs
    threshold-sensitive (steep).

matplotlib is intentionally NOT a core eval dependency; install it just for
plotting (``pip install matplotlib``).

    python -m scripts.plot_operating_points
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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

    data = json.loads(Path(args.det_points).read_text())
    curves = data["curves"]
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Stable ordering; every detector drawn the same way (no model singled out).
    names = sorted(curves)

    # Legend-only display overrides. The curve KEYS stay tied to the committed
    # scores/slugs; this just clarifies labels (e.g. flags the deprecated model).
    _LABELS = {"meta prompt-guard (86M)": "meta prompt-guard v1 (86M, deprecated)"}

    def _label(name: str) -> str:
        return _LABELS.get(name, name)

    def _style(name: str) -> dict:
        return {"linewidth": 1.6, "alpha": 0.9}

    # 1. Deployment curve: FPR (real benign) on x, TPR (attacks) on y.
    fig, ax = plt.subplots(figsize=(7, 5))
    for name in names:
        c = curves[name]
        ax.plot(c["fpr_benign"], c["tpr_attacks"], label=_label(name), **_style(name))
    ax.set_xlabel("False-positive rate on real benign traffic")
    ax.set_ylabel("Detection rate on attacks (TPR)")
    ax.set_title("Operating curve — catch rate vs false alarms on real traffic")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    p1 = out_dir / "operating_curve.svg"
    fig.savefig(p1)
    fig.savefig(p1.with_suffix(".png"), dpi=130)  # PNG renders inline on GitHub
    plt.close(fig)

    # 2. FPR vs threshold.
    fig, ax = plt.subplots(figsize=(7, 5))
    for name in names:
        c = curves[name]
        ax.plot(c["threshold"], c["fpr_benign"], label=_label(name), **_style(name))
    ax.set_xlabel("Decision threshold")
    ax.set_ylabel("False-positive rate on real benign traffic")
    ax.set_title("Threshold sensitivity — flat = robust, steep = brittle")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    p2 = out_dir / "fpr_vs_threshold.svg"
    fig.savefig(p2)
    fig.savefig(p2.with_suffix(".png"), dpi=130)  # PNG renders inline on GitHub
    plt.close(fig)

    print(f"✓ wrote {p1} (+ .png)\n✓ wrote {p2} (+ .png)")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.plot_operating_points")
    p.add_argument("--det-points", default="results/det_points.json")
    p.add_argument("--output-dir", default="results")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
