"""Unit tests for the scoring path.

Deliberately offline: no model or dataset is downloaded. The windowing tests
build a bare `TransformersRunner` via `object.__new__` and set only the
attributes the windowing logic reads, so the chunking arithmetic is tested
without a 500 MB download on every run.
"""

from __future__ import annotations

import pytest

from pidbench.runners import TransformersRunner, _batches, _smooth_max


# ── smooth-max aggregation ────────────────────────────────────────────────
def test_smooth_max_degenerate_cases():
    assert _smooth_max([]) == 0.0
    assert _smooth_max([0.7]) == pytest.approx(0.7)


def test_smooth_max_is_bounded_by_the_maximum():
    """The property the aggregator exists for: a long benign document must not
    score higher than a short one merely for having more windows."""
    for scores in ([0.9], [0.9, 0.02], [0.9] + [0.02] * 63, [0.1] * 40):
        assert _smooth_max(scores) <= max(scores) + 1e-9


def test_quiet_windows_cannot_raise_a_score():
    alone = _smooth_max([0.9])
    padded = _smooth_max([0.9] + [0.02] * 63)
    assert padded <= alone + 1e-9
    assert padded > 0.5, "one confident window must still dominate 63 quiet ones"


def test_low_temperature_approaches_max_high_temperature_approaches_mean():
    scores = [0.9, 0.1, 0.1, 0.1]
    assert _smooth_max(scores, 0.001) == pytest.approx(max(scores), abs=1e-6)
    hot = _smooth_max(scores, 50.0)
    assert hot == pytest.approx(sum(scores) / len(scores), abs=0.05)


def test_smooth_max_is_monotone_in_the_top_score():
    lo = _smooth_max([0.3] + [0.02] * 10)
    hi = _smooth_max([0.8] + [0.02] * 10)
    assert hi > lo


# ── windowing ─────────────────────────────────────────────────────────────
class _FakeTok:
    """Minimal tokenizer: one id per whitespace token, [2] ... [1] affixes."""

    def __init__(self, n_tokens: int):
        self._n = n_tokens

    def __call__(self, text, add_special_tokens=False):
        ids = list(range(self._n))
        return {"input_ids": [2, *ids, 1] if add_special_tokens else ids}


def _runner(n_tokens: int, max_length: int = 512, max_windows: int = 32):
    r = object.__new__(TransformersRunner)
    r.tokenizer = _FakeTok(n_tokens)
    r.max_length = max_length
    r.chunk_max_windows = max_windows
    r.chunk_stride = max(1, max_length - max(96, max_length // 8))
    r._affixes = None
    return r


def test_affixes_are_probed_from_the_tokenizer():
    assert _runner(5)._special_affixes() == ([2], [1])


def test_short_text_is_a_single_window():
    r = _runner(100, max_length=512)
    assert len(r._window_ids("x")) == 1


def test_no_window_exceeds_the_model_window():
    r = _runner(50_000, max_length=512)
    assert all(len(w) <= r.max_length for w in r._window_ids("x"))


def test_windows_cover_the_whole_input():
    """Truncation's failure mode is a payload past the window. Every token must
    appear in at least one window when the cap is not hit."""
    n = 4000
    r = _runner(n, max_length=512, max_windows=1000)
    seen: set[int] = set()
    for w in r._window_ids("x"):
        seen |= set(w[1:-1])  # strip affixes
    assert seen == set(range(n))


def test_window_cap_is_respected_and_keeps_both_ends():
    r = _runner(200_000, max_length=512, max_windows=32)
    windows = r._window_ids("x")
    assert len(windows) <= 32
    assert windows[0][1] == 0, "first window must be kept"
    assert windows[-1][-2] == 199_999, "last window must be kept (no head bias)"


def test_stride_leaves_a_payload_sized_overlap():
    for window in (512, 2048, 8192):
        r = _runner(100, max_length=window)
        assert window - r.chunk_stride >= 96


# ── batching helper ───────────────────────────────────────────────────────
def test_batches_partitions_without_loss():
    items = [str(i) for i in range(10)]
    out = list(_batches(items, 3))
    assert [len(b) for b in out] == [3, 3, 3, 1]
    assert [x for b in out for x in b] == items
