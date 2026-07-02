"""Near-duplicate detection between eval conversations and a training corpus.

The honesty backstop for the never-trained wall: a held-out eval set is only
honest if its rendered conversations don't appear in the detector's training
data. This builds a token-set index over the corpus and, for any eval text,
finds the best-overlapping corpus doc — so the multi-turn dedup gate can drop
contaminated rows and publish the overlap rate.

Method (MinHash-lite): normalize -> token sets -> inverted index over
*distinctive* tokens (document frequency <= ``df_max``). For a query, gather
corpus candidates that share >= ``min_shared`` distinctive tokens and return the
best Jaccard. Near-exact (>= ~0.9) means the text is effectively present in the
corpus; a fuzzy band (~0.6) flags paraphrase worth manual review.

Corpus files are ``{"text": ...}`` JSONL (the training corpus format). Text-only
— no labels needed. Cheap enough to run over a ~1M-row corpus on CPU.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

_WORD = re.compile(r"[a-z0-9]+")


def norm_tokens(s: str) -> list[str]:
    return _WORD.findall(s.lower())


def fingerprint(s: str) -> str:
    """Stable fingerprint of the normalized token stream (for drop manifests —
    no raw text is stored)."""
    return hashlib.sha1(" ".join(norm_tokens(s)).encode()).hexdigest()


class CorpusIndex:
    def __init__(self, df_max: int = 400, min_shared: int = 4, min_token_len: int = 3):
        self.df_max = df_max
        self.min_shared = min_shared
        self.min_token_len = min_token_len
        self._tok: list[set[str]] = []
        self._src: list[str] = []
        self._distinctive: set[str] = set()
        self._inv: dict[str, list[int]] = defaultdict(list)

    @classmethod
    def from_jsonl(cls, paths: list[str | Path], text_key: str = "text", **kw) -> "CorpusIndex":
        idx = cls(**kw)
        texts, srcs = [], []
        for p in paths:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    t = r.get(text_key)
                    if t:
                        texts.append(t)
                        srcs.append(r.get("source", "?"))
        idx.build(texts, srcs)
        return idx

    def build(self, texts: list[str], sources: list[str] | None = None) -> "CorpusIndex":
        self._tok = [set(norm_tokens(t)) for t in texts]
        self._src = sources or ["?"] * len(texts)
        df: Counter = Counter()
        for ts in self._tok:
            df.update(ts)
        self._distinctive = {
            tok for tok, c in df.items() if c <= self.df_max and len(tok) >= self.min_token_len
        }
        self._inv = defaultdict(list)
        for i, ts in enumerate(self._tok):
            for tok in ts & self._distinctive:
                self._inv[tok].append(i)
        return self

    def __len__(self) -> int:
        return len(self._tok)

    def best_match(self, text: str) -> tuple[float, int]:
        """Return (best Jaccard, corpus doc index) for ``text``; (0.0, -1) if none."""
        st = set(norm_tokens(text))
        if len(st) < 3:
            return 0.0, -1
        cand: Counter = Counter()
        for tok in st & self._distinctive:
            for i in self._inv.get(tok, ()):
                cand[i] += 1
        best_j, best_i = 0.0, -1
        for i, shared in cand.items():
            if shared < self.min_shared:
                continue
            cs = self._tok[i]
            jac = len(st & cs) / len(st | cs)
            if jac > best_j:
                best_j, best_i = jac, i
        return best_j, best_i

    def source_of(self, i: int) -> str:
        return self._src[i] if 0 <= i < len(self._src) else "?"
