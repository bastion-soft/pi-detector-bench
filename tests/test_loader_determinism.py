"""BIPIA / InjecAgent loaders must not depend on filesystem glob order."""

from __future__ import annotations

import glob as glob_mod
import json

import pytest

import pidbench.indirect_data as ind
import pidbench.multiturn_data as mt


def _ia_files(root):
    d = root / "InjecAgent" / "data"
    d.mkdir(parents=True)
    for cat in ("dh", "ds"):
        rows = [
            {
                "Tool Response Template": f"{{'content': '<Attacker Instruction>', 'id': '{cat}{i}'}}",
                "Attacker Instruction": f"{cat} attack {i}",
                "User Instruction": f"user task {cat} {i}",
                "User Tool": "Tool",
                "Tool Response": f"IMPORTANT!!! adhere to the following instruction: {cat} attack {i}",
            }
            for i in range(5)
        ]
        (d / f"test_cases_{cat}_enhanced.json").write_text(json.dumps(rows))


def _bipia_files(root):
    b = root / "BIPIA" / "benchmark"
    for dom in ("code", "email", "table"):
        (b / dom).mkdir(parents=True)
        (b / dom / "test.jsonl").write_text(
            "\n".join(json.dumps({"context": f"{dom} doc {i}"}) for i in range(3))
        )
    (b / "text_attack_test.json").write_text(json.dumps({"a": ["atk1", "atk2"], "b": ["atk3"]}))


@pytest.fixture
def reversed_glob(monkeypatch):
    real = glob_mod.glob

    def rev(*a, **k):
        return sorted(real(*a, **k), reverse=True)

    def fwd(*a, **k):
        return sorted(real(*a, **k))

    def use(fn):
        monkeypatch.setattr(glob_mod, "glob", fn)

    return use, rev, fwd


@pytest.mark.parametrize(
    "make,load",
    [
        (_ia_files, lambda: ind.load_injecagent()),
        (_bipia_files, lambda: ind.load_bipia()),
    ],
)
def test_indirect_loaders_ignore_glob_order(tmp_path, monkeypatch, reversed_glob, make, load):
    make(tmp_path)
    monkeypatch.chdir(tmp_path)
    use, rev, fwd = reversed_glob
    use(fwd)
    a = load()
    use(rev)
    b = load()
    assert a.texts and a.texts == b.texts and a.labels == b.labels


def test_injecagent_mt_ignores_glob_order(tmp_path, monkeypatch, reversed_glob):
    _ia_files(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mt, "_benign_multiturn", lambda n: [])  # no depth padding offline
    use, rev, fwd = reversed_glob
    use(fwd)
    a, _ = mt.load_injecagent_mt()
    use(rev)
    b, _ = mt.load_injecagent_mt()
    assert a.texts and a.texts == b.texts
