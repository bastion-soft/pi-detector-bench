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

Since the 2026-11 revision every dump is also stamped with
``"loader_revision"`` (the loader revision that produced the rows) and, when the
caller passes the rows, ``"rows_sha256"`` (a fingerprint of the exact texts +
labels, in order). Scores are only meaningful against the row order they were
computed on, so :func:`check_alignment` refuses files whose rows cannot be shown
to match: wrong lengths, labels or fingerprints that disagree between detectors
on the same dataset, or a dataset whose loader changed after the file was
written (see :data:`ROWS_CHANGED`).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path

# Bumped whenever a loader change alters the rows (content or order) of any set.
LOADER_REVISION = "2026-11"

# Datasets (by their EvalSet name) whose rows or scoring protocol changed in a
# loader revision. A score file for one of these is only usable if it was written
# at or after that revision; older files are reported as "pending re-score" and
# never silently aligned with the new rows. ``requires`` optionally names a
# per-row meta value the file must carry (multi-turn scoring mode).
ROWS_CHANGED: dict[str, dict] = {
    "mhj_mt": {
        "revision": "2026-11",
        "reason": "benign negatives re-rendered user-turns-only; scoring now --chunk",
        "requires": {"scoring": "chunked_tokens"},
    },
    "injecagent_mt/all_enhanced": {
        "revision": "2026-11",
        "reason": "file order now sorted (was filesystem glob order); scoring now --chunk",
        "requires": {"scoring": "chunked_tokens"},
    },
    "agentdojo_mt": {
        "revision": "2026-11",
        "reason": "scoring now --chunk (rows unchanged)",
        "requires": {"scoring": "chunked_tokens"},
    },
    "asb_mt": {
        "revision": "2026-11",
        "reason": "scoring now --chunk (rows unchanged)",
        "requires": {"scoring": "chunked_tokens"},
    },
}


class MisalignedScoresError(ValueError):
    """A score file whose rows can't be shown to match the dataset's rows."""


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
    meta: Sequence[dict] | None = None,
    texts: Sequence[str] | None = None,
) -> Path:
    """Write one (runner, dataset) score file; returns its path.

    ``meta`` (optional) is a per-example list of small dicts persisted verbatim
    alongside scores/labels — used by the multi-turn axis to carry length
    buckets and injection position so the analysis can stratify offline. Older
    readers ignore the extra key; it's absent for sets that don't supply it.

    ``texts`` (optional) are the scored rows, in order; only their fingerprint
    is stored (``rows_sha256``), never the text.
    """
    if labels is not None and len(labels) != len(scores):
        raise MisalignedScoresError(
            f"{runner} / {dataset}: {len(scores)} scores vs {len(labels)} labels"
        )
    if texts is not None and len(texts) != len(scores):
        raise MisalignedScoresError(
            f"{runner} / {dataset}: {len(scores)} scores vs {len(texts)} rows"
        )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "runner": runner,
        "dataset": dataset,
        "kind": kind,
        "loader_revision": LOADER_REVISION,
        "scores": [round(float(s), ndigits) for s in scores],
        "labels": [int(x) for x in labels] if labels is not None else None,
    }
    if texts is not None:
        payload["rows_sha256"] = rows_fingerprint(texts, labels)
    if meta is not None:
        payload["meta"] = list(meta)
    path = out_dir / f"{slugify(runner)}__{slugify(dataset)}.json"
    path.write_text(json.dumps(payload))
    return path


def load_all_scores(in_dir: str | Path) -> list[dict]:
    """Load every score file in ``in_dir`` (sorted by filename)."""
    in_dir = Path(in_dir)
    return [json.loads(p.read_text()) for p in sorted(in_dir.glob("*.json"))]


def rows_fingerprint(texts: Sequence[str], labels: Sequence[int] | None = None) -> str:
    """Order-sensitive sha256 of the scored rows (text + label per row)."""
    h = hashlib.sha256()
    for i, t in enumerate(texts):
        h.update(hashlib.sha256(t.encode("utf-8")).digest())
        h.update(b"|" + (str(int(labels[i])).encode() if labels is not None else b"-") + b"\n")
    return h.hexdigest()


def pending_reason(rec: dict) -> str | None:
    """Why ``rec`` predates a loader change for its dataset (None = usable)."""
    rule = ROWS_CHANGED.get(rec.get("dataset", ""))
    if rule is None:
        return None
    if (rec.get("loader_revision") or "") < rule["revision"]:
        return f"scored before loader revision {rule['revision']} ({rule['reason']})"
    for key, want in (rule.get("requires") or {}).items():
        got = {m.get(key) for m in (rec.get("meta") or [{}])}
        if got != {want}:
            return f"meta {key}={sorted(map(str, got))}, revision requires {want!r}"
    return None


def check_alignment(records: list[dict]) -> tuple[list[dict], dict[tuple[str, str], str]]:
    """Split score records into (usable, pending) and refuse misaligned ones.

    Returns the records that may be used and ``{(runner, dataset): reason}`` for
    files that predate a row change for their dataset (they need a re-score and are
    shown as pending, never re-aligned by guesswork). Raises
    :class:`MisalignedScoresError` for files that are internally inconsistent
    (lengths) or that disagree with other detectors' files on the same dataset
    (labels or ``rows_sha256``) — those can't all describe the same rows.
    """
    usable: list[dict] = []
    pending: dict[tuple[str, str], str] = {}
    by_dataset: dict[tuple[str, str], list[dict]] = {}
    for rec in records:
        name = f"{rec.get('runner')} / {rec.get('dataset')}"
        n = len(rec["scores"])
        if rec.get("labels") is not None and len(rec["labels"]) != n:
            raise MisalignedScoresError(f"{name}: {n} scores vs {len(rec['labels'])} labels")
        if rec.get("meta") is not None and len(rec["meta"]) != n:
            raise MisalignedScoresError(f"{name}: {n} scores vs {len(rec['meta'])} meta rows")
        why = pending_reason(rec)
        if why is not None:
            pending[(rec["runner"], rec["dataset"])] = why
            continue
        by_dataset.setdefault((rec["dataset"], rec["kind"]), []).append(rec)
        usable.append(rec)
    for (dataset, _kind), recs in by_dataset.items():
        labels = {tuple(r["labels"]) if r.get("labels") is not None else None for r in recs}
        lengths = {len(r["scores"]) for r in recs}
        hashes = {r["rows_sha256"] for r in recs if r.get("rows_sha256")}
        if len(lengths) > 1 or len(labels) > 1 or len(hashes) > 1:
            raise MisalignedScoresError(
                f"{dataset}: detectors' score files disagree on the rows "
                f"(lengths {sorted(lengths)}, {len(labels)} label orders, "
                f"{len(hashes)} row fingerprints) — re-score every detector on the same rows"
            )
    return usable, pending
