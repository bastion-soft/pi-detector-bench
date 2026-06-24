# Contributing

This benchmark is meant to be argued with and added to. Three kinds of
contribution, in order of how common they'll be:

1. **Add a detector** to the leaderboard.
2. **Propose a methodology change** (a metric, a fairer protocol, a fix).
3. **Add a dataset** (an attack set, a benign source, or an indirect set).

By contributing you agree to the [Code of Conduct](CODE_OF_CONDUCT.md) and that
your contribution is licensed under the repo's [MIT License](LICENSE).

## Setup

```bash
git clone https://github.com/bastion-soft/pi-detector-bench.git
cd pi-detector-bench
pip install -e ".[dev,plot]"
huggingface-cli login        # optional — only for gated models/datasets
ruff check . && ruff format --check .
```

---

## 1. Add a detector

The detector must be a HuggingFace `AutoModelForSequenceClassification` (it's
scored as a plain classifier — the same generic path as every other model; no
custom code, and **no `trust_remote_code`**, which we decline for security
reasons).

**Step 1 — register it.** Append an entry to [`models.yaml`](models.yaml):

```yaml
  - name: "my-detector (220M)"        # shown in the tables
    hf_id: "my-org/my-detector"       # public HF id
    attack_label: 1                   # softmax index for "attack" (or a list to sum, e.g. [1, 2])
    params: "220M"
    # gated: true                     # only if the model needs HF access approval
```

**Step 2 — run the harness** (a free Colab T4 works — see `notebooks/benchmark_colab.ipynb`):

```bash
python -m scripts.run_leaderboard          --dump-scores results/scores
python -m scripts.measure_false_positives  --dump-scores results/scores
python -m scripts.eval_indirect            --dump-scores results/scores_indirect
python -m scripts.rebuild_results_from_scores
python -m scripts.analyze_operating_points
python -m scripts.analyze_operating_points --scores-dir results/scores_indirect --within-set --label indirect
```

**Step 3 — open the PR** including: the `models.yaml` entry, the regenerated
`results/*.{json,md}`, and the new per-prompt score files under `results/scores*/`
(scores + labels only — no prompt text). Maintainers re-derive your model's tables
from the committed scores to confirm they reproduce.

**Sanity checks before you submit:**
- If your model's AUC is below 0.5, your `attack_label` is probably inverted — flip it (0↔1).
- Don't tune a per-model threshold; the fixed-threshold metrics use 0.5 for everyone.

## 2. Propose a methodology change

The methodology is not settled — better ideas are welcome (a new metric, a fairer
aggregation, a correction). Open an issue first to discuss, then a PR that:
- updates [`METHODOLOGY.md`](METHODOLOGY.md) with the rationale,
- implements it in `pidbench/` / `scripts/`,
- regenerates the affected results, and
- explains what changed and why it's fairer — *especially* if it changes the ranking.

Adversarial scrutiny is explicitly welcome: if you can show a result is an artifact
of the protocol, that's a valuable contribution.

## 3. Add a dataset

- **Direct attack set** → add a loader to `pidbench/data.py` returning an `EvalSet`
  (texts + 0/1 labels) and register it in `BENCHMARK_LOADERS`.
- **Benign source** (false-positive axis) → add a loader to
  `scripts/measure_false_positives.py`'s `DATASET_LOADERS`.
- **Indirect / structured set** → add a loader to `pidbench/indirect_data.py` and
  `INDIRECT_LOADERS`.

For any dataset: it must be **held out** from common training corpora (or clearly
labelled otherwise), publicly accessible (gated is fine — handle it with a clean
skip), and you should note its license. We store only **scores + labels**, never the
dataset's prompt text, so committing results never redistributes gated data.

## Quality bar

- `ruff check .` and `ruff format --check .` pass (CI enforces this).
- New numbers reproduce from committed scores (`rebuild_results_from_scores` is the check).
- Be honest in interpretation — if something is a weak spot (including for the
  maintainers' own model), say so. That honesty is the whole point of the project.
