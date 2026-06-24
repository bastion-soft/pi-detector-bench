"""Rebuild the leaderboard + indirect tables from the committed per-prompt scores.

The torch-based competitor models are non-deterministic across GPU runs, so the
metrics a scoring run *reports* can drift slightly from run to run. To make the
published numbers exactly reproducible — and mutually consistent regardless of
how many times anything ran — this recomputes every threshold-derived metric
(AUC, F1, precision, recall, FPR@TPR) **from the dumped scores**, leaving only
the timing fields (latency) from the original run.

Run order (e.g. as the last Colab cell):

    python -m scripts.run_leaderboard         --dump-scores results/scores
    python -m scripts.measure_false_positives --dump-scores results/scores
    python -m scripts.eval_indirect           --dump-scores results/scores_indirect
    python -m scripts.rebuild_results_from_scores      # ← makes every table scores-derived

After this, `leaderboard.{json,md}` and `indirect.{json,md}` reproduce exactly
from `scores/` and `scores_indirect/` with no GPU. (`false_positives.json` is
already an exact function of the benign scores at threshold 0.5.)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from pidbench.benchmark_suite import SuiteRow
from pidbench.metrics import binary_metrics
from pidbench.scores_io import load_all_scores, slugify
from scripts.eval_indirect import _format_markdown as _ind_md
from scripts.eval_indirect import _write_json as _ind_json
from scripts.run_leaderboard import _format_markdown as _lb_md
from scripts.run_leaderboard import _write_json as _lb_json


def _score_map(scores_dir: str) -> dict:
    """(slug(runner), slug(dataset)) -> record, for labelled attack sets."""
    m = {}
    for r in load_all_scores(scores_dir):
        if r["kind"] == "attack" and r.get("labels") is not None:
            m[(slugify(r["runner"]), slugify(r["dataset"]))] = r
    return m


def _rebuild_rows(json_path: Path, scores_dir: str) -> tuple[list, list, int]:
    """Return (rows[(key, SuiteRow)], benchmark_key order, n_cells_changed)."""
    import json

    payload = json.loads(json_path.read_text())
    sm = _score_map(scores_dir)
    rows, order, changed = [], [], 0
    for row in payload["rows"]:
        key = row["benchmark_key"]
        if key not in order:
            order.append(key)
        rec = sm.get((slugify(row["runner"]), slugify(row["benchmark"])))
        if rec is None:
            # No scores for this cell — keep the original row unchanged.
            print(f"  no scores for {row['runner']} / {key}; keeping reported values")
            rows.append((key, SuiteRow(**{k: row[k] for k in SuiteRow.__dataclass_fields__})))
            continue
        s = np.asarray(rec["scores"], dtype=float)
        labels = np.asarray(rec["labels"], dtype=int)
        m = binary_metrics(s, labels, threshold=0.5)
        if abs(m.auc - row["auc"]) > 1e-4:
            changed += 1
        rows.append(
            (
                key,
                SuiteRow(
                    runner=row["runner"],
                    benchmark=row["benchmark"],
                    n_samples=int(labels.size),
                    n_attack=int((labels == 1).sum()),
                    n_benign=int((labels == 0).sum()),
                    auc=m.auc,
                    f1=m.f1,
                    precision=m.precision,
                    recall=m.recall,
                    fpr_at_tpr_99=m.fpr_at_tpr_99,
                    fpr_at_tpr_95=m.fpr_at_tpr_95,
                    p50_latency_ms=row["p50_latency_ms"],
                    p95_latency_ms=row["p95_latency_ms"],
                    total_seconds=row["total_seconds"],
                ),
            )
        )
    return rows, order, changed


def main() -> int:
    args = _parse_args()
    results = Path(args.results_dir)

    targets = [
        ("leaderboard", results / "leaderboard.json", results / "leaderboard.md", args.scores_dir),
        ("indirect", results / "indirect.json", results / "indirect.md", args.scores_indirect_dir),
    ]
    any_done = False
    for name, json_path, md_path, scores_dir in targets:
        if not json_path.exists():
            print(f"skip {name}: {json_path} not found (run the scoring script first)")
            continue
        if not Path(scores_dir).exists():
            print(f"skip {name}: scores dir {scores_dir} not found (run with --dump-scores first)")
            continue
        rows, order, changed = _rebuild_rows(json_path, scores_dir)
        if name == "leaderboard":
            _lb_json(rows, json_path)
            md_path.write_text(_lb_md(rows, order))
        else:
            json_path.write_text(_ind_json(rows))
            md_path.write_text(_ind_md(rows, order))
        print(f"✓ {name}: rebuilt {len(rows)} rows from {scores_dir} ({changed} AUC cells changed)")
        any_done = True

    if not any_done:
        print("nothing rebuilt — no (json, scores) pair found", file=sys.stderr)
        return 1
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.rebuild_results_from_scores")
    p.add_argument("--results-dir", default="results")
    p.add_argument("--scores-dir", default="results/scores")
    p.add_argument("--scores-indirect-dir", default="results/scores_indirect")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
