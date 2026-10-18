"""Build the multi-turn / cross-step tables from dumped scores — no GPU.

Reads ``results/scores_multiturn/*.json`` (raw per-conversation scores + labels +
meta written by ``scripts.eval_multiturn``) and produces ``results/multiturn.md``
+ ``.json``. Two families are reported SEPARATELY (different threat models,
never averaged together):

  * jailbreak  — conversational, human red-team tactics (MHJ)
  * cross_step — injection inside a tool output (InjecAgent, AgentDojo, ASB)

Per family: a headline table (AUC / FPR@95 / EER + each model's window), and the
decisive stratified cut along the axis that VARIES for that family — injection
**depth** (chars of context after the poison) for cross-step, conversation
**length** for jailbreak. With keep-recent truncation, a recall cliff as depth
grows is the direct answer to "step-1 poisons step-4": the poison fell outside
the model's window. Buckets are absolute (model-agnostic); the cliff surfaces
per-model at its own window.

    python -m scripts.analyze_multiturn
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from pidbench.metrics import binary_metrics, eer, fpr_at_threshold
from pidbench.models import DEFAULT_THRESHOLD, declared_thresholds, threshold_for
from pidbench.scores_io import check_alignment, load_all_scores

FAMILY_TITLE = {
    "jailbreak": "Multi-turn jailbreak (conversational)",
    "cross_step": "Cross-step agent injection (poisoned tool output)",
}
FAMILY_ORDER = ["cross_step", "jailbreak"]
# dataset (EvalSet name) -> family, for score files that are pending (not loaded)
DATASET_FAMILY = {
    "injecagent_mt/all_enhanced": "cross_step",
    "agentdojo_mt": "cross_step",
    "asb_mt": "cross_step",
    "mhj_mt": "jailbreak",
}

# ABSOLUTE buckets (model-agnostic; ~4 chars/token). The eval defines these once;
# each model reads the same conversations through its own window, so a model's
# cliff appears at its own window without tailoring the data to any model.
#
# Length = total conversation size (the jailbreak "buildup/dilution" axis).
LEN_BUCKETS = [
    (0, 1024, "≤256tok"),
    (1024, 2048, "256–512tok"),
    (2048, 4096, "512–1k tok"),
    (4096, 8192, "1k–2k tok"),
    (8192, 10**9, ">2k tok"),
]
# Depth = chars of context AFTER the poison = how far it's buried from the end
# (the cross-step "step-1 poisons step-4" axis; with keep-recent truncation a
# poison buried past a model's window falls out of view).
DEPTH_BUCKETS = [
    (-1, 0, "0 (last turn)"),
    (0, 1024, "≤256tok deep"),
    (1024, 2048, "256–512tok"),
    (2048, 4096, "512–1k tok"),
    (4096, 10**9, ">1k tok deep"),
]


def _bucket(value: int, buckets) -> str:
    for lo, hi, name in buckets:
        if lo < value <= hi:
            return name
    return buckets[-1][2]


def main() -> int:
    args = _parse_args()
    files = load_all_scores(args.scores_dir)
    files = [f for f in files if f.get("meta")]  # multi-turn files carry meta
    if not files:
        print(
            f"no multi-turn score files with meta in {args.scores_dir} — run scripts.eval_multiturn --dump-scores first",
            file=sys.stderr,
        )
        return 1

    # Refuse (raise) on files that disagree about their rows; files written before
    # the loader/scoring change for their set are not used — they are pending.
    files, pending = check_alignment(files)
    declared = declared_thresholds()

    # index: family -> model -> dataset -> {scores, labels, meta}
    fam_rows: dict[str, dict[str, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
    for f in files:
        fam = f["meta"][0].get("family", "?")
        fam_rows[fam][f["runner"]][f["dataset"]] = f
    # pending cells: family -> model -> {dataset: reason}
    fam_pending: dict[str, dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    for (runner, dataset), why in pending.items():
        fam = DATASET_FAMILY.get(dataset, "?")
        fam_pending[fam][runner][dataset] = why
        fam_rows[fam].setdefault(runner, {})

    out_json: dict = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_thresholds": {},
        "families": {},
    }
    lines: list[str] = ["# Multi-turn / cross-step prompt-injection results", ""]
    lines.append(
        "Conversations are model-agnostic (fixed absolute lengths/depths); each model reads them "
        "through its own window (**max_len** column) — chunked into overlapping windows when "
        "scored with `--chunk` (the published protocol since the 2026-11 revision), otherwise "
        "keeping the most recent turns. Families are reported separately — different threat "
        "models, never averaged. Recall is then stratified along the axis that varies per "
        "family: injection **depth** (cross-step) or conversation **length** (jailbreak).\n"
    )
    lines.append(
        "> The cross-step headline AUC pools all injection depths, so it blends easy (recent) and "
        "hard (deeply-buried) cases — read it alongside the depth table.\n"
    )
    if pending:
        lines.append(
            "> **Pending re-score.** Cells marked _pending re-score_ belong to sets whose rows or "
            "scoring protocol changed in the 2026-11 revision (MHJ benign negatives rendered "
            "user-turns-only, deterministic InjecAgent file order, chunked multi-turn scoring). "
            "The committed scores predate that change, so they are not shown. Re-score with "
            "`notebooks/rescore_revision_2026_11.ipynb`.\n"
        )

    for fam in FAMILY_ORDER:
        if fam not in fam_rows:
            continue
        lines.append(f"## {FAMILY_TITLE.get(fam, fam)}\n")
        models = fam_rows[fam]
        datasets = sorted(
            {d for m in models.values() for d in m}
            | {d for by in fam_pending[fam].values() for d in by}
        )

        # ---- headline: AUC / FPR@95 / EER + fixed-threshold FPR/recall, mean across
        # the family's datasets. A model with ANY of the family's sets pending is shown
        # as pending (a mean over a subset of sets would not be comparable).
        head, pend_models = [], []
        for model, by_ds in models.items():
            if fam_pending[fam].get(model):
                pend_models.append(model)
                continue
            thr = threshold_for(model, declared)
            acc = defaultdict(list)
            window = scoring = None
            for ds in datasets:
                rec = by_ds.get(ds)
                if not rec:
                    continue
                s = np.asarray(rec["scores"], float)
                y = np.asarray(rec["labels"], int)
                if len(set(y.tolist())) < 2:
                    continue
                bm = binary_metrics(s, y)
                acc["auc"].append(bm.auc)
                acc["fpr95"].append(bm.fpr_at_tpr_95)
                acc["eer"].append(eer(s, y)[0])
                for tag, t in (("05", DEFAULT_THRESHOLD), ("thr", thr)):
                    acc[f"fpr_{tag}"].append(fpr_at_threshold(s[y == 0], t))
                    acc[f"rec_{tag}"].append(float(np.mean(s[y == 1] >= t)))
                window = rec["meta"][0].get("model_max_length", window)
                scoring = rec["meta"][0].get("scoring", "left_truncated")
            if acc["auc"]:
                head.append(
                    {
                        "model": model,
                        **{k: statistics.mean(v) for k, v in acc.items()},
                        "thr": thr,
                        "window": window,
                        "scoring": scoring,
                    }
                )
                out_json["declared_thresholds"][model] = thr
        head.sort(key=lambda r: r["auc"], reverse=True)
        lines.append(
            "| Model | max_len | AUC | FPR@95%-catch | EER | FPR @0.5 | recall @0.5 "
            "| declared thr | FPR @thr | recall @thr |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in head:
            lines.append(
                f"| {r['model']} | {r['window'] or '?'} | {r['auc']:.3f} | {r['fpr95']:.3f} "
                f"| {r['eer']:.3f} | {r['fpr_05']:.3f} | {r['rec_05']:.3f} | {r['thr']:g} "
                f"| {r['fpr_thr']:.3f} | {r['rec_thr']:.3f} |"
            )
        for model in sorted(pend_models):
            thr = threshold_for(model, declared)
            out_json["declared_thresholds"][model] = thr
            cells = " | ".join(["pending re-score"] * 5)
            lines.append(
                f"| {model} | — | {cells} | {thr:g} | pending re-score | pending re-score |"
            )
        lines.append("")
        fam_out = out_json["families"].setdefault(fam, {})
        fam_out["headline"] = [
            {
                "model": r["model"],
                "auc": round(r["auc"], 4),
                "fpr_at_95": round(r["fpr95"], 4),
                "eer": round(r["eer"], 4),
                "fpr_at_0.5": round(r["fpr_05"], 4),
                "recall_at_0.5": round(r["rec_05"], 4),
                "declared_threshold": r["thr"],
                "fpr_at_declared": round(r["fpr_thr"], 4),
                "recall_at_declared": round(r["rec_thr"], 4),
                "max_len": r["window"],
                "scoring": r["scoring"],
            }
            for r in head
        ]
        if pend_models:
            fam_out["pending_rescore"] = {m: fam_pending[fam][m] for m in sorted(pend_models)}
        head = [(r["model"],) for r in head]  # model order for the stratified table

        # ---- stratified: recall@0.5 along the axis that VARIES for this family
        # (attack rows only). Cross-step → injection DEPTH (chars after the poison);
        # jailbreak → conversation LENGTH (innocent buildup).
        axis = {"cross_step": "depth", "jailbreak": "length"}.get(fam)
        if axis:
            buckets = DEPTH_BUCKETS if axis == "depth" else LEN_BUCKETS
            field = "chars_after" if axis == "depth" else "n_chars"
            strat = defaultdict(
                lambda: defaultdict(lambda: [0, 0])
            )  # model -> bucket -> [hit,total]
            for model, by_ds in models.items():
                for rec in by_ds.values():
                    for s, y, mo in zip(rec["scores"], rec["labels"], rec["meta"], strict=False):
                        if y != 1:
                            continue
                        b = _bucket(int(mo.get(field, 0)), buckets)
                        strat[model][b][1] += 1
                        strat[model][b][0] += int(s >= 0.5)
            cols = [b[2] for b in buckets if any(strat[m].get(b[2], [0, 0])[1] for m in strat)]
            if cols:
                caption = (
                    "**Detection rate (recall @0.5) by injection depth** — chars of context after "
                    "the poison. Under keep-recent truncation a cliff means the poison fell "
                    "outside the model's window ('step-1 poisons step-4'); chunked scoring "
                    "(`--chunk`) reads every window, so a cliff there is a detection limit."
                    if axis == "depth"
                    else "**Detection rate (recall @0.5) by conversation length** — total "
                    "conversation size (attacks only). MHJ places the payload in the most "
                    "recent user turn, so length mostly measures how much red-team buildup "
                    "precedes it."
                )
                lines.append(caption + "\n")
                lines.append("| Model | " + " | ".join(cols) + " |")
                lines.append("|" + "---|" * (len(cols) + 1))
                for model, *_ in head:
                    cells = [
                        f"{strat[model][c][0] / strat[model][c][1]:.2f}"
                        if strat[model][c][1]
                        else "—"
                        for c in cols
                    ]
                    lines.append(f"| {model} | " + " | ".join(cells) + " |")
                lines.append("")
                out_json["families"][fam]["stratified"] = {
                    "axis": axis,
                    "buckets": cols,
                    "recall": {
                        m: {
                            c: (strat[m][c][0] / strat[m][c][1] if strat[m][c][1] else None)
                            for c in cols
                        }
                        for m, *_ in head
                    },
                }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "multiturn.json").write_text(json.dumps(out_json, indent=2))
    lines.append(
        "Held-out public benchmarks (held out by construction for detectors that "
        "didn't train on them). Static "
        "assembly — no agent execution. Scored pure-model via the same path as every "
        "other leaderboard."
    )
    lines.append(
        f"\n_Generated {time.strftime('%Y-%m-%d')} via `python -m scripts.analyze_multiturn`._"
    )
    (out_dir / "multiturn.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\n✓ wrote {out_dir / 'multiturn.md'} and multiturn.json")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.analyze_multiturn")
    p.add_argument("--scores-dir", default="results/scores_multiturn")
    p.add_argument("--output-dir", default="results")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main())
