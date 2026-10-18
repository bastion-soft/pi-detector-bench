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

After this, `leaderboard.{json,md}`, `indirect.{json,md}` and
`false_positives.{json,md}` (at 0.5 and at each model's declared threshold)
reproduce exactly from `scores/` and `scores_indirect/` with no GPU.

Alignment: score files are checked with ``scores_io.check_alignment`` first.
Files that disagree about their rows make the rebuild refuse (exit 2); files
that predate a loader change for their dataset are not used and their cells are
written as "pending re-score" until the set is re-scored (see
``notebooks/rescore_revision_2026_11.ipynb``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from pidbench.benchmark_suite import SuiteRow
from pidbench.data import BENCHMARK_LOADERS
from pidbench.indirect_data import INDIRECT_LOADERS
from pidbench.metrics import binary_metrics
from pidbench.models import declared_thresholds, threshold_for
from pidbench.scores_io import MisalignedScoresError, check_alignment, load_all_scores, slugify
from scripts import measure_false_positives as fp
from scripts.eval_indirect import _format_markdown as _ind_md
from scripts.eval_indirect import _write_json as _ind_json
from scripts.run_leaderboard import _format_markdown as _lb_md
from scripts.run_leaderboard import _write_json as _lb_json


def _score_map(scores_dir: str) -> tuple[dict, dict, list[dict]]:
    """Index the committed scores of one directory.

    Returns ``(attack, pending, benign)``: ``attack`` maps
    (slug(runner), slug(dataset)) -> record for labelled sets; ``pending`` maps the
    same key -> reason for files that predate a loader change for their dataset
    (never used, shown as "pending re-score"); ``benign`` lists benign-only records.
    Raises ``MisalignedScoresError`` (via ``check_alignment``) for files whose rows
    can't be shown to match — the rebuild refuses rather than mis-assigning scores.
    """
    usable, pending = check_alignment(load_all_scores(scores_dir))
    attack, benign = {}, []
    for r in usable:
        if r["kind"] == "attack" and r.get("labels") is not None:
            attack[(slugify(r["runner"]), slugify(r["dataset"]))] = r
        elif r["kind"] == "benign":
            benign.append(r)
    pend = {(slugify(run), slugify(ds)): why for (run, ds), why in pending.items()}
    return attack, pend, benign


def _rebuild_rows(
    json_path: Path, scores_dir: str, registered: set[str] | None = None
) -> tuple[list, list, int, int]:
    """Return (rows[(key, SuiteRow)], benchmark_key order, n_cells_changed, n_pending).

    ``registered`` (optional) is the set of benchmark keys the harness still
    loads; rows for any other key are dropped (a set removed from the benchmark
    leaves the published table, rather than lingering from an old run).
    """
    payload = json.loads(json_path.read_text())
    sm, pend, _ = _score_map(scores_dir)
    rows, order, changed, n_pending = [], [], 0, 0
    fields = SuiteRow.__dataclass_fields__
    for row in payload["rows"]:
        key = row["benchmark_key"]
        if registered is not None and key not in registered:
            continue
        if key not in order:
            order.append(key)
        cell = (slugify(row["runner"]), slugify(row["benchmark"]))
        rec = sm.get(cell)
        if rec is None and cell in pend:
            n_pending += 1
            print(f"  pending re-score: {row['runner']} / {key} — {pend[cell]}")
            blank = {k: None for k in fields}
            blank.update(runner=row["runner"], benchmark=row["benchmark"])
            blank["pending_rescore"] = pend[cell]
            rows.append((key, SuiteRow(**blank)))
            continue
        if rec is None:
            # No scores for this cell — keep the original row unchanged.
            print(f"  no scores for {row['runner']} / {key}; keeping reported values")
            rows.append((key, SuiteRow(**{k: row.get(k) for k in fields})))
            continue
        s = np.asarray(rec["scores"], dtype=float)
        labels = np.asarray(rec["labels"], dtype=int)
        m = binary_metrics(s, labels, threshold=0.5)
        if row.get("auc") is None or abs(m.auc - row["auc"]) > 1e-4:
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
                    p50_latency_ms=row.get("p50_latency_ms"),
                    p95_latency_ms=row.get("p95_latency_ms"),
                    total_seconds=row.get("total_seconds"),
                ),
            )
        )
    return rows, order, changed, n_pending


def _rebuild_false_positives(json_path: Path, scores_dir: str) -> int:
    """Recompute false_positives.{json,md} from the committed benign scores, at 0.5
    and at each model's declared threshold. Wall-clock times are kept from the
    original run (they can't be recomputed offline). Returns rows written."""
    old = json.loads(json_path.read_text()) if json_path.exists() else {"rows": []}
    walls = {(r["runner"], r["dataset"]): r.get("wall_seconds", 0.0) for r in old["rows"]}
    declared = declared_thresholds()
    _, _, benign = _score_map(scores_dir)
    order = [d for d in fp.DEFAULT_DATASETS if any(r["dataset"] == d for r in benign)]
    order += sorted({r["dataset"] for r in benign} - set(order))
    rows = [
        fp.fpr_row(
            r["runner"],
            r["dataset"],
            [float(x) for x in r["scores"]],
            walls.get((r["runner"], r["dataset"]), 0.0),
            threshold_for(r["runner"], declared),
        )
        for r in benign
    ]
    if not rows:
        return 0
    rows.sort(key=lambda x: (x.runner, order.index(x.dataset)))
    samples = {d: max(x.n_samples for x in rows if x.dataset == d) for d in order}
    json_path.write_text(json.dumps(fp.fp_payload(rows, samples, old.get("run")), indent=2))
    json_path.with_suffix(".md").write_text(fp._format_markdown(rows, order))
    return len(rows)


def main() -> int:
    args = _parse_args()
    results = Path(args.results_dir)

    targets = [
        ("leaderboard", results / "leaderboard.json", results / "leaderboard.md", args.scores_dir),
        ("indirect", results / "indirect.json", results / "indirect.md", args.scores_indirect_dir),
    ]
    any_done = False
    try:
        for name, json_path, md_path, scores_dir in targets:
            if not json_path.exists():
                print(f"skip {name}: {json_path} not found (run the scoring script first)")
                continue
            if not Path(scores_dir).exists():
                print(f"skip {name}: scores dir {scores_dir} not found (run with --dump-scores)")
                continue
            registered = set(BENCHMARK_LOADERS) if name == "leaderboard" else set(INDIRECT_LOADERS)
            run = json.loads(json_path.read_text()).get("run")
            rows, order, changed, n_pending = _rebuild_rows(json_path, scores_dir, registered)
            if name == "leaderboard":
                _lb_json(rows, json_path, run)
                md_path.write_text(_lb_md(rows, order))
            else:
                json_path.write_text(_ind_json(rows, run))
                md_path.write_text(_ind_md(rows, order))
            print(
                f"✓ {name}: rebuilt {len(rows)} rows from {scores_dir} "
                f"({changed} AUC cells changed, {n_pending} pending re-score)"
            )
            any_done = True

        fp_json = results / "false_positives.json"
        if Path(args.scores_dir).exists():
            n = _rebuild_false_positives(fp_json, args.scores_dir)
            if n:
                print(f"✓ false_positives: rebuilt {n} rows from {args.scores_dir}")
                any_done = True
    except MisalignedScoresError as exc:
        print(f"REFUSING to rebuild — misaligned score files: {exc}", file=sys.stderr)
        return 2

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
