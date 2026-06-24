"""Threshold-agnostic operating-point analysis from dumped scores.

Reads the per-prompt scores written by ``run_leaderboard --dump-scores`` (attack
sets, labelled) and ``measure_false_positives --dump-scores`` (real benign
traffic) and computes, per detector:

  * FPR at a fixed detection rate (TPR=0.95 / 0.99) on **real benign traffic** —
    the apples-to-apples comparison that doesn't depend on where anyone's 0.5
    falls: hold the catch rate constant, compare the false-alarm cost.
  * Equal-error rate (EER) and AUC (detection basis; AUC cross-checks the
    leaderboard).
  * A threshold sweep (FPR on real benign + recall on attacks) at chosen
    thresholds — free once scores are loaded.
  * A "deployment curve": TPR-on-attacks vs FPR-on-benign across thresholds,
    for plotting (the false-positive-axis companion to the detection ROC).

Two modes:
  * cross-benign (default): threshold picked from the pooled attack sets, FPR
    measured on the separate real-benign traffic (direct leaderboard).
  * --within-set: each labelled set is self-contained, FPR measured on the set's
    own benign half — for indirect/structured sets with matched injected-vs-benign
    pairs ("does it catch the injection without flagging benign structured data?").

No model inference — pure post-processing, reproducible offline from the
committed score files.

    python -m scripts.analyze_operating_points
    python -m scripts.analyze_operating_points --scores-dir results/scores_indirect \\
        --within-set --label indirect
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from pidbench.metrics import eer, fpr_at_threshold, threshold_at_tpr
from pidbench.scores_io import load_all_scores


def _pool(records: list[dict], runner: str, kind: str) -> tuple[np.ndarray, np.ndarray | None]:
    """Concatenate all (scores, labels) for one runner and kind."""
    scores: list[float] = []
    labels: list[int] = []
    have_labels = False
    for rec in records:
        if rec["runner"] != runner or rec["kind"] != kind:
            continue
        scores.extend(rec["scores"])
        if rec.get("labels") is not None:
            labels.extend(rec["labels"])
            have_labels = True
    s = np.asarray(scores, dtype=float)
    return s, (np.asarray(labels, dtype=int) if have_labels else None)


def _analyze_runner(
    attack_scores: np.ndarray,
    attack_labels: np.ndarray,
    benign_scores: np.ndarray,
    tprs: list[float],
    thresholds: list[float],
) -> dict:
    from sklearn.metrics import roc_auc_score  # type: ignore[import-not-found]

    pos = attack_scores[attack_labels == 1]  # attack-only scores → recall

    fpr_at_tpr = {}
    for tpr in tprs:
        t = threshold_at_tpr(attack_scores, attack_labels, tpr)
        fpr_at_tpr[f"{tpr:g}"] = {
            "threshold": round(t, 5),
            "fpr_benign": round(fpr_at_threshold(benign_scores, t), 5),
        }

    sweep = {}
    for thr in thresholds:
        sweep[f"{thr:g}"] = {
            "fpr_benign": round(fpr_at_threshold(benign_scores, thr), 5),
            "recall_attacks": round(float(np.mean(pos >= thr)) if pos.size else 0.0, 5),
        }

    eer_val, eer_t = eer(attack_scores, attack_labels)

    # Deployment curve: TPR(attacks) vs FPR(real benign) swept over thresholds.
    grid = np.linspace(0.0, 1.0, 201)
    curve = {
        "threshold": [round(float(t), 4) for t in grid],
        "tpr_attacks": [round(float(np.mean(pos >= t)) if pos.size else 0.0, 5) for t in grid],
        "fpr_benign": [round(float(np.mean(benign_scores >= t)), 5) for t in grid],
    }

    return {
        "auc": round(float(roc_auc_score(attack_labels, attack_scores)), 5),
        "eer": round(eer_val, 5),
        "eer_threshold": round(eer_t, 5),
        "n_attack": int((attack_labels == 1).sum()),
        "n_benign": int(benign_scores.size),
        "fpr_at_tpr": fpr_at_tpr,
        "threshold_sweep": sweep,
        "deployment_curve": curve,
    }


def _format_markdown(results: dict, tprs: list[float], thresholds: list[float]) -> str:
    rows = results["rows"]
    primary = f"{tprs[0]:g}"
    # Rank by FPR at the primary detection rate (lower = better), missing last.
    order = sorted(
        rows,
        key=lambda r: r["fpr_at_tpr"].get(primary, {}).get("fpr_benign", 1e9),
    )

    lines: list[str] = []
    lines.append("## Operating points — false positives at a fixed detection rate")
    lines.append("")
    lines.append(
        "Each detector's threshold is set to catch the same share of attacks; we then "
        "report how much **real benign traffic** (WildChat + LMSYS) it flags at that catch "
        "rate. This holds detection constant and shows the false-alarm cost, so the "
        "comparison does not depend on where any detector's 0.5 happens to fall."
    )
    lines.append("")
    tpr_cols = " | ".join(f"FPR @ {int(float(t) * 100)}% catch" for t in tprs)
    lines.append(f"| Detector | AUC | EER | {tpr_cols} |")
    lines.append("|" + "---|" * (len(tprs) + 3))
    for r in order:
        cells = [
            f"{r['fpr_at_tpr'].get(f'{t:g}', {}).get('fpr_benign', float('nan')) * 100:.2f}%"
            for t in tprs
        ]
        lines.append(
            f"| {r['runner']} | {r['auc']:.3f} | {r['eer'] * 100:.1f}% | "
            + " | ".join(cells)
            + " |"
        )

    lines.append("")
    lines.append("## Threshold sweep — FPR on real benign traffic (lower = better)")
    lines.append("")
    thr_cols = " | ".join(f"{t:g}" for t in thresholds)
    lines.append(f"| Detector | {thr_cols} |")
    lines.append("|" + "---|" * (len(thresholds) + 1))
    for r in order:
        cells = [
            f"{r['threshold_sweep'].get(f'{t:g}', {}).get('fpr_benign', float('nan')) * 100:.2f}%"
            for t in thresholds
        ]
        lines.append(f"| {r['runner']} | " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("## Threshold sweep — recall on attacks (higher = better)")
    lines.append("")
    lines.append(f"| Detector | {thr_cols} |")
    lines.append("|" + "---|" * (len(thresholds) + 1))
    for r in order:
        cells = [
            f"{r['threshold_sweep'].get(f'{t:g}', {}).get('recall_attacks', float('nan')) * 100:.1f}%"
            for t in thresholds
        ]
        lines.append(f"| {r['runner']} | " + " | ".join(cells) + " |")

    lines.append("")
    lines.append(
        f"_Generated {time.strftime('%Y-%m-%d')} via `python -m scripts.analyze_operating_points` "
        "from dumped per-prompt scores. No model inference; reproducible offline._"
    )
    return "\n".join(lines) + "\n"


def _format_markdown_within(results: dict, tprs: list[float], thresholds: list[float]) -> str:
    """Per-(detector, set) table for self-contained labelled sets (e.g. indirect).

    Here each set carries its own benign half (benign structured records), so
    'FPR at a fixed catch rate' is measured within the set: how much benign
    structured data is flagged when the detector is tuned to catch X% of that
    set's injections.
    """
    rows = results["rows"]
    primary = f"{tprs[0]:g}"
    datasets = sorted({r["dataset"] for r in rows})
    by_runner: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_runner.setdefault(r["runner"], {})[r["dataset"]] = r

    def _avg_fpr(runner: str) -> float:
        vals = [
            by_runner[runner][d]["fpr_at_tpr"].get(primary, {}).get("fpr_benign")
            for d in by_runner[runner]
        ]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else 1e9

    order = sorted(by_runner, key=_avg_fpr)
    pct = int(float(primary) * 100)

    lines: list[str] = []
    lines.append(f"## Indirect / structured — false positives at a fixed {pct}% catch rate")
    lines.append("")
    lines.append(
        "Each set is matched injected-vs-benign structured data. The threshold is set per "
        f"detector to catch {pct}% of that set's injections; the cell is the share of **benign "
        "structured records** wrongly flagged at that catch rate. Low = catches the injection "
        "without tripping on legitimate structured data. Threshold-agnostic (per-set tuned)."
    )
    lines.append("")
    lines.append("| Detector | " + " | ".join(datasets) + " | **Avg** |")
    lines.append("|" + "---|" * (len(datasets) + 2))
    for runner in order:
        cells, vals = [], []
        for d in datasets:
            r = by_runner[runner].get(d)
            v = r["fpr_at_tpr"].get(primary, {}).get("fpr_benign") if r else None
            cells.append(f"{v * 100:.2f}%" if v is not None else "—")
            if v is not None:
                vals.append(v)
        avg = f"**{sum(vals) / len(vals) * 100:.2f}%**" if vals else "—"
        lines.append(f"| {runner} | " + " | ".join(cells) + f" | {avg} |")

    lines.append("")
    lines.append("## Indirect / structured — summary (averaged across sets)")
    lines.append("")
    lines.append(f"| Detector | Avg AUC | Avg EER | Avg FPR @ {pct}% catch |")
    lines.append("|---|---|---|---|")
    for runner in order:
        rs = list(by_runner[runner].values())
        auc = sum(r["auc"] for r in rs) / len(rs)
        eer_avg = sum(r["eer"] for r in rs) / len(rs)
        lines.append(
            f"| {runner} | {auc:.3f} | {eer_avg * 100:.1f}% | {_avg_fpr(runner) * 100:.2f}% |"
        )

    lines.append("")
    lines.append(
        f"_Generated {time.strftime('%Y-%m-%d')} via "
        "`python -m scripts.analyze_operating_points --within-set` from dumped per-prompt scores. "
        "No model inference; reproducible offline._"
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = _parse_args()
    tprs = [float(x) for x in args.tprs.split(",") if x.strip()]
    thresholds = [float(x) for x in args.thresholds.split(",") if x.strip()]

    records = load_all_scores(args.scores_dir)
    if not records:
        print(
            f"no score files in {args.scores_dir} — run with --dump-scores first", file=sys.stderr
        )
        return 1

    rows = []
    curves = {}
    if args.within_set:
        # Each labelled set carries its own benign half (e.g. indirect/structured
        # sets are matched injected-vs-benign). One row per (detector, set);
        # FPR is measured within the set on its own benign records.
        for rec in records:
            if rec["kind"] != "attack" or rec.get("labels") is None:
                continue
            s = np.asarray(rec["scores"], dtype=float)
            label_arr = np.asarray(rec["labels"], dtype=int)
            if (label_arr == 1).sum() == 0 or (label_arr == 0).sum() == 0:
                print(
                    f"skip {rec['runner']} / {rec['dataset']}: needs both classes", file=sys.stderr
                )
                continue
            res = _analyze_runner(s, label_arr, s[label_arr == 0], tprs, thresholds)
            res["runner"] = rec["runner"]
            res["dataset"] = rec["dataset"]
            curves[f"{rec['runner']} · {rec['dataset']}"] = res.pop("deployment_curve")
            rows.append(res)
        formatter = _format_markdown_within
        empty_msg = "no labelled sets with both classes found"
    else:
        # Cross-benign: pool attack sets to pick the threshold, measure FPR on
        # the separate real-benign traffic.
        for runner in sorted({rec["runner"] for rec in records}):
            attack_scores, attack_labels = _pool(records, runner, "attack")
            benign_scores, _ = _pool(records, runner, "benign")
            if attack_labels is None or attack_scores.size == 0:
                print(f"skip {runner}: no labelled attack scores", file=sys.stderr)
                continue
            if benign_scores.size == 0:
                print(f"skip {runner}: no real-benign scores", file=sys.stderr)
                continue
            res = _analyze_runner(attack_scores, attack_labels, benign_scores, tprs, thresholds)
            res["runner"] = runner
            curves[runner] = res.pop("deployment_curve")
            rows.append(res)
        formatter = _format_markdown
        empty_msg = "no runner had both attack and benign scores"

    if not rows:
        print(empty_msg, file=sys.stderr)
        return 1

    label = args.label.strip()
    suffix = f"_{label}" if label else ""
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "within-set" if args.within_set else "cross-benign",
        "tprs": tprs,
        "thresholds": thresholds,
        "rows": rows,
    }
    (out_dir / f"operating_points{suffix}.json").write_text(json.dumps(results, indent=2))
    (out_dir / f"operating_points{suffix}.md").write_text(formatter(results, tprs, thresholds))
    (out_dir / f"det_points{suffix}.json").write_text(
        json.dumps(
            {"schema_version": 1, "generated_at": results["generated_at"], "curves": curves},
            indent=2,
        )
    )
    print(f"✓ wrote operating_points{suffix}.{{json,md}} and det_points{suffix}.json to {out_dir}")
    print("\n" + (out_dir / f"operating_points{suffix}.md").read_text())
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.analyze_operating_points")
    p.add_argument("--scores-dir", default="results/scores")
    p.add_argument("--output-dir", default="results")
    p.add_argument("--tprs", default="0.95,0.99", help="fixed detection rates (comma-separated)")
    p.add_argument(
        "--thresholds",
        default="0.2,0.45,0.5,0.55,0.8",
        help="sweep thresholds for the discrete table (comma-separated); "
        "the deployment curve always covers the full 0→1 range",
    )
    p.add_argument(
        "--within-set",
        action="store_true",
        help="treat each labelled set as self-contained (FPR measured on the set's own "
        "benign half) — for indirect/structured sets with matched injected-vs-benign pairs. "
        "Default off = cross-benign mode (threshold from attacks, FPR on real traffic).",
    )
    p.add_argument(
        "--label",
        default="",
        help="suffix for output filenames, e.g. --label indirect → operating_points_indirect.*",
    )
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
