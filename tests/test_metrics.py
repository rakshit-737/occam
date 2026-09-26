import math

import pytest

from occam.metrics import ari, brier, ece, nmi, prf, purity, reliability


def test_prf_micro_and_macro():
    m = prf([{"a", "b"}, {"a"}], [{"a"}, {"a", "c"}])
    assert m["micro_precision"] == pytest.approx(2 / 3)
    assert m["micro_recall"] == pytest.approx(2 / 3)
    # labels present in gold: a (F1=1), b (F1=0)
    assert m["macro_f1"] == pytest.approx(0.5)


def test_brier_and_ece():
    assert brier([1.0, 0.0], [True, False]) == 0
    assert brier([0.5], [True]) == pytest.approx(0.25)
    assert ece([0.9] * 10, [True] * 9 + [False]) == pytest.approx(0.0)
    assert ece([0.9] * 10, [False] * 10) == pytest.approx(0.9)
    assert reliability([0.9, 0.1], [True, False]) == [(0.1, 0.0, 1), (0.9, 1.0, 1)]


def test_clustering_scores():
    t = ["a", "a", "b", "b"]
    assert purity(t, [0, 0, 1, 1]) == 1.0
    assert nmi(t, [5, 5, 7, 7]) == pytest.approx(1.0)
    assert ari(t, [0, 0, 1, 1]) == pytest.approx(1.0)
    assert ari(t, [0, 1, 0, 1]) < 0
    assert 0 <= nmi(t, [0, 0, 0, 0]) < 1e-9 or math.isclose(nmi(t, [0, 0, 0, 0]), 0.0)
