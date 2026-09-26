import pytest

from occam.calibration import GradeCalibrator


def test_fit_is_smoothed_accuracy_per_grade():
    g = ["high"] * 4 + ["low"] * 4
    y = [1, 1, 1, 0, 0, 0, 1, 0]
    cal = GradeCalibrator(prior_strength=0.0, monotone=False).fit(g, y)
    assert cal["high"] == pytest.approx(0.75)
    assert cal["low"] == pytest.approx(0.25)
    assert cal["moderate"] == 0.5


def test_monotone_pools_violators():
    g = ["low"] * 10 + ["moderate"] * 10 + ["high"] * 10
    y = [1] * 8 + [0] * 2 + [1] * 3 + [0] * 7 + [1] * 9 + [0]
    cal = GradeCalibrator().fit(g, y)
    assert cal["low"] <= cal["moderate"] <= cal["high"]
    assert cal["low"] == pytest.approx(cal["moderate"])


def test_roundtrip(tmp_path):
    cal = GradeCalibrator().fit(["high", "low"], [1, 0])
    p = tmp_path / "cal.json"
    cal.save(p)
    assert GradeCalibrator.load(p).mapping() == cal.mapping()


def test_load_rejects_bad_file(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"probs": {"high": 2.0, "low": 0.1, "moderate": 0.5}}')
    with pytest.raises(ValueError):
        GradeCalibrator.load(p)
    with pytest.raises(ValueError):
        GradeCalibrator().fit(["certain"], [1])
