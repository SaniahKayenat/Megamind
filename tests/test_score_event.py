"""
Hand-checkable tests for score_event(). Run with:  python tests/test_score_event.py
(or with pytest). Each case can be checked with a calculator.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline_lib import score_event  # noqa: E402

DAYS = 10
nan = np.nan


def blank(n_households=1):
    return np.full((n_households, DAYS * 48), nan)


def test_basic_example():
    """The worked example: event 0.30, matched days 0.36 -> score -0.06."""
    H = blank()
    S = np.arange(5 * 48 + 34, 5 * 48 + 46)          # day 5, 17:00-23:00 (12 half-hours)
    H[0, S] = 0.30
    for k in (-3, -2, 2, 3):
        H[0, S + 48 * k] = 0.36
    r = score_event(H, S, [-3, -2, 2, 3])
    assert np.isclose(r["score"][0], -0.06)
    assert r["valid"][0] and r["n_days"][0] == 4


def test_missing_reading_is_not_zero():
    """A missing event half-hour is left out of the sum AND the count, and out of the matched days too."""
    H = blank()
    S = np.arange(5 * 48 + 34, 5 * 48 + 46)
    H[0, S] = 0.30
    H[0, S[3]] = nan                                  # one missing reading on the event day
    for k in (-3, -2, 2, 3):
        H[0, S + 48 * k] = 0.36
        H[0, S[3] + 48 * k] = 5.0                     # a huge value at that same time on matched days
    r = score_event(H, S, [-3, -2, 2, 3])
    assert np.isclose(r["event_mean"][0], 0.30)       # not 0.30 * 11/12
    assert np.isclose(r["matched_mean"][0], 0.36)     # the 5.0s are dropped: same half-hours on both sides
    assert np.isclose(r["cover"][0], 11 / 12)


def test_coverage_rule():
    """Fewer than 80% of event half-hours -> not valid."""
    H = blank()
    S = np.arange(5 * 48 + 34, 5 * 48 + 46)
    H[0, S[:9]] = 0.30                                # 9 of 12 = 75%
    for k in (-3, -2, 2, 3):
        H[0, S + 48 * k] = 0.36
    assert not score_event(H, S, [-3, -2, 2, 3])["valid"][0]


def test_matched_day_rule():
    """Only 2 usable matched days -> not valid; a sparse matched day doesn't count."""
    H = blank()
    S = np.arange(5 * 48 + 34, 5 * 48 + 46)
    H[0, S] = 0.30
    H[0, S - 48 * 2] = 0.36
    H[0, S + 48 * 2] = 0.36
    H[0, (S + 48 * 3)[:6]] = 0.36                     # day +3 has only half the half-hours -> not usable
    r = score_event(H, S, [-2, 2, 3])
    assert r["n_days"][0] == 2 and not r["valid"][0]


def test_households_are_independent():
    """Two households on one event get their own scores."""
    H = blank(2)
    S = np.arange(5 * 48 + 34, 5 * 48 + 46)
    H[0, S], H[1, S] = 0.30, 0.42
    for k in (-3, -2, 2, 3):
        H[0, S + 48 * k], H[1, S + 48 * k] = 0.36, 0.40
    r = score_event(H, S, [-3, -2, 2, 3])
    assert np.allclose(r["score"], [-0.06, 0.02])


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("passed:", name)
