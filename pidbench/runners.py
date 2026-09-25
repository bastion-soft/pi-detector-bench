from __future__ import annotations

import math
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
        max_length: int | None = 512,
        batch_size: int = 16,
        device: str | None = None,
        name: str | None = None,
        truncation_side: str = "right",
        chunk: bool = False,
        chunk_temperature: float = 0.1,
        chunk_max_windows: int = 32,
    ) -> None:
        """``max_length=None`` auto-detects the model's own context window from
        ``config.max_position_embeddings`` (clamped to a sane range) — so a
        long-context detector isn't silently capped and a short one isn't
        over-fed. Pass an int to force a fixed window for all models.

        ``truncation_side="left"`` keeps the most RECENT tokens (drops the oldest)
        — the deployment-faithful choice for multi-turn conversations, where a
        real filter sees the latest turns. The default ``"right"`` keeps the start
        (fine for single-message direct/indirect sets).

        ``chunk=True`` scores an input longer than the window as OVERLAPPING
        WINDOWS aggregated with a smooth-max, instead of truncating it. This is a
        HARNESS-WIDE switch, never a per-model one: it is set once for a run and
        applied to every entry, at each model's own window. Truncation silently
        zeroes recall for any payload past the window — a property of the harness,
        not of the detector — and chunking is a generic inference strategy that
        any sequence classifier supports, so offering it to one model and not
        another would be exactly the special-casing this benchmark refuses. It is
        off by default so published numbers stay comparable to earlier runs; when
        on, the extra forward passes are charged to the reported latency."""
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
        self.batch_size = batch_size

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        # keep-recent truncation for multi-turn (drop oldest turns, not newest)
        self.tokenizer.truncation_side = truncation_side
        if self.tokenizer.pad_token is None:
            # Qwen / Llama-style decoders don't define a pad token by default.
            # Reusing eos for padding is the conventional fix and won't affect
            # classification logits since attention_mask zeros out padding.
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device)
        if self.model.config.pad_token_id is None and self.tokenizer.pad_token_id is not None:
            self.model.config.pad_token_id = self.tokenizer.pad_token_id
        self.model.eval()

        # Resolve the context window. None -> the model's own, from config; else fixed.
        # Clamp against absurd config sentinels (some models set 1e30 / 0).
        if max_length is None:
            mpe = getattr(self.model.config, "max_position_embeddings", 0) or 0
            max_length = mpe if 16 <= mpe <= 16384 else 512
        self.max_length = int(max_length)

        # Auto-load temperature scalar if the model repo ships `temperature.json`.
        # Models that ship one get calibrated probability output; models that don't
        # default to identity (T=1.0, no-op). Applied uniformly to every model.
        self.temperature = _load_temperature(model_id)

        self._affixes: tuple[list[int], list[int]] | None = None
        self.chunk = bool(chunk)
        self.chunk_temperature = float(chunk_temperature)
        self.chunk_max_windows = int(chunk_max_windows)
        # Overlap exists so a payload straddling a boundary lands wholly inside
        # some window, so it scales with the PAYLOAD, not the window — hence a
        # floor rather than a pure ratio.
        self.chunk_stride = max(1, self.max_length - max(96, self.max_length // 8))

    def score_batch(self, texts: list[str]) -> RunnerOutput:
        if self.chunk:
            return self._score_batch_chunked(texts)
        return self._score_batch_truncated(texts)

    def _score_batch_truncated(self, texts: list[str]) -> RunnerOutput:
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

    def _window_ids(self, text: str) -> list[list[int]]:
        """Token-id windows for one text, with special tokens applied per model.

        ``build_inputs_with_special_tokens`` is used rather than hardcoding
        cls/sep, because this harness also scores decoder-based classifiers that
        define neither.
        """
        ids = self.tokenizer(text, add_special_tokens=False)["input_ids"]
        prefix, suffix = self._special_affixes()
        body = max(1, self.max_length - len(prefix) - len(suffix))
        stride = max(1, min(self.chunk_stride, body))
        if len(ids) <= body:
            windows = [ids]
        else:
            windows = []
            i = 0
            while i < len(ids):
                windows.append(ids[i : i + body])
                if i + body >= len(ids):
                    break
                i += stride
        # Bound worst-case latency on pathological inputs. Keep the FIRST and LAST
        # windows and sample the middle evenly: dropping the tail would recreate
        # the head-truncation bias this path exists to remove, and payloads
        # concentrate at the extremes.
        if len(windows) > self.chunk_max_windows:
            keep = {0, len(windows) - 1}
            n_mid = self.chunk_max_windows - 2
            if n_mid > 0:
                step = (len(windows) - 2) / n_mid
                keep |= {1 + int(i * step) for i in range(n_mid)}
            windows = [windows[i] for i in sorted(keep)]
        prefix, suffix = self._special_affixes()
        return [prefix + w + suffix for w in windows]

    def _special_affixes(self) -> tuple[list[int], list[int]]:
        """The special tokens this tokenizer wraps a sequence in, as (prefix, suffix).

        Derived by probing rather than by calling
        ``build_inputs_with_special_tokens``, which transformers 5.x dropped from
        the fast-tokenizer backend. Probing also covers decoder tokenizers that add
        nothing, and models with unusual affixes, without special-casing any of them.
        """
        if self._affixes is not None:
            return self._affixes
        probe = "x"
        with_sp = list(self.tokenizer(probe, add_special_tokens=True)["input_ids"])
        without = list(self.tokenizer(probe, add_special_tokens=False)["input_ids"])
        prefix: list[int] = []
        suffix: list[int] = []
        if without and len(with_sp) >= len(without):
            for i in range(len(with_sp) - len(without) + 1):
                if with_sp[i : i + len(without)] == without:
                    prefix, suffix = with_sp[:i], with_sp[i + len(without) :]
                    break
        self._affixes = (prefix, suffix)
        return self._affixes

    def _score_batch_chunked(self, texts: list[str]) -> RunnerOutput:
        import torch  # type: ignore[import-not-found]

        scores: list[float] = []
        latencies: list[float] = []
        pad_id = self.tokenizer.pad_token_id or 0

        for batch in _chunks(texts, self.batch_size):
            t0 = time.perf_counter()
            per_doc = [self._window_ids(t) for t in batch]
            flat = [w for doc in per_doc for w in doc]

            win_scores: list[float] = []
            for i in range(0, len(flat), self.batch_size):
                grp = flat[i : i + self.batch_size]
                mx = max(len(w) for w in grp)
                ids = torch.tensor([w + [pad_id] * (mx - len(w)) for w in grp]).to(self.device)
                att = torch.tensor([[1] * len(w) + [0] * (mx - len(w)) for w in grp]).to(
                    self.device
                )
                with torch.no_grad():
                    logits = self.model(input_ids=ids, attention_mask=att).logits / self.temperature
                probs = torch.softmax(logits, dim=-1)
                if isinstance(self.attack_label_id, list):
                    win_scores += probs[:, self.attack_label_id].sum(dim=-1).cpu().tolist()
                else:
                    win_scores += probs[:, self.attack_label_id].cpu().tolist()

            pos = 0
            for doc in per_doc:
                scores.append(_smooth_max(win_scores[pos : pos + len(doc)], self.chunk_temperature))
                pos += len(doc)

            # Charge the windowing cost to latency, matching the truncated path's
            # batch_latency / batch_size convention.
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.extend([elapsed_ms / max(len(batch), 1)] * len(batch))

        return RunnerOutput(scores=scores, latencies_ms=latencies)


def _smooth_max(scores: list[float], temperature: float = 0.1) -> float:
    """Softmax-weighted average of window scores.

    Bounded above by ``max(scores)``, so adding quiet windows can never raise a
    document's score — a plain logsumexp grows with window count and would make a
    long benign document outrank a short one for being long. As the temperature
    falls it converges to the max, so one confident window in a long document
    still decides it; as it rises it accumulates weak agreement across windows.
    """
    if not scores:
        return 0.0
    if len(scores) == 1:
        return float(scores[0])
    t = max(temperature, 1e-6)
    mx = max(scores)
    exps = [math.exp((v - mx) / t) for v in scores]
    denom = sum(exps) or 1.0
    return float(sum(w * v for w, v in zip(exps, scores, strict=True)) / denom)


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
