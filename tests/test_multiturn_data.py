"""Multi-turn loaders: turn structure of the MHJ comparison, cross-step padding.

Offline: the MHJ CSV and the WildChat/LMSYS benign pool are replaced with small
synthetic stand-ins shaped like the real sources (MHJ: user turns only; benign
pool: alternating user/assistant turns, as in WildChat).
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pidbench import multiturn_data as mt


def _benign_pool(n: int = 60) -> list[list[tuple[str, str]]]:
    return [
        [
            ("user", f"benign question {i} part one about cooking pasta"),
            ("assistant", f"benign answer {i} with a long explanation " * 3),
            ("user", f"benign follow-up {i} on sauces"),
            ("assistant", f"benign answer {i} again"),
        ]
        for i in range(n)
    ]


@pytest.fixture
def fake_sources(monkeypatch, tmp_path):
    pd = pytest.importorskip("pandas")
    huggingface_hub = pytest.importorskip("huggingface_hub")

    rows = []
    for i in range(40):
        rows.append(
            {
                "message_0": json.dumps({"role": "system", "body": "scaffold"}),
                "message_1": json.dumps({"role": "user", "body": f"red-team opener {i}"}),
                "message_2": json.dumps({"role": "user", "body": f"red-team escalation {i}"}),
                "message_3": json.dumps({"role": "user", "body": f"red-team payload {i}"}),
            }
        )
    csv = tmp_path / "mhj.csv"
    pd.DataFrame(rows).to_csv(csv, index=False)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", lambda *a, **k: str(csv))
    pool = _benign_pool()
    monkeypatch.setattr(mt, "_benign_multiturn", lambda n: pool[:n])
    return pool


def _has_assistant(text: str) -> int:
    return int("[ASSISTANT]" in text)


def test_has_assistant_turn_no_longer_separates_mhj_labels(fake_sources):
    """Before the 2026-11 revision this feature alone gave AUC 1.0 (attacks had no
    assistant turns, every benign conversation did). It must now be constant."""
    from sklearn.metrics import roc_auc_score

    es, meta = mt.load_mhj_mt()
    labels = np.asarray(es.labels)
    assert labels.sum() and (labels == 0).sum(), "need both classes"
    feat = np.asarray([_has_assistant(t) for t in es.texts])
    assert feat.sum() == 0, "no MHJ-comparison row may contain an assistant turn"
    assert roc_auc_score(labels, feat) == pytest.approx(0.5)


def test_mhj_rows_are_user_only_on_both_sides(fake_sources):
    es, meta = mt.load_mhj_mt()
    for text, m in zip(es.texts, meta, strict=True):
        tags = [line.split("]")[0] + "]" for line in text.splitlines() if line.startswith("[")]
        assert set(tags) == {"[USER]"}
        assert m.n_turns >= 2
    # injection turn indexes the user-only rendering (the last user turn)
    for m in meta:
        if m.injected:
            assert m.injection_turn == m.n_turns - 1
            assert m.chars_after == 0


def test_mhj_benign_rendering_does_not_mutate_the_shared_pool(fake_sources):
    before = [list(c) for c in fake_sources]
    mt.load_mhj_mt()
    assert fake_sources == before


def test_cross_step_depth_padding_still_uses_full_benign_turns(monkeypatch):
    """The cross-step sets (InjecAgent/AgentDojo/ASB) pad with the same benign pool;
    the MHJ user-only rendering must not leak into that padding."""
    pool = _benign_pool()
    monkeypatch.setattr(mt, "_benign_multiturn", lambda n: pool[:n])
    trace = [("user", "book a flight"), ("assistant", "Calling tool: x"), ("tool", "ok")]
    out = mt._depth_expand([(trace, 1, "test", 2)], targets=[0, 512])
    padded = out[-1][0]
    assert any(role == "assistant" for role, _ in padded[len(trace) :])


def test_removed_sets_are_not_registered():
    assert set(mt.MULTITURN_LOADERS_MT) == {"injecagent", "agentdojo", "asb", "mhj"}
    assert not hasattr(mt, "load_cosafe_mt")
    assert not hasattr(mt, "load_agentharm_mt")


def test_jailbreakbench_is_not_registered():
    from pidbench.data import BENCHMARK_LOADERS

    assert "jailbreakbench" not in BENCHMARK_LOADERS
