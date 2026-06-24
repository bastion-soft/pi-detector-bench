"""Score every detector in ``models.yaml`` on the held-out adversarial benchmarks.

Produces the detection leaderboard (AUC / F1 / latency). Every model is scored
the same generic way (a plain HF classifier) — there are no special paths.

Usage (a free Colab T4 is enough — total wall-clock ~5-10 min):

    # 1. Install + auth (only gated entries like Meta Prompt-Guard need a token)
    pip install -e .
    huggingface-cli login

    # 2. Run
    python -m scripts.run_leaderboard

    # 3. Outputs
    #    results/leaderboard.json   — raw rows
    #    results/leaderboard.md     — markdown table
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import time
from pathlib import Path

from pidbench.benchmark_suite import SuiteRow, _run
from pidbench.data import BENCHMARK_LOADERS
from pidbench.models import load_models
from pidbench.runners import TransformersRunner

logger = logging.getLogger(__name__)


BENCHMARK_DISPLAY = {
    "rogue": "rogue (5k)",
    "jailbreakbench": "JBB (200)",
    "xtram1_test": "xTRam1 test (2k)",
    "slabs_test": "S-Labs test (2k)",
    "deepset_test": "deepset test (116)",
}


DEFAULT_BENCHMARKS = ["rogue", "jailbreakbench", "xtram1_test", "slabs_test"]


def main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Load benchmarks once, reuse across runners. Track (key, EvalSet) so we
    # can key the output table off the registry key, not EvalSet.name.
    bench_keys = args.benchmark or DEFAULT_BENCHMARKS
    bench_pairs: list[tuple[str, object]] = []
    name_to_key: dict[str, str] = {}
    for key in bench_keys:
        try:
            eval_set = BENCHMARK_LOADERS[key](limit=args.limit)
        except Exception as exc:
            logger.warning("could not load benchmark %s: %s", key, exc)
            continue
        bench_pairs.append((key, eval_set))
        name_to_key[eval_set.name] = key
    if not bench_pairs:
        logger.error("no benchmarks loaded")
        return 1

    rows: list[tuple[str, SuiteRow]] = []  # (bench_key, row)
    for spec in load_models():
        display, model_id, attack_label = spec.name, spec.hf_id, spec.attack_label
        logger.info("=" * 60)
        logger.info("loading %s (%s)", display, model_id)
        try:
            runner = TransformersRunner(
                model_id=model_id,
                attack_label_id=attack_label,
                max_length=512,
                batch_size=args.batch_size,
                name=display,
            )
        except Exception as exc:
            if spec.gated:
                logger.warning(
                    "skip %s — gated model. Accept its terms on the HF model page and "
                    "`huggingface-cli login` with a token that has access. (%s)",
                    display,
                    exc,
                )
            else:
                logger.warning("skip %s: %s", display, exc)
            continue
        for key, bench in bench_pairs:
            try:
                rows.append(
                    (key, _run(runner, bench, threshold=args.threshold, dump_dir=args.dump_scores))
                )
            except Exception as exc:
                logger.warning("%s on %s failed: %s", display, bench.name, exc)

    if not rows:
        logger.error("no rows produced")
        return 1

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    bench_order = [k for k, _ in bench_pairs]

    json_path = out_dir / "leaderboard.json"
    _write_json(rows, json_path)
    logger.info("wrote %s", json_path)

    md_path = out_dir / "leaderboard.md"
    md_path.write_text(_format_markdown(rows, bench_order))
    logger.info("wrote %s", md_path)
    print("\n" + md_path.read_text())
    return 0


def _format_markdown(rows: list[tuple[str, SuiteRow]], bench_order: list[str]) -> str:
    by_runner: dict[str, dict[str, SuiteRow]] = {}
    for key, r in rows:
        by_runner.setdefault(r.runner, {})[key] = r

    # Rank models by average AUC (descending), applied consistently to every
    # table so the same model order reads down the AUC, F1 and latency tables.
    def _avg_auc(by_bench: dict[str, SuiteRow]) -> float:
        vals = [row.auc for row in by_bench.values()]
        return statistics.mean(vals) if vals else 0.0

    order = sorted(by_runner, key=lambda name: _avg_auc(by_runner[name]), reverse=True)

    headers = [BENCHMARK_DISPLAY.get(k, k) for k in bench_order]

    lines: list[str] = []
    lines.append("## Leaderboard — AUC")
    lines.append("")
    lines.append("| Model | " + " | ".join(headers) + " | **Avg** |")
    lines.append("|" + "---|" * (len(headers) + 2))
    for runner in order:
        by_bench = by_runner[runner]
        values, aucs = [], []
        for key in bench_order:
            row = by_bench.get(key)
            if row is None:
                values.append("—")
            else:
                values.append(f"{row.auc:.3f}")
                aucs.append(row.auc)
        avg = f"**{statistics.mean(aucs):.3f}**" if aucs else "—"
        lines.append(f"| {runner} | " + " | ".join(values) + f" | {avg} |")

    lines.append("")
    lines.append("## Leaderboard — F1 @ threshold=0.5")
    lines.append("")
    lines.append("| Model | " + " | ".join(headers) + " | **Avg** |")
    lines.append("|" + "---|" * (len(headers) + 2))
    for runner in order:
        by_bench = by_runner[runner]
        values, f1s = [], []
        for key in bench_order:
            row = by_bench.get(key)
            if row is None:
                values.append("—")
            else:
                values.append(f"{row.f1:.3f}")
                f1s.append(row.f1)
        avg = f"**{statistics.mean(f1s):.3f}**" if f1s else "—"
        lines.append(f"| {runner} | " + " | ".join(values) + f" | {avg} |")

    lines.append("")
    lines.append("## Latency (p50 ms / sample, batched inference)")
    lines.append("")
    lines.append("| Model | " + " | ".join(headers) + " |")
    lines.append("|" + "---|" * (len(headers) + 1))
    for runner in order:
        by_bench = by_runner[runner]
        values = []
        for key in bench_order:
            row = by_bench.get(key)
            values.append(f"{row.p50_latency_ms:.1f}" if row else "—")
        lines.append(f"| {runner} | " + " | ".join(values) + " |")

    lines.append("")
    lines.append(
        f"_Generated {time.strftime('%Y-%m-%d')} via `python -m scripts.run_leaderboard`._"
    )
    return "\n".join(lines) + "\n"


def _write_json(rows: list[tuple[str, SuiteRow]], path: Path) -> None:
    from dataclasses import asdict

    payload = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": [{"benchmark_key": key, **asdict(r)} for key, r in rows],
    }
    path.write_text(json.dumps(payload, indent=2))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.run_leaderboard")
    p.add_argument(
        "--benchmark",
        action="append",
        default=[],
        help="benchmark(s) to run; repeat for multiple. Default: DEFAULT_BENCHMARKS.",
    )
    p.add_argument(
        "--limit", type=int, default=None, help="cap samples per benchmark (smoke testing)"
    )
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--output-dir", default="results")
    p.add_argument(
        "--dump-scores",
        default=None,
        metavar="DIR",
        help="also write raw per-prompt scores+labels per (model, benchmark) to DIR "
        "(e.g. results/scores) for offline operating-point analysis.",
    )
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
