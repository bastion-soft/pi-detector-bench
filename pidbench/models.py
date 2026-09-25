"""The detector registry — loaded from the top-level ``models.yaml``.

This is the single source of truth for *which* detectors the benchmark scores,
shared by every scoring script. Contributors add a model by appending an entry
to ``models.yaml`` (a PR), never by editing code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "models.yaml"


@dataclass
class ModelSpec:
    name: str
    hf_id: str
    attack_label: int | list[int]
    params: str | None = None
    gated: bool = False
    notes: str | None = None
    max_length: int | None = None  # None = auto-detect from config.max_position_embeddings


def load_models(path: str | Path | None = None, only: list[str] | None = None) -> list[ModelSpec]:
    """Load the detector registry from ``models.yaml`` (or a custom path).

    ``only`` keeps just the entries matching one of the given patterns, so a run
    can re-score a single detector without re-running the other eleven. Matching
    is case-insensitive substring or glob, against both ``name`` and ``hf_id``.

    This selects WHICH entries are scored; it never changes HOW one is scored.
    A partial run writes partial results -- merge it into a published table via
    ``--dump-scores`` and ``scripts/rebuild_results_from_scores.py``, so every row
    still comes from the same generic path.
    """
    import yaml  # PyYAML — declared in pyproject

    data = yaml.safe_load(Path(path or _DEFAULT_PATH).read_text())
    specs = [ModelSpec(**entry) for entry in data["models"]]
    if not only:
        return specs

    import fnmatch

    pats = [q.strip().lower() for q in only if q.strip()]
    kept, matched = [], set()
    for spec in specs:
        fields = (spec.name.lower(), spec.hf_id.lower())
        for q in pats:
            if any(q in f or fnmatch.fnmatch(f, q) for f in fields):
                kept.append(spec)
                matched.add(q)
                break
    unmatched = [q for q in pats if q not in matched]
    if unmatched:
        raise SystemExit(
            f"--model matched nothing: {', '.join(unmatched)}\n"
            f"available:\n  " + "\n  ".join(f"{s.name}  [{s.hf_id}]" for s in specs)
        )
    return kept


def run_provenance(args) -> dict:
    """Scoring settings that change what the numbers mean, for the results JSON.

    Two tables are only comparable when these match. Chunking in particular moves
    every score for any input longer than a model's window, so a run that used it
    must say so in its own output rather than relying on someone remembering the
    command line.
    """
    return {
        "chunk": bool(getattr(args, "chunk", False)),
        "chunk_temperature": (
            float(getattr(args, "chunk_temperature", 0.1))
            if getattr(args, "chunk", False)
            else None
        ),
        "models_filter": list(getattr(args, "model", []) or []) or None,
        "threshold": getattr(args, "threshold", None),
    }
