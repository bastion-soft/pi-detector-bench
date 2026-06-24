"""Core scoring: run one detector on one benchmark → a metrics row.

`_run` is the shared primitive used by every scoring script (`run_leaderboard`,
`eval_indirect`). It scores a detector on a labelled set, optionally dumps the
raw per-prompt scores (so all downstream metrics are reproducible offline), and
returns a `SuiteRow` of standard binary-classification metrics.
"""

from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pidbench.data import EvalSet
from pidbench.metrics import binary_metrics
from pidbench.runners import Runner, RunnerOutput

logger = logging.getLogger(__name__)


@dataclass
class SuiteRow:
    runner: str
    benchmark: str
    n_samples: int
    n_attack: int
    n_benign: int
    auc: float
    f1: float
    precision: float
    recall: float
    fpr_at_tpr_99: float
    fpr_at_tpr_95: float
    p50_latency_ms: float
    p95_latency_ms: float
    total_seconds: float


def _run(
    runner: Runner,
    bench: EvalSet,
    threshold: float,
    dump_dir: str | Path | None = None,
) -> SuiteRow:
    logger.info(
        "running %s on %s (n=%d, attack=%d, benign=%d)",
        runner.name,
        bench.name,
        len(bench),
        bench.n_attack,
        bench.n_benign,
    )
    t0 = time.perf_counter()
    output: RunnerOutput = runner.score_batch(bench.texts)
    total = time.perf_counter() - t0

    scores = np.asarray(output.scores, dtype=float)
    labels = np.asarray(bench.labels, dtype=int)

    if dump_dir is not None:
        from pidbench.scores_io import dump_scores

        dump_scores(dump_dir, runner.name, bench.name, "attack", output.scores, bench.labels)

    metrics = binary_metrics(scores, labels, threshold=threshold)

    p50 = statistics.median(output.latencies_ms) if output.latencies_ms else 0.0
    p95 = (
        statistics.quantiles(output.latencies_ms, n=20)[-1]
        if len(output.latencies_ms) >= 20
        else max(output.latencies_ms, default=0.0)
    )

    return SuiteRow(
        runner=runner.name,
        benchmark=bench.name,
        n_samples=len(bench),
        n_attack=bench.n_attack,
        n_benign=bench.n_benign,
        auc=metrics.auc,
        f1=metrics.f1,
        precision=metrics.precision,
        recall=metrics.recall,
        fpr_at_tpr_99=metrics.fpr_at_tpr_99,
        fpr_at_tpr_95=metrics.fpr_at_tpr_95,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        total_seconds=total,
    )
