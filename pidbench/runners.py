from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass
class RunnerOutput:
    scores: list[float]
    latencies_ms: list[float]


class Runner(Protocol):
    name: str

    def score_batch(self, texts: list[str]) -> RunnerOutput: ...


class TransformersRunner:
    """Runs a HuggingFace AutoModelForSequenceClassification baseline.

    Performs batched inference and reports per-item latency as
    batch_latency / batch_size, which approximates what users see in batched
    serving.
    """

    def __init__(
        self,
        model_id: str,
        attack_label_id: int | list[int] = 1,
        max_length: int = 512,
        batch_size: int = 16,
        device: str | None = None,
        name: str | None = None,
    ) -> None:
        """`attack_label_id` may be an int (single class) or a list of ints
        (sum of softmax probabilities across those classes — useful for
        multi-class detectors like Meta Prompt-Guard where both
        INJECTION (1) and JAILBREAK (2) are "attack" in our binary frame).
        """
        import torch  # type: ignore[import-not-found]
        from transformers import (  # type: ignore[import-not-found]
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        self.model_id = model_id
        self.name = name or model_id
        self.attack_label_id = attack_label_id
        self.max_length = max_length
        self.batch_size = batch_size

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        if self.tokenizer.pad_token is None:
            # Qwen / Llama-style decoders don't define a pad token by default.
            # Reusing eos for padding is the conventional fix and won't affect
            # classification logits since attention_mask zeros out padding.
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device)
        if self.model.config.pad_token_id is None and self.tokenizer.pad_token_id is not None:
            self.model.config.pad_token_id = self.tokenizer.pad_token_id
        self.model.eval()

        # Auto-load temperature scalar if the model repo ships `temperature.json`.
        # Models that ship one get calibrated probability output; models that don't
        # default to identity (T=1.0, no-op). Applied uniformly to every model.
        self.temperature = _load_temperature(model_id)

    def score_batch(self, texts: list[str]) -> RunnerOutput:
        import torch  # type: ignore[import-not-found]

        scores: list[float] = []
        latencies: list[float] = []

        for batch in _chunks(texts, self.batch_size):
            t0 = time.perf_counter()
            enc = self.tokenizer(
                list(batch),
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)
            with torch.no_grad():
                logits = self.model(**enc).logits / self.temperature
            probs = torch.softmax(logits, dim=-1)
            if isinstance(self.attack_label_id, list):
                attack_probs = probs[:, self.attack_label_id].sum(dim=-1).cpu().tolist()
            else:
                attack_probs = probs[:, self.attack_label_id].cpu().tolist()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            per_item = elapsed_ms / max(len(batch), 1)

            scores.extend(attack_probs)
            latencies.extend([per_item] * len(batch))

        return RunnerOutput(scores=scores, latencies_ms=latencies)


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _load_temperature(model_id: str) -> float:
    """Try to fetch `temperature.json` from a HuggingFace model repo.

    Returns the temperature scalar if present, else 1.0 (identity — no
    calibration applied). Logits are divided by this value before softmax.

    Some detectors ship a fitted temperature; many don't. Applied uniformly.
    """
    import json

    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(repo_id=model_id, filename="temperature.json")
        return float(json.loads(open(path).read())["temperature"])
    except Exception:
        return 1.0
