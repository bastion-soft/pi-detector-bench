"""Persist and load per-prompt detector scores.

The eval scripts can dump the raw per-prompt scores they compute (which are
otherwise discarded after metrics are calculated). Once dumped, every
operating-point analysis — FPR at a fixed detection rate, EER, DET/ROC curves,
arbitrary thresholds — can be computed in post with no model inference, and
reproduced by anyone from the committed files.

File layout: one JSON per (runner, dataset) at
``<dir>/<slug(runner)>__<slug(dataset)>.json`` with:

    {"runner": str, "dataset": str, "kind": "attack" | "benign",
     "scores": [float, ...], "labels": [int, ...] | null}

``labels`` is present for attack/detection sets (mixed attack+benign) and null
for benign-only false-positive sets.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path


def slugify(text: str) -> str:
    """Filesystem-safe slug: lowercase, non-alphanumerics collapsed to ``_``."""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")


def dump_scores(
    out_dir: str | Path,
    runner: str,
    dataset: str,
    kind: str,
    scores: Sequence[float],
    labels: Sequence[int] | None = None,
    ndigits: int = 5,
) -> Path:
    """Write one (runner, dataset) score file; returns its path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "runner": runner,
        "dataset": dataset,
        "kind": kind,
        "scores": [round(float(s), ndigits) for s in scores],
        "labels": [int(x) for x in labels] if labels is not None else None,
    }
    path = out_dir / f"{slugify(runner)}__{slugify(dataset)}.json"
    path.write_text(json.dumps(payload))
    return path


def load_all_scores(in_dir: str | Path) -> list[dict]:
    """Load every score file in ``in_dir`` (sorted by filename)."""
    in_dir = Path(in_dir)
    return [json.loads(p.read_text()) for p in sorted(in_dir.glob("*.json"))]
