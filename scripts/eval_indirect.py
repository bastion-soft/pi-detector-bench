"""Indirect / structured prompt-injection leaderboard — scored pure-model.

Scores every detector in ``models.yaml`` on the held-out indirect / structured
sets in ``pidbench/indirect_data.py`` (Z-Edgar, BIPIA, InjecAgent, AgentDojo,
HackAPrompt, TensorTrust), the same generic way as the direct leaderboard.
Written to a SEPARATE ``results/indirect.json`` — these target structured/indirect
injection, a distinct capability, so they are NOT folded into the main 4-benchmark
average.

    python -m scripts.eval_indirect
    python -m scripts.eval_indirect --dataset zedgar --dataset agentdojo   # subset
    python -m scripts.eval_indirect --limit 200                            # smoke run
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
from pidbench.indirect_data import INDIRECT_LOADERS
from pidbench.models import load_models
from pidbench.runners import TransformersRunner

logger = logging.getLogger(__name__)

# benchmark_key -> column label
_DISPLAY = {
    "zedgar": "Z-Edgar",
    "bipia": "BIPIA",
    "injecagent": "InjecAgent",
    "agentdojo": "AgentDojo",
    "hackaprompt": "HackAPrompt",
    "tensortrust": "TensorTrust",
}
# Pooled keys (per-category splits like bipia_email exist in INDIRECT_LOADERS for
# manual drill-down but aren't in the default published table).
DEFAULT_DATASETS = ["zedgar", "bipia", "injecagent", "agentdojo", "hackaprompt", "tensortrust"]


def main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    keys = args.dataset or DEFAULT_DATASETS
    bench_pairs: list[tuple[str, object]] = []
    for key in keys:
        loader = INDIRECT_LOADERS.get(key)
        if loader is None:
            logger.warning("unknown indirect set %s (known: %s)", key, ", ".join(INDIRECT_LOADERS))
            continue
        try:
            eval_set = loader(limit=args.limit)
        except Exception as exc:
            logger.warning("could not load %s: %s", key, exc)
            continue
        if not eval_set.texts:
            logger.warning("skip %s — empty (data unavailable / gated / not installed)", key)
            continue
        bench_pairs.append((key, eval_set))
    if not bench_pairs:
        logger.error("no indirect sets loaded")
        return 1

    rows: list[tuple[str, SuiteRow]] = []
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
                    "skip %s — commercial/gated (need a license + granted token). %s", display, exc
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

    (out_dir / "indirect.json").write_text(_write_json(rows))
    logger.info("wrote %s", out_dir / "indirect.json")
    md_path = out_dir / "indirect.md"
    md_path.write_text(_format_markdown(rows, bench_order))
    logger.info("wrote %s", md_path)
    print("\n" + md_path.read_text())
    return 0


def _format_markdown(rows: list[tuple[str, SuiteRow]], bench_order: list[str]) -> str:
    by_runner: dict[str, dict[str, SuiteRow]] = {}
    for key, r in rows:
        by_runner.setdefault(r.runner, {})[key] = r

    def _avg(by_bench: dict[str, SuiteRow], metric: str) -> float:
        vals = [getattr(row, metric) for row in by_bench.values()]
        return statistics.mean(vals) if vals else 0.0

    order = sorted(by_runner, key=lambda n: _avg(by_runner[n], "auc"), reverse=True)
    headers = [_DISPLAY.get(k, k) for k in bench_order]

    def _table(metric: str, title: str) -> list[str]:
        out = [f"## Indirect / structured injection — {title}", ""]
        out.append("| Model | " + " | ".join(headers) + " | **Avg** |")
        out.append("|" + "---|" * (len(headers) + 2))
        for runner in order:
            bb = by_runner[runner]
            vals, present = [], []
            for k in bench_order:
                row = bb.get(k)
                if row is None:
                    vals.append("—")
                else:
                    v = getattr(row, metric)
                    vals.append(f"{v:.3f}")
                    present.append(v)
            avg = f"**{statistics.mean(present):.3f}**" if present else "—"
            out.append(f"| {runner} | " + " | ".join(vals) + f" | {avg} |")
        out.append("")
        return out

    lines: list[str] = []
    lines += _table("auc", "AUC")
    lines += _table("f1", "F1 @ threshold=0.5")
    lines.append(
        "Held-out indirect/structured sets, scored pure-model. Reported "
        "separately from the direct leaderboard — competitors target plain-prose "
        "injection, so this is a distinct capability axis, not folded into the "
        "main average."
    )
    lines.append("")
    lines.append(f"_Generated {time.strftime('%Y-%m-%d')} via `python -m scripts.eval_indirect`._")
    return "\n".join(lines) + "\n"


def _write_json(rows: list[tuple[str, SuiteRow]]) -> str:
    from dataclasses import asdict

    payload = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": [{"benchmark_key": key, **asdict(r)} for key, r in rows],
    }
    return json.dumps(payload, indent=2)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.eval_indirect")
    p.add_argument(
        "--dataset",
        action="append",
        default=[],
        help="indirect set(s) to run; repeat. Default: the pooled set.",
    )
    p.add_argument("--limit", type=int, default=None, help="cap samples per set (smoke testing)")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--output-dir", default="results")
    p.add_argument(
        "--dump-scores",
        default=None,
        metavar="DIR",
        help="also write raw per-prompt scores+labels per (model, set) to DIR for offline "
        "within-set operating-point analysis. Use a SEPARATE dir from the direct leaderboard "
        "(e.g. results/scores_indirect) so indirect sets aren't pooled with direct attacks.",
    )
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
