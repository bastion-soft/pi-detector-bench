# Prompt Injection Detector Benchmark

[![lint](https://github.com/bastion-soft/pi-detector-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/bastion-soft/pi-detector-bench/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/bastion-soft/pi-detector-bench/blob/main/notebooks/benchmark_colab.ipynb)

**An open, model-agnostic benchmark for prompt-injection *detectors* — measured on both axes (attack catch-rate **and** false positives on real traffic), threshold-agnostically, and reproducible from raw scores.**

Most prompt-injection benchmarks measure one thing: can a detector spot an attack? That's half the story. A detector that flags one in four *normal* user messages is an outage, not a guardrail — and a detector tuned to look great at one threshold can fall apart at another. This benchmark measures **both axes** and compares detectors **at the same catch rate**, so the ranking doesn't depend on where any model's 0.5 happens to fall.

> ### Disclosure
> This benchmark is maintained by **[Bastion Soft](https://github.com/bastion-soft)**, who also ship one of the evaluated detectors (`bastion-prompt-protection`). We keep it honest by design:
> - **Every number is reproducible from committed raw scores** with no GPU — rerun and check.
> - Bastion's model is scored through the **identical generic path** as every other model (a plain HuggingFace classifier — no special handling).
> - The interpretation doc **documents where our own model is weak** (see [`results/FINDINGS.md`](results/FINDINGS.md)).
> - **Contributions and criticism are welcome** — add your detector, propose a methodology change, or challenge a result.

## Leaderboard (seed results)

Ten open detectors, four held-out adversarial benchmarks. Full tables + latency in [`results/leaderboard.md`](results/leaderboard.md); these are **seed results** — [add your model](CONTRIBUTING.md).

| Detector | Params | Detection (avg AUC) | False positives (real traffic, @0.5) | FPR @ 95% catch |
|---|---:|---:|---:|---:|
| bastion-prompt-protection | 70M | 0.991 | 1.24% | 7.71% |
| sentinel (qualifire) | 395M | 0.955 | 23.60% | 46.30% |
| wolf-defender | 0.3B | 0.954 | 24.03% | 34.63% |
| hlyn judge | 70M | 0.950 | 21.67% | 77.12% |
| wolf-defender-small | 0.1B | 0.941 | 28.79% | 43.79% |
| proventra mdeberta | 280M | 0.843 | 21.83% | 82.22% |
| protectai v2 | 184M | 0.820 | 8.82% | 100.00% |
| deepset injection | 184M | 0.766 | 65.89% | 69.44% |
| fmops distilbert | 67M | 0.700 | 64.98% | 74.64% |
| meta prompt-guard† | 86M | 0.314 | 88.30% | 85.77% |

What this table is *for*: notice that detectors close on AUC are nowhere close on false positives, and that some low-FPR-at-0.5 numbers are bought by under-catching (visible in the "@95% catch" column). **Read [`results/FINDINGS.md`](results/FINDINGS.md) for the honest interpretation** — including each detector's weak spots. † `meta prompt-guard` is a deprecated, over-firing model kept for context (see FINDINGS).

![False-positive rate vs decision threshold](results/fpr_vs_threshold.png)

*False positives on real traffic as the decision threshold moves — a flat line is threshold-robust, a steep one is brittle. This is why a single fixed-threshold number can mislead, and why we also compare at a fixed catch rate. Full reading + the operating curve: [`results/FINDINGS.md`](results/FINDINGS.md).*

## Why this benchmark exists

It's not another attack dataset — it's a **methodology** (see [`METHODOLOGY.md`](METHODOLOGY.md)):

- **Two axes.** Detection (does it catch attacks?) **and** false positives on **real chat traffic** (WildChat + LMSYS), not synthetic benigns. A number on one axis alone is close to meaningless.
- **Threshold-agnostic.** Beyond the fixed-0.5 view, we report **FPR at a fixed detection rate** (tune each detector to catch 95% of attacks, compare the false-alarm cost), **EER**, and full **operating curves** — so no detector is helped or hurt by where its 0.5 falls.
- **Indirect / structured injection.** A separate axis for injection hidden inside data (documents, JSON, tool output), with a structured-data false-positive measure.
- **Reproducible from raw scores.** Every detector's per-prompt scores are committed (`results/scores/`), so all tables, curves, and operating points recompute offline with no GPU. The exact published numbers don't depend on trusting a GPU run.

## Run it yourself

```bash
git clone https://github.com/bastion-soft/pi-detector-bench.git
cd pi-detector-bench
pip install -e .
huggingface-cli login          # optional — only for gated entries/datasets

python -m scripts.run_leaderboard          --dump-scores results/scores            # detection
python -m scripts.measure_false_positives  --dump-scores results/scores            # false positives
python -m scripts.eval_indirect            --dump-scores results/scores_indirect   # indirect/structured

# Post-processing — no GPU, recomputes every table from the dumped scores:
python -m scripts.rebuild_results_from_scores
python -m scripts.analyze_operating_points
python -m scripts.analyze_operating_points --scores-dir results/scores_indirect --within-set --label indirect
python -m scripts.plot_operating_points    # optional curves (pip install -e ".[plot]")
```

No GPU? Run the whole suite on a free Colab T4 — open [`notebooks/benchmark_colab.ipynb`](notebooks/benchmark_colab.ipynb).

## Add your detector

It's a one-file PR. Append your model to [`models.yaml`](models.yaml):

```yaml
  - name: "my-detector (220M)"
    hf_id: "my-org/my-prompt-injection-detector"
    attack_label: 1        # softmax index meaning "attack" (or a list to sum)
    params: "220M"
```

…then run the harness and include the new result rows + scores. Full guide — including how to propose a **methodology change** or add a **dataset** — in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Documents

- **[`METHODOLOGY.md`](METHODOLOGY.md)** — how detectors are scored, and why (the two-axis / threshold-agnostic design).
- **[`results/FINDINGS.md`](results/FINDINGS.md)** — honest interpretation of the seed results, with graphs and per-detector weak spots.
- **[`CONTRIBUTING.md`](CONTRIBUTING.md)** — add a detector, a dataset, or a methodology change.

## License

Code: **MIT** (see [`LICENSE`](LICENSE)). Evaluation datasets retain their own licenses — some are gated and require accepting terms on the HuggingFace Hub. Committed results contain only per-prompt scores and labels, never dataset prompt text.
