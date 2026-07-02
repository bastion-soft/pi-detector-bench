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
# Each model is scored at its OWN context window (auto-detected from the model
# config, or a per-model override in models.yaml) — not a global cap — so a
# long-context detector isn't silently truncated to a short window.


def main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    keys = args.dataset or DEFAULT_DATASETS
    sets: list[tuple[str, object, list]] = []
    missing: list[str] = []  # requested sets that came back empty / failed to load
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
            missing.append(key)
            continue
        if not eval_set.texts:
            logger.warning("skip %s — empty (unavailable / gated / not installed)", key)
            missing.append(key)
            continue
        sets.append((key, eval_set, meta))

    # No silent shrinkage: a requested set coming back empty (missing dep, gated
    # without a token, schema drift) would quietly reduce the eval — e.g. agentdojo
    # vanishing from cross-step. Fail loudly unless the caller opts into partial.
    if missing and not args.allow_missing:
        logger.error(
            "MISSING sets: %s — refusing a partial run. Install deps (e.g. `pip install "
            "agentdojo`) / accept gated terms + set HF_TOKEN, or pass --allow-missing "
            "to score only what's available.",
            ", ".join(missing),
        )
        return 1
    if not sets:
        logger.error("no multi-turn sets loaded")
        return 1

    dump_dir = args.dump_scores
    summary: list[dict] = []
    for spec in load_models():
        logger.info("=" * 60)
        logger.info("loading %s (%s)", spec.name, spec.hf_id)
        # per-model window: explicit models.yaml override, else CLI --max-length,
        # else None -> the runner auto-detects from config.max_position_embeddings.
        window = spec.max_length if spec.max_length is not None else args.max_length
        try:
            runner = TransformersRunner(
                model_id=spec.hf_id,
                attack_label_id=spec.attack_label,
                max_length=window,
                batch_size=args.batch_size,
                name=spec.name,
                truncation_side="left",  # keep the most recent turns (deployment-faithful)
            )
        except Exception as exc:
            level = "commercial/gated — need a license + token" if spec.gated else str(exc)
            logger.warning("skip %s (%s)", spec.name, level)
            continue

        # the model's resolved window, recorded per row for the length analysis
        model_window = int(runner.max_length)
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
        default=None,
        help="force a fixed token window for every model; default None = each model's "
        "own window (config.max_position_embeddings, or its models.yaml override)",
    )
    p.add_argument(
        "--dump-scores",
        default="results/scores_multiturn",
        metavar="DIR",
        help="write raw per-conversation scores+labels+meta per (model,set) for offline analysis",
    )
    p.add_argument(
        "--allow-missing",
        action="store_true",
        help="score only the sets that load instead of erroring when a requested set "
        "is empty (missing dep / gated without token). Off by default so a partial "
        "run can't silently pass as complete.",
    )
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
