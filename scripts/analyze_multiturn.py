"""Build the multi-turn / cross-step tables from dumped scores — no GPU.

Reads ``results/scores_multiturn/*.json`` (raw per-conversation scores + labels +
meta written by ``scripts.eval_multiturn``) and produces ``results/multiturn.md``
+ ``.json``. Three families are reported SEPARATELY (different threat models,
never averaged together):

  * jailbreak       — conversational, harmless-early / malicious-later (CoSafe, MHJ)
  * cross_step      — injection inside a tool output (InjecAgent, AgentDojo)
  * agent_jailbreak — malicious user query to an agent (AgentHarm)

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

from pidbench.metrics import binary_metrics, eer
from pidbench.scores_io import load_all_scores

FAMILY_TITLE = {
    "jailbreak": "Multi-turn jailbreak (conversational)",
    "cross_step": "Cross-step agent injection (poisoned tool output)",
    "agent_jailbreak": "Agent-jailbreak by user (separate threat model)",
}
FAMILY_ORDER = ["cross_step", "jailbreak", "agent_jailbreak"]

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

    # index: family -> model -> dataset -> {scores, labels, meta}
    fam_rows: dict[str, dict[str, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
    for f in files:
        fam = f["meta"][0].get("family", "?")
        fam_rows[fam][f["runner"]][f["dataset"]] = f

    out_json: dict = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "families": {},
    }
    lines: list[str] = ["# Multi-turn / cross-step prompt-injection results", ""]
    lines.append(
        "Conversations are model-agnostic (fixed absolute lengths/depths); each model reads them "
        "through its own window, keeping the most recent turns (**max_len** column). Families are "
        "reported separately — different threat models, never averaged. Recall is then stratified "
        "along the axis that varies per family: injection **depth** (cross-step) or conversation "
        "**length** (jailbreak).\n"
    )
    lines.append(
        "> The cross-step headline AUC pools all injection depths, so it blends easy (recent) and "
        "hard (deeply-buried) cases — read it alongside the depth table, where a short-window model "
        "can be excellent at shallow injections yet collapse on deep ones.\n"
    )

    for fam in FAMILY_ORDER:
        if fam not in fam_rows:
            continue
        lines.append(f"## {FAMILY_TITLE.get(fam, fam)}\n")
        models = fam_rows[fam]
        datasets = sorted({d for m in models.values() for d in m})

        # ---- headline: AUC / FPR@95 / EER, mean across the family's datasets ----
        head = []
        for model, by_ds in models.items():
            aucs, fpr95s, eers, window = [], [], [], None
            for ds in datasets:
                rec = by_ds.get(ds)
                if not rec:
                    continue
                s = np.asarray(rec["scores"], float)
                y = np.asarray(rec["labels"], int)
                if len(set(y.tolist())) < 2:
                    continue
                bm = binary_metrics(s, y)
                aucs.append(bm.auc)
                fpr95s.append(bm.fpr_at_tpr_95)
                eers.append(eer(s, y)[0])
                window = rec["meta"][0].get("model_max_length", window)
            if aucs:
                head.append(
                    (
                        model,
                        statistics.mean(aucs),
                        statistics.mean(fpr95s),
                        statistics.mean(eers),
                        window,
                    )
                )
        head.sort(key=lambda r: r[1], reverse=True)
        lines.append("| Model | max_len | AUC | FPR@95%-catch | EER |")
        lines.append("|---|---|---|---|---|")
        for model, auc, fpr95, e, window in head:
            lines.append(f"| {model} | {window or '?'} | {auc:.3f} | {fpr95:.3f} | {e:.3f} |")
        lines.append("")
        out_json["families"].setdefault(fam, {})["headline"] = [
            {
                "model": m,
                "auc": round(a, 4),
                "fpr_at_95": round(fp, 4),
                "eer": round(e, 4),
                "max_len": w,
            }
            for m, a, fp, e, w in head
        ]

        # ---- stratified: recall@0.5 along the axis that VARIES for this family
        # (attack rows only). Cross-step → injection DEPTH (chars after the poison);
        # jailbreak → conversation LENGTH (innocent buildup). Agent-jailbreak is
        # single-turn, so there's nothing to stratify.
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
                    "the poison (keep-recent truncation). A cliff = the poison fell outside the "
                    "model's window ('step-1 poisons step-4'); a flat line = the window reaches it."
                    if axis == "depth"
                    else "**Detection rate (recall @0.5) by conversation length** — total innocent "
                    "buildup before the payload. These crescendo/coreference attacks place the "
                    "payload in the most recent turn (kept under keep-recent truncation), so more "
                    "buildup tends to mean *more* accumulated attack signal — recall usually rises, "
                    "not falls, with length."
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
