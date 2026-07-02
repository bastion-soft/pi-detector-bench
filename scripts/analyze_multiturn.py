"""Build the multi-turn / cross-step tables from dumped scores — no GPU.

Reads ``results/scores_multiturn/*.json`` (raw per-conversation scores + labels +
meta written by ``scripts.eval_multiturn``) and produces ``results/multiturn.md``
+ ``.json``. Three families are reported SEPARATELY (different threat models,
never averaged together):

  * jailbreak       — conversational, harmless-early / malicious-later (CoSafe, MHJ)
  * cross_step      — injection inside a tool output (InjecAgent, AgentDojo)
  * agent_jailbreak — malicious user query to an agent (AgentHarm)

Per family: a headline table (AUC / FPR@95 / EER + each model's window), and the
decisive stratified cut — detection rate by conversation-length bucket and by
injection position (early vs late turn). That cut is the direct answer to
"does the filter fire before the agent acts on the poisoned turn": if a model's
recall collapses on long conversations or early injections, its window is too
small to see the poison.

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

# length buckets on rendered chars (~4 chars/token): the boundaries bracket the
# common detector windows (256-tok ~1k chars, 512-tok ~2k chars).
LEN_BUCKETS = [
    (0, 1024, "≤256tok"),
    (1024, 2048, "256–512tok"),
    (2048, 4096, "512–1k tok"),
    (4096, 10**9, ">1k tok"),
]


def _bucket(n_chars: int) -> str:
    for lo, hi, name in LEN_BUCKETS:
        if lo < n_chars <= hi:
            return name
    return LEN_BUCKETS[-1][2]


def _position(inj_turn, n_turns) -> str:
    if inj_turn is None or not n_turns or n_turns <= 1:
        return "n/a"
    return "early" if inj_turn < n_turns / 2 else "late"


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
        "Conversations scored at natural length; each model truncates to its own "
        "window (**max_len** column). Families are reported separately — different "
        "threat models, never averaged together.\n"
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

        # ---- stratified: detection rate (recall@0.5) by length bucket & position ----
        # pooled across the family's datasets, attack rows only.
        strat = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # model -> key -> [hit, total]
        benign = defaultdict(
            lambda: defaultdict(lambda: [0, 0])
        )  # model -> lenbucket -> [fp, total]
        for model, by_ds in models.items():
            for rec in by_ds.values():
                for s, y, mo in zip(rec["scores"], rec["labels"], rec["meta"], strict=False):
                    lb = _bucket(int(mo.get("n_chars", 0)))
                    if y == 1:
                        pos = _position(mo.get("injection_turn"), mo.get("n_turns"))
                        for key in (f"len:{lb}", f"pos:{pos}"):
                            strat[model][key][1] += 1
                            strat[model][key][0] += int(s >= 0.5)
                    else:
                        benign[model][lb][1] += 1
                        benign[model][lb][0] += int(s >= 0.5)

        len_keys = [f"len:{b[2]}" for b in LEN_BUCKETS]
        pos_keys = ["pos:early", "pos:late"]
        cols = [k for k in len_keys + pos_keys if any(strat[m].get(k, [0, 0])[1] for m in strat)]
        if cols:
            lines.append(
                "**Detection rate (recall @0.5) — by conversation length and injection position.** "
                "A recall cliff on long conversations or early injections = the model's window "
                "can't see the poison.\n"
            )
            lines.append("| Model | " + " | ".join(c.split(":", 1)[1] for c in cols) + " |")
            lines.append("|" + "---|" * (len(cols) + 1))
            for model, _auc, *_ in head:
                cells = []
                for k in cols:
                    hit, tot = strat[model].get(k, [0, 0])
                    cells.append(f"{hit / tot:.2f}" if tot else "—")
                lines.append(f"| {model} | " + " | ".join(cells) + " |")
            lines.append("")
            out_json["families"][fam]["stratified"] = {
                m: {k: (strat[m][k][0] / strat[m][k][1] if strat[m][k][1] else None) for k in cols}
                for m, *_ in head
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
