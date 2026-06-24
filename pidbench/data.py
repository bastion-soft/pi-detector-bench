from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvalSet:
    name: str
    texts: list[str]
    labels: list[int]

    def __len__(self) -> int:
        return len(self.texts)

    @property
    def n_attack(self) -> int:
        return sum(1 for label in self.labels if label == 1)

    @property
    def n_benign(self) -> int:
        return sum(1 for label in self.labels if label == 0)


_BENCHMARK_LABEL_TO_INT = {
    "jailbreak": 1,
    "benign": 0,
    "injection": 1,
    "safe": 0,
    "attack": 1,
}


def load_rogue_benchmark(limit: int | None = None) -> EvalSet:
    """Held-out benchmark. Two-class: jailbreak vs benign.

    Source: rogue-security/prompt-injections-benchmark.
    """
    from datasets import load_dataset  # type: ignore[import-not-found]

    ds = load_dataset("rogue-security/prompt-injections-benchmark")
    split_name = "train" if "train" in ds else next(iter(ds.keys()))
    rows = ds[split_name]

    texts: list[str] = []
    labels: list[int] = []
    for row in rows:
        text = row.get("text") or row.get("prompt") or ""
        if not text or not text.strip():
            continue
        raw_label = row.get("label")
        label = _coerce_label(raw_label)
        if label is None:
            continue
        texts.append(text)
        labels.append(label)

    if limit:
        texts = texts[:limit]
        labels = labels[:limit]

    return EvalSet(name="rogue-security/prompt-injections-benchmark", texts=texts, labels=labels)


def load_xtram1_test(limit: int | None = None) -> EvalSet:
    """xTRam1 test split — excluded from v2 training via HOLDOUT_TEST_SPLIT.

    Different distribution from train (held-out by the dataset authors).
    protectai trained on it pre-2024, so it inflates protectai's apparent score.
    """
    from datasets import load_dataset

    ds = load_dataset("xTRam1/safe-guard-prompt-injection")
    rows = ds["test"]
    texts = [r["text"] for r in rows if r.get("text")]
    labels = [int(r["label"]) for r in rows if r.get("text")]
    if limit:
        texts = texts[:limit]
        labels = labels[:limit]
    return EvalSet(name="xTRam1/test", texts=texts, labels=labels)


def load_slabs_test(limit: int | None = None) -> EvalSet:
    """S-Labs test split — excluded from v2 training via HOLDOUT_TEST_SPLIT."""
    from datasets import load_dataset

    ds = load_dataset("S-Labs/prompt-injection-dataset")
    rows = ds["test"]
    texts = [r["text"] for r in rows if r.get("text")]
    labels = [int(r["label"]) for r in rows if r.get("text")]
    if limit:
        texts = texts[:limit]
        labels = labels[:limit]
    return EvalSet(name="S-Labs/test", texts=texts, labels=labels)


def load_deepset_test(limit: int | None = None) -> EvalSet:
    """deepset test split — excluded from v2 training via HOLDOUT_TEST_SPLIT."""
    from datasets import load_dataset

    ds = load_dataset("deepset/prompt-injections")
    rows = ds["test"]
    texts: list[str] = []
    labels: list[int] = []
    for r in rows:
        if r.get("text"):
            texts.append(r["text"])
            labels.append(int(r["label"]))
    if limit:
        texts = texts[:limit]
        labels = labels[:limit]
    return EvalSet(name="deepset/test", texts=texts, labels=labels)


def load_jailbreakbench(limit: int | None = None) -> EvalSet:
    """JailbreakBench JBB-Behaviors — public JailbreakBench eval set.

    100 harmful behavior goals + 100 benign — covers a different attack
    style than rogue (harmful content elicitation rather than prompt
    injection per se). Useful complement.
    """
    from datasets import load_dataset

    ds = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors")
    texts: list[str] = []
    labels: list[int] = []
    for split_name in ds:
        for row in ds[split_name]:
            text = row.get("Goal") or ""
            if not text:
                continue
            # The dataset has separate harmful (100) and benign (100) configs;
            # in the "behaviors" combined view, split name indicates which.
            label = 1 if split_name == "harmful" else 0
            texts.append(text)
            labels.append(label)
    if limit:
        texts = texts[:limit]
        labels = labels[:limit]
    return EvalSet(name="JailbreakBench", texts=texts, labels=labels)


# Registry for benchmark suite runner
BENCHMARK_LOADERS = {
    "rogue": load_rogue_benchmark,
    "xtram1_test": load_xtram1_test,
    "slabs_test": load_slabs_test,
    "deepset_test": load_deepset_test,
    "jailbreakbench": load_jailbreakbench,
}


def _coerce_label(raw: object) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return 1 if raw else 0
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str):
        return _BENCHMARK_LABEL_TO_INT.get(raw.strip().lower())
    return None
