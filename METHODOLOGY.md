# Methodology

How detectors are scored here, and why. The goal is a comparison that is **fair**
(same policy for every model), **realistic** (false positives measured on real
traffic), and **threshold-agnostic** (results don't depend on where any model's
0.5 falls). Everything is recomputable from the committed per-prompt scores.

## Scope

The benchmark measures detection of prompt-injection **and jailbreak techniques**: an input
that tries to override, extract, impersonate, break out of a delimiter, exfiltrate, suppress
refusals, or otherwise manipulate the model's instructions — directly, inside data the model
reads, or across turns. A plainly worded harmful request with no injection mechanism ("how do
I make X") is **out of scope**: that is a content-safety classifier's job, and a set built from
such requests measures harmful-intent detection rather than injection detection. See
[Benchmark revision 2026-11](#benchmark-revision-2026-11) for the sets this removed.

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

- **Direct attacks** (detection axis): three public held-out adversarial benchmarks —
  rogue, xTRam1-test, S-Labs-test. (JailbreakBench was removed in the 2026-11 revision.)
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
  see. Two families, reported separately (distinct threat models, never averaged):
  *jailbreak* (human multi-turn red-team tactics, MHJ) and *cross-step* (injection
  inside a tool output that poisons a later step, InjecAgent-enhanced + AgentDojo +
  ASB). CoSafe and the agent-jailbreak family (AgentHarm) were removed in the 2026-11
  revision. See the dedicated section below.

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
detector's context window — every model reads it through its own `max_length`, and we
report that window as a column. Since the 2026-11 revision the published multi-turn
numbers use `--chunk` (overlapping windows at each model's own window, see *Long inputs*
below) for every model, so a payload past the window is still read; the earlier
keep-recent truncation remains available and is recorded per row (`scoring` in the
score-file meta). A detector too small to see the poisoned turn
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

**Held out from training.** Every set here is a public benchmark, held out by
construction for any detector that did not train on it. A benchmark can't inspect
each model's training data, so held-out status is a **per-maintainer disclosure**,
not a benchmark-wide guarantee — the same posture the direct/indirect axes already
take. Contributors should confirm their detector didn't train on these sets. As the
maintainer that also ships a detector, Bastion self-audits its own corpus for overlap
against these conversations and reports the result in
[`results/FINDINGS.md`](results/FINDINGS.md) (a conflict-of-interest disclosure, kept
out of the model-agnostic scoring path). InjecAgent uses the **`_enhanced` split
only**, since its `_base` split is a common training source.

## Scoring protocol — the same for everyone

- **Pure classifier, one path.** Every detector is loaded as a HuggingFace
  `AutoModelForSequenceClassification` and scored identically. No model gets a
  special wrapper or SDK path. The registry ([`models.yaml`](models.yaml)) records
  each model's HF id and the softmax index that means "attack" (a list of indices for
  multi-class models, summed).
- **No per-model threshold tuning** for the fixed-threshold metrics: 0.5 for
  everyone. The threshold-agnostic metrics then remove the threshold entirely.
- **Declared thresholds, reported alongside.** A model's maintainer may declare an
  operating threshold (`threshold:` in [`models.yaml`](models.yaml); 0.5 when absent).
  Every table that reports FPR @0.5 — false positives, operating points, multi-turn —
  also reports FPR (and recall where relevant) at that declared threshold, and the
  results JSON records it per model. It is a reporting column, not tuning: it never
  changes scores, and the benchmark does not pick it.
- **Long inputs: truncate (default) or chunk, never per model.** By default an
  input longer than a model's window is truncated, which means a payload past the
  window is invisible and the detector scores a document it was never shown. On the
  published tiny (70M) at a 512 window, a clean 3.5k-token report and the same
  report with an injection appended both score **0.0801** — identical, because the
  injection is cut off. `--chunk` instead scores overlapping windows (overlap
  `max(96, window//8)`, capped at 32 windows) and aggregates them with a
  softmax-weighted average, which is bounded by the max, so adding quiet windows
  can never raise a score. The same two documents then score **0.1575** and
  **0.9969**.

  `--chunk` is a **run-wide switch applied to every entry**, at each model's own
  window — never a per-model setting. Chunking is generic inference that any
  sequence classifier supports, so enabling it for one entry and not another would
  be precisely the special-casing this benchmark refuses. It is **off by default**,
  so published numbers stay comparable to earlier runs, and when on the extra
  forward passes are charged to the reported latency. It is not free: the clean
  document above also roughly doubles (0.0801 → 0.1575), so a chunked run trades
  recall on buried payloads against false positives on long benign documents. Both
  sides belong in any table produced with it.
- **Calibration is auto-applied if shipped.** If a model's HF repo includes a
  `temperature.json`, logits are divided by it before softmax (temperature scaling).
  Models without one get `T=1.0` (no-op). This is applied uniformly — a model that
  ships calibration isn't penalized for it, nor advantaged beyond what calibration
  actually does.
- **Averages are unweighted** across datasets (S-Labs-test, n=2,000, counts as much
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
- **Score files must align with their rows.** Since the 2026-11 revision every dump
  records the loader revision and an order-sensitive fingerprint of the scored rows
  (`rows_sha256`; a hash, never the text). The offline rebuild refuses files that
  disagree about their rows (lengths, labels or fingerprints differing between
  detectors on one set), and files written before a loader change for their set are
  shown as *pending re-score* instead of being re-aligned by guesswork
  (`python -m scripts.rescore_plan` lists them).
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

## Benchmark revision 2026-11

_Decided by the maintainer and written up 2026-10-19._ This revision narrows the benchmark
to its stated scope, removes a label shortcut, and tightens reproducibility. Every model is
re-scored in the same change: tables whose rows did not change are rebuilt from the committed
per-prompt scores for all twelve detectors at once, and every set whose rows or scoring
protocol changed is re-scored for all twelve detectors in one run
([`notebooks/rescore_revision_2026_11.ipynb`](notebooks/rescore_revision_2026_11.ipynb)).
Until that run lands, those cells read **pending re-score**; no score is carried over from a
row order it was not computed on.

### Scope: three sets removed

The scope is injection and jailbreak *techniques* (see [Scope](#scope)). To check each set
against it, the rows were searched with an injection-mechanism pattern set covering these
classes: instruction override ("ignore previous instructions" and variants), system-prompt /
secret extraction, persona or role-play takeover (DAN-style "you are now…"), delimiter and
fake-role-tag injection, data exfiltration instructions, refusal suppression ("do not
refuse", "no warnings"), and similar control phrasing. Counts of rows with at least one
match:

| Set | Attack rows with a mechanism | Benign rows with a mechanism | Reading |
|---|---:|---:|---|
| JailbreakBench (direct) | 0 / 100 | 0 / 100 | 100 harmful requests vs 100 benign near-twins |
| AgentHarm (multi-turn, agent-jailbreak) | 8 / 176 | 8 / 176 | harmful vs harmless agent tasks; mechanisms equally common on both sides |
| CoSafe (multi-turn, jailbreak) | 0 / 400 | 14 / 400 | harmful intent expressed through dialogue coreference |

None of the three separates its labels by an injection or jailbreak technique; they separate
harmful from harmless intent. They are removed from the scored tables, with their loaders and
committed scores (the multi-turn *agent-jailbreak* family had only AgentHarm and is gone).
This also removes a strong result for the maintainer's own detector: Bastion's 0.986 AUC on
JailbreakBench was the top score on that set, and it no longer counts toward its average.
A pattern search is a coarse instrument — it can miss paraphrased mechanisms — but a
technique benchmark whose attack side shows no technique at all is not measuring one.

### MHJ: same turn structure on both sides

MHJ (Scale AI's human multi-turn red-teaming) stays: its attacks are human jailbreak tactics,
in scope. But its attack conversations contain **no assistant turns**, while every benign
negative (the shared WildChat/LMSYS multi-turn pool) contains them, so the single feature
"has an assistant turn" separated the labels perfectly (AUC 1.0, or 0.0 inverted), and
conversation length was itself a strong inverted cue (AUC 0.12–0.19). A detector could score
well by reacting to transcript shape. From this revision the MHJ comparison renders **both
sides user-turns-only**: assistant turns are dropped from the benign conversations (and would
be from attacks, which have none). Benign conversations keep their deterministic first-N
order and must still have at least two user turns. The cross-step sets (InjecAgent,
AgentDojo, ASB) are unaffected: they keep their user → assistant tool call → tool output
traces, and the benign pool they are padded with is read unchanged. A test asserts the
has-assistant-turn feature no longer separates MHJ labels. Length is no longer a perfect
inverse cue but remains correlated with the source (red-team conversations and chat
conversations differ in length); read the length-bucket table rather than the pooled AUC alone.

### Declared-threshold column

Some detectors are published with an operating threshold other than 0.5, and judging them
only at 0.5 reports a point their maintainers do not recommend. `models.yaml` takes an
optional `threshold:` per model (default 0.5). Every table that reports FPR @0.5 also
reports FPR, and recall where the table has attacks, at the declared threshold; the results
JSON records each model's declared threshold. At the time of writing no entry declares one,
so both columns agree; maintainers are invited to add theirs (with a model-card citation).

### Chunked multi-turn harness

Multi-turn conversations are scored with `--chunk`: overlapping windows at each model's own
context window (overlap `max(96, window//8)`, at most 32 windows) aggregated with a smooth
max, the same token windowing the direct and indirect harnesses offer. Under the earlier
keep-recent truncation a 512-token detector could not see a payload buried deeper than its
window, so the cross-step depth table measured window size as much as detection; with
chunking every model reads the whole conversation and the depth table measures detection.
The trade-off is documented under *Long inputs*: long benign conversations become several
windows, which can raise false positives. Every multi-turn row records its scoring mode.
`--chunk-unit turns` stays opt-in.

### Loader determinism

The BIPIA and InjecAgent loaders (indirect and multi-turn) read their source files in
filesystem `glob` order. Row order — and, through the per-class caps and index-assigned
attacks, row *content* — therefore depended on the machine. The file lists are now sorted.
To find out which committed scores this invalidates, the old loaders were run under every
file order and two detectors (bastion-prompt-protection, protectai v2) were re-scored locally
against the committed per-prompt scores:

- **InjecAgent (indirect)** — the committed scores match the sorted order exactly (dh before
  ds), so they stay valid and the table is rebuilt from them.
- **BIPIA (indirect)** — the committed scores match *table → email → code*; the sorted order is
  *code → email → table*. Attacks are assigned by row index, so the injected rows themselves
  change. BIPIA is **pending re-score** for every detector; indirect averages are over the
  remaining five sets until then (this removes one of Bastion's two weakest indirect sets from
  its average in the meantime).
- **InjecAgent (multi-turn)** — re-scored anyway with the chunked harness.

Score files now carry the loader revision and a row fingerprint, and the offline rebuild
refuses files that disagree about their rows, so this cannot recur silently.

### Known issues (not fixed in this revision)

Label noise found while auditing; recorded here so readers can weigh the affected columns.

- **rogue** — 103 rows labelled *attack* are multiple-choice safety quizzes ("pick the
  safe/unsafe answer", SafetyBench-style, containing `<ans>` and `<eoa>` markers), not
  injections.
- **S-Labs test** — about 40 rows labelled *attack* are vague curiosity prompts with no
  injection or jailbreak content.
- **False-positive samples** — the WildChat and LMSYS benign samples contain real jailbreak
  attempts (about 140 in WildChat, about 70 in LMSYS) that are counted as false positives
  when a detector flags them. This inflates every detector's FPR, more so for detectors that
  catch jailbreaks.
- **LMSYS scaffold** — one "you are the text completion model…" scaffold prompt appears 195
  times in the LMSYS sample (≈3.9% of it); detectors that flag it carry that whole share as
  false positives, and it drives several competitors' LMSYS FPR.
- **wolf-defender** — the current checkpoint on the Hub no longer reproduces its committed
  scores. The committed scores are what the direct and indirect tables show; the 2026-11
  multi-turn re-score necessarily uses the current checkpoint, so wolf-defender's
  multi-turn numbers and its direct/indirect numbers come from different checkpoints.

## Changing the methodology

This methodology is itself open to contribution — propose a new metric, a fairer
protocol, an additional dataset, or a fix. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
