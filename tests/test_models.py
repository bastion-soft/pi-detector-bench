"""Registry loading, selection, and run provenance."""

from __future__ import annotations

import pytest

from pidbench.models import load_models, run_provenance


def test_registry_loads_and_every_entry_is_complete():
    specs = load_models()
    assert specs, "models.yaml is empty"
    for s in specs:
        assert s.name and s.hf_id
        assert isinstance(s.attack_label, (int, list))


def test_model_filter_matches_substring_and_glob():
    all_specs = load_models()
    needle = all_specs[0].name.split()[0].lower()
    assert load_models(only=[needle])
    assert len(load_models(only=[needle])) <= len(all_specs)
    assert load_models(only=[f"{needle}*"])


def test_model_filter_matches_on_hf_id_too():
    spec = load_models()[0]
    assert [s.name for s in load_models(only=[spec.hf_id])] == [spec.name]


def test_model_filter_is_case_insensitive():
    spec = load_models()[0]
    assert load_models(only=[spec.hf_id.upper()])


def test_unmatched_filter_is_a_hard_error_not_an_empty_run():
    """A silent empty run would write an empty table that looks like a result."""
    with pytest.raises(SystemExit) as e:
        load_models(only=["definitely-not-a-model"])
    assert "matched nothing" in str(e.value)


def test_empty_filter_returns_everything():
    assert len(load_models(only=[])) == len(load_models())


# ── provenance ────────────────────────────────────────────────────────────
class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_provenance_records_chunk_settings():
    p = run_provenance(_Args(chunk=True, chunk_temperature=0.3, model=["bastion"], threshold=0.5))
    assert p["chunk"] is True
    assert p["chunk_temperature"] == 0.3
    assert p["models_filter"] == ["bastion"]


def test_provenance_omits_temperature_when_not_chunking():
    p = run_provenance(_Args(chunk=False, chunk_temperature=0.1, model=[], threshold=0.5))
    assert p["chunk"] is False
    assert p["chunk_temperature"] is None
    assert p["models_filter"] is None


def test_provenance_tolerates_missing_attributes():
    assert run_provenance(_Args())["chunk"] is False
