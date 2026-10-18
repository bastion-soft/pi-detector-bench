"""Declared per-model thresholds (models.yaml `threshold:`)."""

from __future__ import annotations

import numpy as np
import pytest

from pidbench.models import (
    DEFAULT_THRESHOLD,
    ModelSpec,
    declared_thresholds,
    load_models,
    threshold_for,
)


def test_default_is_half_when_absent():
    s = ModelSpec(name="x", hf_id="o/x", attack_label=1)
    assert s.threshold is None and s.declared_threshold == DEFAULT_THRESHOLD == 0.5


def test_declared_threshold_is_used():
    assert ModelSpec(name="x", hf_id="o/x", attack_label=1, threshold=0.8).declared_threshold == 0.8


@pytest.mark.parametrize("bad", [0, 1, -0.1, 1.5])
def test_out_of_range_threshold_is_rejected(bad):
    with pytest.raises(ValueError):
        ModelSpec(name="x", hf_id="o/x", attack_label=1, threshold=bad)


def test_registry_thresholds_cover_every_model():
    table = declared_thresholds()
    assert set(table) == {s.name for s in load_models()}
    assert all(0 < t < 1 for t in table.values())
    assert threshold_for("not-registered", table) == 0.5


def test_custom_registry_threshold_loads(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text(
        'models:\n  - name: "a"\n    hf_id: "o/a"\n    attack_label: 1\n    threshold: 0.7\n'
        '  - name: "b"\n    hf_id: "o/b"\n    attack_label: 1\n'
    )
    assert declared_thresholds(p) == {"a": 0.7, "b": 0.5}


def test_fpr_row_reports_both_thresholds():
    from scripts.measure_false_positives import _format_markdown, fpr_row

    risks = [0.1, 0.55, 0.65, 0.9]
    row = fpr_row("m", "wildchat", risks, 1.0, declared_threshold=0.6)
    assert row.fpr == 0.75 and row.fpr_at_declared == 0.5 and row.declared_threshold == 0.6
    md = _format_markdown([row], ["wildchat"])
    assert "@thr" in md and "| 0.6 |" in md


def test_operating_point_records_declared_threshold():
    from scripts.analyze_operating_points import _analyze_runner

    s = np.array([0.1, 0.4, 0.6, 0.9])
    y = np.array([0, 0, 1, 1])
    res = _analyze_runner(s, y, np.array([0.3, 0.7, 0.2]), [0.95], [0.5], declared=0.8)
    assert res["declared_threshold"] == 0.8
    assert res["at_declared"]["recall_attacks"] == 0.5
    assert res["at_declared"]["fpr_benign"] == 0.0
    assert res["at_0.5"]["fpr_benign"] == pytest.approx(1 / 3, abs=1e-4)
