# Methodology

How detectors are scored here, and why. The goal is a comparison that is **fair**
(same policy for every model), **realistic** (false positives measured on real
traffic), and **threshold-agnostic** (results don't depend on where any model's
0.5 falls). Everything is recomputable from the committed per-prompt scores.

## What's being measured

A prompt-injection detector outputs a risk score in `[0, 1]` per input; you pick a
threshold above which you block. Two questions decide whether it's deployable, and
they trade off against each other:

1. **Detection** — does it catch attacks it hasn't seen?
2. **False positives** — how often does it flag ordinary, benign traffic?

A number on either axis alone is close to meaningless. A 0.95-AUC detector that
trips on a quarter of real users is an outage; a detector with a low false-alarm
rate that misses attacks is theatre. We report both, and we hold one constant to
compare the other honestly.

## Three families of metric

| Metric | Threshold-dependent? | What it tells you |
|---|---|---|
| **ROC-AUC** | No | How well the detector *ranks* attacks above benign across all thresholds. The "how good is it really" number; can't be gamed by threshold choice. |
| **F1 / FPR at a fixed threshold (0.5)** | Yes | Out-of-the-box behaviour if you don't tune. Realistic (most deployments never tune) but unfair to models whose scores cluster near 0.5. |
| **FPR at a fixed detection rate; EER; operating curves** | No (normalized) | Tune each detector to the *same* catch rate (e.g. 95% of attacks), then compare the false-alarm cost. Removes the "where's the line" objection. |

The **fixed-detection-rate** view is the headline fair comparison: set each
detector's threshold so it catches 95% (and 99%) of attacks, then measure how much
**real benign traffic** it flags at that point. **Equal-error rate (EER)** — where
false-positive rate meets false-negative rate — is a single threshold-free summary.
The **operating curves** (`results/det_points*.json`, plotted as SVG/PNG) show the
whole catch-rate-vs-false-alarm trade-off.

## Datasets

All evaluation sets are **held out** — they are not training data for the detectors
(that's the contract behind the numbers). Three groups:

- **Direct attacks** (detection axis): four public held-out adversarial benchmarks —
  rogue, JailbreakBench, xTRam1-test, S-Labs-test.
- **Real benign traffic** (false-positive axis): first user turns sampled
  deterministically (fixed seed, reservoir sampling) from **WildChat-1M** and
  **LMSYS-Chat-1M** — real messages, not synthetic "benign" prompts. This is where
  detectors break in production.
- **Indirect / structured injection** (separate axis): injection hidden inside data
  — Z-Edgar, BIPIA, InjecAgent, AgentDojo, HackAPrompt, TensorTrust. Reported
  separately, **not folded into the direct average**, because it's a distinct
  capability. Each set is matched injected-vs-benign, so we can also measure the
  false-positive rate on **benign structured records** at a fixed catch rate
  (`--within-set`).
- **Multi-turn / cross-step injection** (separate axis): whole *conversations*,
  not single messages — the attacks a single-prompt classifier structurally cannot
  see. Three families, reported separately (distinct threat models, never averaged):
  *jailbreak* (harmless-early / malicious-later, CoSafe + MHJ), *cross-step*
  (injection inside a tool output that poisons a later step, InjecAgent-enhanced +
  AgentDojo + ASB), and *agent-jailbreak* (a malicious user query to a tool-using
  agent, AgentHarm). See the dedicated section below.

Some datasets are gated (LMSYS, HackAPrompt, MHJ) — the harness skips them cleanly if
you don't have access.

## Multi-turn / cross-step injection

A single-prompt classifier has no conversation state, so it cannot, on its own,
catch an attack that builds across turns or a payload planted in an earlier tool
output. The architectural answer (which the maintainers argue for publicly) is to
**feed the whole accumulated conversation to the filter** — at which point "can it
catch this" becomes a measurable detection question. This axis measures exactly
that, under one rule:

**Eval the task, not the model.** Each conversation is rendered (role-tagged) at
its **natural length** and scored as one input. We do **not** cap length to fit any
detector's context window — every model truncates per its own `max_length`, and we
report that window as a column. A detector too small to see the poisoned turn
*should* score worse; hiding that by trimming the input would measure the harness,
not the model. (Rendered lengths span from a few hundred to tens of thousands of
characters, so the short-window cliff is exercised, not assumed away.)

**Stratified reporting.** Beyond AUC / FPR@95%-catch / EER per family, the decisive
cut is **detection rate by conversation-length bucket × injection position**
(early vs late turn). This is the direct test of "does the filter fire before the
agent acts on the poison": a recall cliff on long conversations or early injections
means the window can't reach the payload. It converts the abstract "cross-step
injection" objection into a number.

**Matched pairs, static assembly.** Every injected conversation has a benign twin
that differs only by the payload (e.g. the same AgentDojo record or InjecAgent tool
output with the injection removed), so the signal is the injection, not surface
structure. Cross-step traces are assembled **statically** — we render the untrusted
tool-output content a detector would see; we do **not** execute an agent, because
this measures *detection*, not attack success. No LLM driver, deterministic,
reproducible.

**The never-trained wall, as a published number.** These sets are held out from
training. Because several share behavior seeds with training sources (e.g. MHJ and
HarmBench-derived corpus rows), we don't trust lineage — we **measure** it: every
rendered eval conversation is checked for near-duplication against the full training
corpus (`scripts/dedup_multiturn.py`), rows at/above a Jaccard threshold are dropped,
and the overlap rate is reported per set. Verbatim contamination is ≈0% across the
sets (the human/structured multi-turn wrappers are novel text even when a seed
behavior overlaps); the committed drop manifest (`results/multiturn_dedup.json`,
fingerprints only) makes the wall reproducible without corpus access.

Contamination note per source: InjecAgent uses the **`_enhanced` split only** (its
`_base` split is in training); it shows elevated *fuzzy* (paraphrase-level) overlap
with training but ≈0% verbatim, which is disclosed rather than hidden.

## Scoring protocol — the same for everyone

- **Pure classifier, one path.** Every detector is loaded as a HuggingFace
  `AutoModelForSequenceClassification` and scored identically. No model gets a
  special wrapper or SDK path. The registry ([`models.yaml`](models.yaml)) records
  each model's HF id and the softmax index that means "attack" (a list of indices for
  multi-class models, summed).
- **No per-model threshold tuning** for the fixed-threshold metrics: 0.5 for
  everyone. The threshold-agnostic metrics then remove the threshold entirely.
- **Calibration is auto-applied if shipped.** If a model's HF repo includes a
  `temperature.json`, logits are divided by it before softmax (temperature scaling).
  Models without one get `T=1.0` (no-op). This is applied uniformly — a model that
  ships calibration isn't penalized for it, nor advantaged beyond what calibration
  actually does.
- **Averages are unweighted** across datasets (JailbreakBench, n=200, counts as much
  as rogue, n=5,000). **Read the per-dataset columns**, not just the average.
- **Polarity check:** a binary detector whose AUC comes out below 0.5 has its label
  index reversed — flip its `attack_label` (0↔1). An AUC far below 0.5 is a config
  error, not a bad model.

## Reproducibility

- **Raw scores are committed.** Each scoring run can `--dump-scores` the per-prompt
  scores (`results/scores/`, `results/scores_indirect/`, `results/scores_multiturn/` —
  scores + labels only, no prompt text; the multi-turn files also carry per-example
  `meta` for length/injection-position stratification). Every table, curve, and
  operating point is then recomputed from those with **no GPU**
  (`rebuild_results_from_scores`, `analyze_operating_points`, `analyze_multiturn`).
- **GPU runs aren't bit-stable; the committed numbers are.** PyTorch detectors vary
  slightly run-to-run on a GPU (most visibly on small sets and near-0.5-AUC models).
  So the *published* numbers are pinned by the committed scores, not by trusting any
  single GPU run — rerun the Colab and you'll reproduce the scores to within that
  noise, with rankings unchanged.

## What this benchmark does *not* claim

Detectors catch the patterns they were trained on. No detector here addresses
domain-specific abuse (e.g. "give me a 100% discount" is valid user language) or
tool misuse (an infrastructure/authorization concern). **Multi-step / contextual
attacks** used to be out of scope entirely; the multi-turn axis above now *measures*
them — but only when the filter is given the whole conversation, and only as
detection (not attack prevention). A single message scored in isolation still has no
conversation state, and no classifier catches a brand-new exploit absent from its
training set. A detector is one layer of defense-in-depth, not the whole wall. See
[`results/FINDINGS.md`](results/FINDINGS.md).

## Changing the methodology

This methodology is itself open to contribution — propose a new metric, a fairer
protocol, an additional dataset, or a fix. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
