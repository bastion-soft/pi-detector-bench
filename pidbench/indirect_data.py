"""Indirect / agentic prompt-injection eval sets.

Held-out sets that complement the direct benchmarks in ``eval/data.py``
(rogue/xTRam1/S-Labs/JailbreakBench) so the harness can show direct vs indirect
injection side-by-side. Scored the same way as the direct benchmarks (pure model,
all baselines) and written to a SEPARATE table — these target structured/indirect
injection, a distinct capability, so they aren't folded into the main average.

Sources: Z-Edgar (injection in JSON/XML agent interactions), BIPIA (injection in
documents), InjecAgent (poisoned tool outputs), AgentDojo, HackAPrompt (gated),
TensorTrust. These benchmarks originally measure *attack success*; we adapt them
to a binary *detection* task (injected=1 vs clean=0). All loaders return
``pidbench.data.EvalSet``; a loader that can't map fields (missing dependency, gated
access, or schema drift) returns an empty set and is skipped with a warning.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import re
import subprocess
from functools import partial

from pidbench.data import EvalSet, load_deepset_test

logger = logging.getLogger(__name__)


def _clone(url: str, path: str) -> None:
    if not os.path.exists(path):
        subprocess.run(["git", "clone", "--depth", "1", url, path], check=True)


def _benign_pool(n: int) -> list[str]:
    """Benign negatives for attack-only sources — drawn from the held-out deepset
    benign rows so the set is two-class (AUC needs both classes)."""
    try:
        ds = load_deepset_test()
        benign = [t for t, lbl in zip(ds.texts, ds.labels, strict=False) if lbl == 0]
        if benign:
            return benign[:n]
    except Exception:
        pass
    return [
        "What is the capital of Lithuania?",
        "Summarize the attached quarterly report.",
        "Translate this sentence into French.",
        "How do I sort a list in Python?",
    ] * (n // 4 + 1)


def _mk(name: str, pos: list[str], neg: list[str], max_per_class: int) -> EvalSet:
    pos, neg = pos[:max_per_class], neg[:max_per_class]
    texts = pos + neg
    labels = [1] * len(pos) + [0] * len(neg)
    return EvalSet(name=name, texts=texts, labels=labels)


# --------------------------------------------------------------------------- #
# BIPIA — injection embedded in documents (email / table / code / qa / abstract)
# --------------------------------------------------------------------------- #
# CLEAN contexts ({context, question, ideal}) are stored separately from the
# injection strings. We build a PAIRED detection set: each context yields a CLEAN
# row (neg) and an INJECTED twin (pos = context + attack appended) — measuring the
# benign<->injected gap (does the model key on the injection or the document?).
def _bipia_attacks() -> list[str]:
    out: list[str] = []
    for fn in ("text_attack_test.json", "code_attack_test.json"):
        path = os.path.join("BIPIA", "benchmark", fn)
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                d = json.load(f)
        except Exception:
            continue
        if isinstance(d, dict):
            for v in d.values():
                if isinstance(v, list):
                    out.extend(s for s in v if isinstance(s, str) and s.strip())
    return out


def load_bipia(limit: int | None = None, domain: str | None = None) -> EvalSet:
    """domain=None pools all document types; or one of email/table/code."""
    m = limit or 400
    _clone("https://github.com/microsoft/BIPIA", "BIPIA")
    pattern = f"BIPIA/benchmark/{domain}/test.jsonl" if domain else "BIPIA/benchmark/**/test.jsonl"
    name = f"bipia/{domain}" if domain else "bipia/indirect"
    contexts: list[str] = []
    for p in glob.glob(pattern, recursive=True):
        with open(p) as f:
            for line in f:
                try:
                    ctx = json.loads(line).get("context")
                except Exception:
                    continue
                if isinstance(ctx, list):  # code domain stores context as line list
                    ctx = "\n".join(str(x) for x in ctx)
                if isinstance(ctx, str) and ctx.strip():
                    contexts.append(ctx)
        if len(contexts) >= m:
            break
    attacks = _bipia_attacks()
    if not contexts or not attacks:
        return EvalSet(name=name, texts=[], labels=[])
    pos, neg = [], []
    for i, ctx in enumerate(contexts[:m]):
        atk = attacks[i % len(attacks)]
        pos.append(f"{ctx}\n\n{atk}")  # indirect injection appended to the document
        neg.append(ctx)  # same document, clean
    return _mk(name, pos, neg, m)


# --------------------------------------------------------------------------- #
# InjecAgent — injection via tool outputs fed back to an agent (ENHANCED only)
# --------------------------------------------------------------------------- #
# 'Tool Response Template' is the CLEAN structure with an '<Attacker Instruction>'
# slot; we build a PAIRED set — pos fills the slot with the real attack, neg with a
# context-aware benign string. Loads the `_enhanced` split.
_IA_SLOT = "<Attacker Instruction>"
_IA_FILLERS = {
    "description": "A dependable, well-reviewed option that works well for everyday use.",
    "content": "Reminder: the team sync has been moved to 3pm on Thursday.",
    "snippet": "Draft notes from the planning meeting — nothing urgent to action here.",
    "body": "Hi, just following up on our earlier conversation. Thanks for your help!",
    "review_content": "Great product, exactly as described — would recommend.",
    "short_bio": "Software engineer based in Berlin who enjoys hiking and photography.",
    "bio": "Software engineer based in Berlin who enjoys hiking and photography.",
    "event_name": "Quarterly Team Offsite",
}
_IA_DEFAULT_FILL = "Thanks for your help — everything looks good on my end."
_IA_KEY_RE = re.compile(r"'([A-Za-z0-9_ ]+)'\s*:\s*'?" + re.escape(_IA_SLOT))


def _ia_benign_fill(template: str) -> str:
    m = _IA_KEY_RE.search(template)
    return _IA_FILLERS.get(m.group(1) if m else "", _IA_DEFAULT_FILL)


def load_injecagent(limit: int | None = None, category: str | None = None) -> EvalSet:
    """category=None pools all attacks; 'dh' = direct-harm, 'ds' = data-stealing.
    Uses the `_enhanced` split."""
    m = limit or 400
    _clone("https://github.com/uiuc-kang-lab/InjecAgent", "InjecAgent")
    glob_pat = (
        f"InjecAgent/**/test_cases_{category}_enhanced.json"
        if category
        else "InjecAgent/**/test_cases_*_enhanced.json"
    )
    name = f"injecagent/{category}_enhanced" if category else "injecagent/enhanced"
    pos, neg = [], []
    for p in glob.glob(glob_pat, recursive=True):
        try:
            with open(p) as f:
                rows = json.load(f)
        except Exception:
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            tmpl = row.get("Tool Response Template")
            atk = row.get("Attacker Instruction")
            if not isinstance(tmpl, str) or _IA_SLOT not in tmpl:
                continue
            if isinstance(atk, str) and atk.strip():
                pos.append(f"Tool result: {tmpl.replace(_IA_SLOT, atk)}")
                neg.append(f"Tool result: {tmpl.replace(_IA_SLOT, _ia_benign_fill(tmpl))}")
        if len(pos) >= m and len(neg) >= m:
            break
    if not pos:
        return EvalSet(name=name, texts=[], labels=[])
    return _mk(name, pos, neg, m)


# --------------------------------------------------------------------------- #
# Z-Edgar — indirect injection in JSON/XML agent interactions (held-out test split)
# --------------------------------------------------------------------------- #
# Native matched pairs: each record has `clean` (benign structure) and `attacked`
# (same structure + injection). easy/hard → clean(neg) + attacked(pos); no_attack
# → clean(neg) only. English-filtered. Scores the held-out **test** split.
_ZEDGAR_RID = "Z-Edgar/Agent-IPI-Structured-Interaction-Datasets-v2"


def _zedgar_text(v) -> str | None:
    return (
        json.dumps(v, ensure_ascii=False)
        if isinstance(v, dict)
        else (v if isinstance(v, str) else None)
    )


def _mostly_ascii(s: str, thresh: float = 0.85) -> bool:
    return bool(s) and sum(ord(c) < 128 for c in s) / len(s) >= thresh


def load_zedgar(limit: int | None = None) -> EvalSet:
    m = limit or 600
    try:
        from huggingface_hub import hf_hub_download
    except Exception:
        return EvalSet(name="zedgar/structured", texts=[], labels=[])

    def _ok(s):
        return bool(s) and _mostly_ascii(s) and 20 <= len(s) <= 4000

    pos, neg = [], []
    for fmt in ("json", "xml"):
        for diff in ("easy", "hard", "no_attack"):
            try:
                path = hf_hub_download(_ZEDGAR_RID, f"test/{fmt}/{diff}.json", repo_type="dataset")
                with open(path, encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                continue
            for rec in records:
                clean = _zedgar_text(rec.get("clean"))
                if diff == "no_attack":
                    if _ok(clean):
                        neg.append(clean)
                else:
                    atk = _zedgar_text(rec.get("attacked"))
                    if _ok(clean) and _ok(atk):
                        neg.append(clean)
                        pos.append(atk)
            if len(pos) >= m and len(neg) >= m:
                break
    if not pos:
        return EvalSet(name="zedgar/structured", texts=[], labels=[])
    return _mk("zedgar/structured", pos, neg, m)


# --------------------------------------------------------------------------- #
# AgentDojo — injection-task goals (pos) vs user-task prompts (neg)
# --------------------------------------------------------------------------- #
def load_agentdojo(limit: int | None = None) -> EvalSet:
    m = limit or 300
    try:
        from agentdojo.task_suite.load_suites import get_suites  # type: ignore

        suites = get_suites("v1")
    except Exception:
        try:
            from agentdojo.task_suites import SUITES as suites  # type: ignore  # noqa: N811
        except Exception:
            return EvalSet(name="agentdojo/agent", texts=[], labels=[])
    pos, neg = [], []
    iterable = suites.values() if isinstance(suites, dict) else suites
    for suite in iterable:
        inj = getattr(suite, "injection_tasks", {}) or {}
        usr = getattr(suite, "user_tasks", {}) or {}
        for it in inj.values() if isinstance(inj, dict) else inj:
            goal = getattr(it, "GOAL", None) or getattr(it, "goal", None)
            if isinstance(goal, str) and goal:
                pos.append(goal)
        for ut in usr.values() if isinstance(usr, dict) else usr:
            prompt = getattr(ut, "PROMPT", None) or getattr(ut, "prompt", None)
            if isinstance(prompt, str) and prompt:
                neg.append(prompt)
    return _mk("agentdojo/agent", pos, neg, m)


# --------------------------------------------------------------------------- #
# HackAPrompt — large crowdsourced injection-attempt corpus (GATED)
# --------------------------------------------------------------------------- #
def load_hackaprompt(limit: int | None = None) -> EvalSet:
    # Accept the terms on the HF page once and set HF_TOKEN, else load_dataset
    # raises 401/403 (caught -> empty set, skipped with a warning).
    m = limit or 400
    try:
        from datasets import load_dataset

        ds = load_dataset("hackaprompt/hackaprompt-dataset", split="train")
    except Exception:
        return EvalSet(name="hackaprompt/direct", texts=[], labels=[])
    pos = []
    for r in ds:
        text = r.get("prompt") or r.get("user_input") or r.get("text")
        if isinstance(text, str) and text.strip():
            pos.append(text)
        if len(pos) >= m:
            break
    neg = _benign_pool(len(pos))
    return _mk("hackaprompt/direct", pos, neg, m)


# --------------------------------------------------------------------------- #
# Tensor Trust — prompt-injection attacks vs benign access codes
# --------------------------------------------------------------------------- #
_TENSORTRUST_FILES = [
    "benchmarks/hijacking-robustness/v1/hijacking_robustness_dataset.jsonl",
    "benchmarks/extraction-robustness/v1/extraction_robustness_dataset.jsonl",
]


def load_tensortrust(limit: int | None = None) -> EvalSet:
    m = limit or 400
    try:
        from datasets import load_dataset

        ds = load_dataset("qxcv/tensor-trust", data_files=_TENSORTRUST_FILES, split="train")
    except Exception:
        return EvalSet(name="tensortrust/direct", texts=[], labels=[])
    pos, neg = [], []
    for r in ds:
        atk = r.get("attack")
        benign = r.get("access_code")
        if isinstance(atk, str) and atk.strip():
            pos.append(atk)
        if isinstance(benign, str) and benign.strip():
            neg.append(benign)
        if len(pos) >= m and len(neg) >= m:
            break
    if not neg:
        neg = _benign_pool(len(pos) or m)
    return _mk("tensortrust/direct", pos, neg, m)


# Pooled keys + per-category splits for per-surface recall. Scored by
# scripts/eval_indirect.py; kept separate from the direct BENCHMARK_LOADERS.
# --------------------------------------------------------------------------- #
# Quadrat-IPI — injection planted in long real documents (mail / web / report)
# --------------------------------------------------------------------------- #
# What it adds to this axis: the other five sets here are agent scaffolding — JSON
# tool results, poisoned tool outputs, prompt-hacking games — and their benign side is
# a few hundred matched records per set. This one is ordinary prose a RAG pipeline
# would retrieve: Enron mail, FineWeb and CNN/DM pages, BillSum and GovReport, 63 000
# clean documents against 16 800 injections spread over a fixed 92-cell grid of
# family x action.
#
# NOT TWINNED, and the difference matters for how a result reads. BIPIA above pairs each
# document with its own injected copy, so a rate is measured against the same prose. Here
# the two sides are drawn from the same six corpora and the same three carrier types but
# from DISJOINT documents: no clean row is the twin of an injected one. What that buys is
# size — enough clean prose to place a threshold at 0.1% instead of extrapolating to it —
# and what it costs is that the benign<->injected gap is a distribution comparison rather
# than a per-document one.
#
# Licence ODC-BY 1.0 on the database, per-row source terms for the carrier text. The
# injections are generated rather than collected, so none of them is recycled from another
# benchmark, and a canary string ships with the corpus.
# PINNED TO A REVISION, unlike the sets above. BIPIA and Z-Edgar are cloned from main and
# drift with whatever their authors push; a number recomputed from committed scores then
# describes rows nobody can identify. Quadrat-IPI is published as a git repository on the
# Hub with a tag per release, and a released tag is never rewritten - an edit after
# publication opens the next version instead. So the tag below is what the committed scores
# were taken on, and it keeps meaning that.
#
# When a new release ships, bumping this constant is a PR of its own: it changes the rows,
# so the affected results have to be regenerated with it rather than alongside it.
_QUADRAT_REPO = "mihailgribov/quadrat-ipi"
_QUADRAT_REV = "v1.0.2"


def load_quadrat(
    limit: int | None = None, carrier: str | None = None, revision: str = _QUADRAT_REV
) -> EvalSet:
    """carrier=None pools all three; or one of email/web/doc.

    revision defaults to the pinned tag; pass "main" to track the newest release instead.
    """
    m = limit or 400
    name = f"quadrat/{carrier}" if carrier else "quadrat/indirect"
    try:
        from datasets import load_dataset
    except ImportError:
        logger.warning("datasets not installed — skipping Quadrat-IPI")
        return EvalSet(name=name, texts=[], labels=[])
    try:
        ds = load_dataset(_QUADRAT_REPO, revision=revision)
    except Exception as exc:
        logger.warning("Quadrat-IPI load failed: %s", exc)
        return EvalSet(name=name, texts=[], labels=[])

    def take(split: str) -> list[str]:
        rows = ds[split]
        # Deterministic and stratified by carrier: taking the head of the file would hand
        # back one corpus, because the release is written corpus by corpus.
        out: dict[str, list[str]] = {}
        for r in rows:
            if carrier and r.get("host_type") != carrier:
                continue
            out.setdefault(r.get("host_type") or "doc", []).append(r["text"])
            if sum(len(v) for v in out.values()) >= m * 4:
                break
        picked: list[str] = []
        for i in range(m):
            for key in sorted(out):
                if i < len(out[key]) and len(picked) < m:
                    picked.append(out[key][i])
        return picked

    pos, neg = take("injected"), take("clean")
    if not pos or not neg:
        return EvalSet(name=name, texts=[], labels=[])
    return _mk(name, pos, neg, m)


INDIRECT_LOADERS = {
    "zedgar": load_zedgar,
    "bipia": load_bipia,
    "bipia_email": partial(load_bipia, domain="email"),
    "bipia_table": partial(load_bipia, domain="table"),
    "bipia_code": partial(load_bipia, domain="code"),
    "injecagent": load_injecagent,
    "injecagent_dh": partial(load_injecagent, category="dh"),
    "injecagent_ds": partial(load_injecagent, category="ds"),
    "agentdojo": load_agentdojo,
    "hackaprompt": load_hackaprompt,  # gated
    "tensortrust": load_tensortrust,
    "quadrat": load_quadrat,
    "quadrat_email": partial(load_quadrat, carrier="email"),
    "quadrat_web": partial(load_quadrat, carrier="web"),
    "quadrat_doc": partial(load_quadrat, carrier="doc"),
}
