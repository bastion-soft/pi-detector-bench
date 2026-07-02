"""Multi-turn / cross-step prompt-injection scoring — pure-model.

Scores every detector in ``models.yaml`` on the multi-turn sets in
``pidbench/multiturn_data.py`` (InjecAgent-enhanced, AgentDojo, CoSafe, MHJ,
AgentHarm) the same generic way as the other leaderboards, and dumps raw
per-conversation scores + labels + **meta** (length, injection position,
family) to ``results/scores_multiturn/``. The stratified tables are then built
offline with no GPU by ``scripts.analyze_multiturn``.

Key rule (see METHODOLOGY): conversations are scored at their NATURAL length —
each model truncates to its own ``max_length``. We record each model's window so
the analysis can show the truncation cliff rather than hide it.

    python -m scripts.eval_multiturn --dump-scores results/scores_multiturn
    python -m scripts.eval_multiturn --dataset cosafe --dataset agentdojo --limit 100
"""

from __future__ import annotations

import argparse
import logging
import sys

import numpy as np

from pidbench.metrics import binary_metrics
from pidbench.models import load_models
from pidbench.multiturn_data import MULTITURN_LOADERS_MT
from pidbench.runners import TransformersRunner
from pidbench.scores_io import dump_scores

logger = logging.getLogger(__name__)

DEFAULT_DATASETS = ["injecagent", "agentdojo", "asb", "cosafe", "mhj", "agentharm"]
# Each model scores conversations truncated to ITS OWN window — recorded per row.
MODEL_MAX_LENGTH = 512  # upper bound we pass to the tokenizer; model truncates within


def main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    keys = args.dataset or DEFAULT_DATASETS
    sets: list[tuple[str, object, list]] = []
    for key in keys:
        loader = MULTITURN_LOADERS_MT.get(key)
        if loader is None:
            logger.warning(
                "unknown multi-turn set %s (known: %s)", key, ", ".join(MULTITURN_LOADERS_MT)
            )
            continue
        try:
            eval_set, meta = loader(limit=args.limit)
        except Exception as exc:
            logger.warning("could not load %s: %s", key, exc)
            continue
        if not eval_set.texts:
            logger.warning("skip %s — empty (unavailable / gated / not installed)", key)
            continue
        sets.append((key, eval_set, meta))
    if not sets:
        logger.error("no multi-turn sets loaded")
        return 1

    dump_dir = args.dump_scores
    summary: list[dict] = []
    for spec in load_models():
        logger.info("=" * 60)
        logger.info("loading %s (%s)", spec.name, spec.hf_id)
        try:
            runner = TransformersRunner(
                model_id=spec.hf_id,
                attack_label_id=spec.attack_label,
                max_length=args.max_length,
                batch_size=args.batch_size,
                name=spec.name,
            )
        except Exception as exc:
            level = "commercial/gated — need a license + token" if spec.gated else str(exc)
            logger.warning("skip %s (%s)", spec.name, level)
            continue

        # each model's actual window, for the truncation-cliff column
        model_window = int(getattr(runner, "max_length", args.max_length))
        for key, eval_set, meta in sets:
            try:
                out = runner.score_batch(list(eval_set.texts))
            except Exception as exc:
                logger.warning("%s on %s failed: %s", spec.name, key, exc)
                continue
            scores = np.asarray(out.scores, dtype=float)
            labels = np.asarray(eval_set.labels, dtype=int)
            # tag each row with the scoring model's window for offline analysis
            meta_out = [{**m.as_dict(), "model_max_length": model_window} for m in meta]
            if dump_dir:
                dump_scores(
                    dump_dir, spec.name, eval_set.name, "attack", scores, labels, meta=meta_out
                )
            m = binary_metrics(scores, labels, threshold=args.threshold)
            summary.append(
                {
                    "model": spec.name,
                    "dataset": key,
                    "family": meta[0].family if meta else "?",
                    "n": len(labels),
                    "auc": round(m.auc, 4),
                    "f1": round(m.f1, 4),
                    "fpr_at_95": round(m.fpr_at_tpr_95, 4),
                    "model_max_length": model_window,
                }
            )
            logger.info(
                "  %-12s %-11s n=%-4d AUC=%.3f F1=%.3f FPR@95=%.3f",
                spec.name[:12],
                key,
                len(labels),
                m.auc,
                m.f1,
                m.fpr_at_tpr_95,
            )

    if not summary:
        logger.error("no rows produced (all models skipped?)")
        return 1
    if dump_dir:
        logger.info("\n✓ raw scores + meta dumped to %s", dump_dir)
        logger.info("  build the stratified tables with: python -m scripts.analyze_multiturn")
    else:
        logger.info("\n(no --dump-scores — pass a dir to enable the offline stratified analysis)")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.eval_multiturn")
    p.add_argument("--dataset", action="append", default=[], help="multi-turn set(s); repeat.")
    p.add_argument("--limit", type=int, default=None, help="cap rows per set (smoke testing)")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument(
        "--max-length",
        type=int,
        default=MODEL_MAX_LENGTH,
        help="upper token bound passed to the tokenizer; each model truncates within it",
    )
    p.add_argument(
        "--dump-scores",
        default="results/scores_multiturn",
        metavar="DIR",
        help="write raw per-conversation scores+labels+meta per (model,set) for offline analysis",
    )
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
