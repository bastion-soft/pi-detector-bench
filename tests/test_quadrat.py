"""Offline tests for the Quadrat-IPI sampler: no dataset is downloaded.

The release is written corpus by corpus, so the fixture mimics that layout: long runs
of one carrier, in file order.
"""

from __future__ import annotations

from collections import Counter

from pidbench.indirect_data import quadrat_pick

# Corpus-by-corpus layout: all mail first, then web, then reports.
HOSTS = ["email"] * 3000 + ["web"] * 2000 + ["doc"] * 1500


def test_pooled_sample_has_equal_carrier_shares():
    idx = quadrat_pick(HOSTS, 400)
    mix = Counter(HOSTS[i] for i in idx)
    assert len(idx) == 400
    assert set(mix) == {"email", "web", "doc"}
    assert max(mix.values()) - min(mix.values()) <= 1


def test_sample_is_not_the_head_of_each_carrier():
    """Within a carrier the rows come from across the run, not its first m rows."""
    idx = quadrat_pick(HOSTS, 300, carrier="email")
    assert max(idx) > 300


def test_carrier_filter_keeps_one_carrier():
    idx = quadrat_pick(HOSTS, 200, carrier="doc")
    assert len(idx) == 200
    assert {HOSTS[i] for i in idx} == {"doc"}


def test_sample_is_deterministic():
    assert quadrat_pick(HOSTS, 400) == quadrat_pick(HOSTS, 400)


def test_no_duplicates_and_short_carriers_are_exhausted():
    hosts = ["email"] * 1000 + ["doc"] * 10
    idx = quadrat_pick(hosts, 100)
    assert len(idx) == len(set(idx)) == 100
    assert sum(hosts[i] == "doc" for i in idx) == 10
