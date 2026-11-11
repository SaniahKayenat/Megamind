"""
test_stage4.py - checks for Stage 4 (Nyo).

    python tests/test_stage4.py

1. The compact matrix used by 07_simulation.py gives exactly the same score_event() result as the
   same readings laid out at their real 2013 columns.
2. The parametric-bootstrap KS test is calibrated: on data that really is lognormal it rejects
   about 5% of the time (refitting inside the bootstrap is what makes this true; the textbook KS
   table would reject far less often).
"""
import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline_lib import score_event  # noqa: E402

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location(
    "dist", Path(__file__).resolve().parents[1] / "src" / "06_distribution.py")
dist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dist)


def test_compact_matrix_matches_real_layout():
    rng = np.random.default_rng(1)
    n, first_slot, ns = 50, 48 * 40 + 46, 6            # event starts 23:00, crosses midnight
    shifts = [-9, -2, 5, 12]
    days = [0] + shifts
    X = rng.lognormal(-2, 0.8, size=(n, len(days), ns))
    X[rng.random(X.shape) < 0.1] = np.nan                # some missing readings
    # real layout
    H = np.full((n, 365 * 48), np.nan)
    S = np.arange(first_slot, first_slot + ns)
    for j, k in enumerate(days):
        H[:, S + 48 * k] = X[:, j, :]
    a = score_event(H, S, shifts)
    # compact layout (as in 07_simulation.py)
    off = first_slot % 48
    Hs = np.empty((n, 48 * len(shifts) + off + ns))
    Sc = off + np.arange(ns)
    for j in range(len(days)):
        Hs[:, Sc + 48 * j] = X[:, j, :]
    b = score_event(Hs, Sc, list(range(1, len(days))))
    assert np.array_equal(a["valid"], b["valid"])
    assert np.allclose(a["score"], b["score"], equal_nan=True)
    assert np.array_equal(a["n_days"], b["n_days"])
    print("compact matrix == real layout: OK")


def test_ks_boot_is_calibrated(reps=200, B=99):
    rng = np.random.default_rng(2013)
    p = np.array([dist.ks_boot(rng.lognormal(-2, 0.75, 500), stats.lognorm, rng, B)[0]
                  for _ in range(reps)])
    rate = (p <= 0.05).mean()
    print(f"bootstrap KS rejection rate on true lognormal data: {rate:.3f} ({reps} samples)")
    assert 0.01 <= rate <= 0.10, rate      # 5% +/- Monte Carlo error with 200 samples


if __name__ == "__main__":
    test_compact_matrix_matches_real_layout()
    test_ks_boot_is_calibrated()
    print("all Stage 4 tests passed")
