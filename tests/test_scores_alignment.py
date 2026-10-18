"""Score-file alignment, the pending re-score state, and the rebuild refusing
misaligned files. Offline: synthetic score files in a temp dir."""

from __future__ import annotations

import json

import pytest

from pidbench import scores_io
from pidbench.scores_io import (
    LOADER_REVISION,
    MisalignedScoresError,
    check_alignment,
    dump_scores,
    load_all_scores,
    rows_fingerprint,
)


def _rec(runner, dataset, scores, labels, **extra):
    return {
        "runner": runner,
        "dataset": dataset,
        "kind": "attack",
        "scores": scores,
        "labels": labels,
        **extra,
    }


def test_fingerprint_is_order_sensitive():
    assert rows_fingerprint(["a", "b"], [1, 0]) != rows_fingerprint(["b", "a"], [0, 1])
    assert rows_fingerprint(["a", "b"], [1, 0]) == rows_fingerprint(["a", "b"], [1, 0])
    assert rows_fingerprint(["a"], [1]) != rows_fingerprint(["a"], [0])


def test_dump_stamps_revision_and_fingerprint(tmp_path):
    p = dump_scores(tmp_path, "m", "rogue", "attack", [0.1, 0.9], [0, 1], texts=["x", "y"])
    d = json.loads(p.read_text())
    assert d["loader_revision"] == LOADER_REVISION
    assert d["rows_sha256"] == rows_fingerprint(["x", "y"], [0, 1])
    assert "x" not in p.read_text(), "prompt text must never be written"


def test_dump_refuses_length_mismatch(tmp_path):
    with pytest.raises(MisalignedScoresError):
        dump_scores(tmp_path, "m", "d", "attack", [0.1, 0.9], [0])
    with pytest.raises(MisalignedScoresError):
        dump_scores(tmp_path, "m", "d", "attack", [0.1, 0.9], [0, 1], texts=["only one"])


def test_label_disagreement_between_models_is_refused():
    recs = [_rec("a", "rogue", [0.1, 0.9], [0, 1]), _rec("b", "rogue", [0.1, 0.9], [1, 0])]
    with pytest.raises(MisalignedScoresError):
        check_alignment(recs)


def test_fingerprint_disagreement_between_models_is_refused():
    recs = [
        _rec("a", "rogue", [0.1, 0.9], [0, 1], rows_sha256="aaa"),
        _rec("b", "rogue", [0.1, 0.9], [0, 1], rows_sha256="bbb"),
    ]
    with pytest.raises(MisalignedScoresError):
        check_alignment(recs)


def test_meta_length_mismatch_is_refused():
    with pytest.raises(MisalignedScoresError):
        check_alignment([_rec("a", "x", [0.1, 0.9], [0, 1], meta=[{}])])


def test_pre_revision_file_for_a_changed_set_is_pending_not_used():
    old = _rec("a", "mhj_mt", [0.1, 0.9], [0, 1], meta=[{"scoring": "left_truncated"}] * 2)
    usable, pending = check_alignment([old])
    assert usable == []
    assert ("a", "mhj_mt") in pending


def test_revised_chunked_file_clears_pending():
    new = _rec(
        "a",
        "mhj_mt",
        [0.1, 0.9],
        [0, 1],
        loader_revision=LOADER_REVISION,
        meta=[{"scoring": "chunked_tokens"}] * 2,
    )
    usable, pending = check_alignment([new])
    assert usable == [new] and pending == {}


def test_revised_but_truncated_multiturn_file_stays_pending():
    rec = _rec(
        "a",
        "asb_mt",
        [0.1, 0.9],
        [0, 1],
        loader_revision=LOADER_REVISION,
        meta=[{"scoring": "left_truncated"}] * 2,
    )
    assert check_alignment([rec])[1]


def test_unchanged_sets_stay_usable_without_a_revision_stamp():
    rec = _rec("a", "rogue-security/prompt-injections-benchmark", [0.1, 0.9], [0, 1])
    usable, pending = check_alignment([rec])
    assert usable == [rec] and not pending


# ── the committed score files ─────────────────────────────────────────────
@pytest.mark.parametrize(
    "d", ["results/scores", "results/scores_indirect", "results/scores_multiturn"]
)
def test_committed_score_files_are_aligned_or_explicitly_pending(d):
    """Every committed file is either usable (consistent across detectors) or
    pending a re-score for a documented loader change — never silently misaligned."""
    usable, pending = check_alignment(load_all_scores(d))
    for _, dataset in pending:
        assert dataset in scores_io.ROWS_CHANGED


def test_no_committed_scores_for_removed_sets():
    names = {
        r["dataset"]
        for d in ("results/scores", "results/scores_multiturn")
        for r in load_all_scores(d)
    }
    assert not names & {"JailbreakBench", "cosafe_mt", "agentharm_mt"}


# ── rebuild refuses / marks pending ───────────────────────────────────────
def _write_results(tmp_path, recs, rows):
    sd = tmp_path / "scores_indirect"
    sd.mkdir()
    for r in recs:
        (
            sd / f"{scores_io.slugify(r['runner'])}__{scores_io.slugify(r['dataset'])}.json"
        ).write_text(json.dumps(r))
    (tmp_path / "indirect.json").write_text(json.dumps({"rows": rows}))
    return sd


def _row(runner, key, bench):
    return {
        "benchmark_key": key,
        "runner": runner,
        "benchmark": bench,
        "n_samples": 2,
        "n_attack": 1,
        "n_benign": 1,
        "auc": 1.0,
        "f1": 1.0,
        "precision": 1.0,
        "recall": 1.0,
        "fpr_at_tpr_99": 0.0,
        "fpr_at_tpr_95": 0.0,
        "p50_latency_ms": 1.0,
        "p95_latency_ms": 1.0,
        "total_seconds": 1.0,
    }


def test_rebuild_marks_pending_cells(tmp_path, monkeypatch):
    from scripts import rebuild_results_from_scores as rb

    monkeypatch.setitem(
        scores_io.ROWS_CHANGED, "bipia/indirect", {"revision": "2026-11", "reason": "test"}
    )
    sd = _write_results(
        tmp_path,
        [
            _rec("m", "bipia/indirect", [0.2, 0.8], [0, 1]),
            _rec("m", "zedgar/structured", [0.2, 0.8], [0, 1]),
        ],
        [_row("m", "bipia", "bipia/indirect"), _row("m", "zedgar", "zedgar/structured")],
    )
    rows, order, _, n_pending = rb._rebuild_rows(tmp_path / "indirect.json", str(sd))
    assert n_pending == 1
    by_key = {k: r for k, r in rows}
    assert by_key["bipia"].pending_rescore and by_key["bipia"].auc is None
    assert by_key["zedgar"].pending_rescore is None and by_key["zedgar"].auc == 1.0
    from scripts.eval_indirect import _format_markdown

    md = _format_markdown(rows, order)
    assert "pending re-score" in md


def test_rebuild_refuses_misaligned_files(tmp_path, monkeypatch):
    from scripts import rebuild_results_from_scores as rb

    sd = _write_results(
        tmp_path,
        [
            _rec("a", "zedgar/structured", [0.2, 0.8], [0, 1]),
            _rec("b", "zedgar/structured", [0.2, 0.8], [1, 0]),
        ],
        [_row("a", "zedgar", "zedgar/structured")],
    )
    with pytest.raises(MisalignedScoresError):
        rb._rebuild_rows(tmp_path / "indirect.json", str(sd))


def test_rescore_plan_covers_every_changed_set():
    from scripts.rescore_plan import _RESCORE, plan

    assert set(scores_io.ROWS_CHANGED) <= set(_RESCORE)
    cmds = plan({("m", "mhj_mt"): "x", ("m", "asb_mt"): "x"})
    assert cmds == [
        [
            "python",
            "-m",
            "scripts.eval_multiturn",
            "--dataset",
            "asb",
            "--dataset",
            "mhj",
            "--chunk",
            "--dump-scores",
            "results/scores_multiturn",
        ]
    ]
