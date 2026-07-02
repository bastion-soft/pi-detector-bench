"""Dedup gate — the honesty backstop for the multi-turn eval.

Checks every rendered multi-turn eval conversation against the TRAINING corpus
and reports the overlap rate per set + family, so the never-trained claim is a
published number, not a promise. Rows at or above ``--near`` Jaccard are treated
as contaminated (effectively present in training) and written to a drop
manifest of fingerprints (hashes only — no text) that ``scripts.eval_multiturn``
consumes to exclude them before scoring.

Run once with corpus access (the corpus is private; the manifest is not):

    python -m scripts.dedup_multiturn \
        --corpus /path/to/bastion-training/data/corpus_v1.5.1_en/train.jsonl \
        --corpus /path/to/.../val.jsonl \
        --out results/multiturn_dedup.json

Then commit ``results/multiturn_dedup.json``; ``eval_multiturn --dedup-manifest
results/multiturn_dedup.json`` drops the flagged rows on every run, GPU or not.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from pidbench.dedup import CorpusIndex, fingerprint
from pidbench.multiturn_data import MULTITURN_LOADERS_MT

logger = logging.getLogger(__name__)


def main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.corpus:
        logger.error("pass --corpus <train.jsonl> (repeatable) — the training corpus to dedup against")
        return 1
    logger.info("building corpus index from %d file(s)…", len(args.corpus))
    idx = CorpusIndex.from_jsonl(args.corpus, df_max=args.df_max)
    logger.info("  corpus docs indexed: %d", len(idx))

    keys = args.dataset or list(MULTITURN_LOADERS_MT)
    manifest: dict = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "near_threshold": args.near,
        "fuzzy_threshold": args.fuzzy,
        "corpus_docs": len(idx),
        "sets": {},
        "dropped_fingerprints": [],
    }
    dropped: set[str] = set()

    logger.info("\n%-14s %-16s %6s %8s %8s   top src", "set", "family", "n", "near%", "fuzzy%")
    logger.info("-" * 70)
    for key in keys:
        loader = MULTITURN_LOADERS_MT.get(key)
        if loader is None:
            continue
        try:
            es, meta = loader(limit=args.limit)
        except Exception as exc:
            logger.warning("skip %s: %s", key, exc)
            continue
        if not es.texts:
            continue
        near = fuzzy = 0
        srcs: dict[str, int] = {}
        for text in es.texts:
            j, i = idx.best_match(text)
            if j >= args.fuzzy:
                fuzzy += 1
            if j >= args.near:
                near += 1
                dropped.add(fingerprint(text))
                s = idx.source_of(i)
                srcs[s] = srcs.get(s, 0) + 1
        n = len(es.texts)
        fam = meta[0].family if meta else "?"
        top = max(srcs, key=srcs.get) if srcs else "—"
        logger.info("%-14s %-16s %6d %7.2f%% %7.2f%%   %s",
                    key, fam, n, 100 * near / n, 100 * fuzzy / n, top)
        manifest["sets"][key] = {
            "family": fam, "n": n, "near": near, "fuzzy": fuzzy,
            "near_pct": round(100 * near / n, 3), "top_corpus_source": top,
        }

    manifest["dropped_fingerprints"] = sorted(dropped)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    logger.info("\n✓ %d contaminated rows -> drop manifest %s", len(dropped), out)
    logger.info("  eval_multiturn --dedup-manifest %s will exclude them before scoring.", out)
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.dedup_multiturn")
    p.add_argument("--corpus", action="append", default=[], help="training corpus JSONL (repeat)")
    p.add_argument("--dataset", action="append", default=[], help="multi-turn set(s); default all")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--near", type=float, default=0.9, help="Jaccard >= this = contaminated (dropped)")
    p.add_argument("--fuzzy", type=float, default=0.6, help="Jaccard >= this = flagged for review")
    p.add_argument("--df-max", type=int, default=400, help="token distinctiveness cutoff")
    p.add_argument("--out", default="results/multiturn_dedup.json")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
