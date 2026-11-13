"""tests/test_10_model.py - checks the Stage 6 code on made-up events where the right answer is known.

    python tests/test_10_model.py

Uses no real electricity data and writes nothing to results/.
  1. planted coefficients are recovered, and the HC3 standard errors match the textbook formula;
  2. with a real signal the model beats the mean baseline in leave-one-month-out CV;
  3. a predictor that is constant in a training fold is dropped for that fold only;
  4. if `hours` overlaps strongly with the others (VIF > 5) it is dropped, as decisions.md says;
  5. a planted extreme event is flagged by Cook's distance and the refit leaves it out.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location("model10", SRC / "10_model.py")
m10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m10)


def fake_events(n=63, seed=2013, beta=(-0.01, -0.012, -0.001, 0.004, -0.006), noise=0.002):
    """Made-up event table in the event_effects_main.csv layout, with a known true model."""
    rng = np.random.default_rng(seed)
    months = np.sort(rng.integers(1, 13, size=n))
    df = pd.DataFrame({
        "event_id": [f"H{i:03d}" for i in range(n)],
        "tariff": "High",
        "start": pd.to_datetime([f"2013-{mm:02d}-{rng.integers(1, 28):02d} 17:00" for mm in months]),
        "month": months,
        "evening": rng.integers(0, 2, size=n).astype(float),
        "hours": rng.choice([3.0, 6.0, 12.0], size=n, p=[0.45, 0.45, 0.10]),
        "winter": np.isin(months, [10, 11, 12, 1, 2, 3]).astype(float),
        "low_before": rng.integers(0, 2, size=n).astype(float),
    })
    b0, be, bh, bw, bl = beta
    df["effect"] = (b0 + be * df.evening + bh * df.hours + bw * df.winter + bl * df.low_before
                    + rng.normal(0, noise, size=n))
    return df.sort_values("start").reset_index(drop=True)


def hc3_by_hand(df, predictors):
    X = np.column_stack([np.ones(len(df))] + [df[p].to_numpy(float) for p in predictors])
    y = df["effect"].to_numpy()
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    h = np.einsum("ij,jk,ik->i", X, XtX_inv, X)
    meat = X.T @ (X * (e ** 2 / (1 - h) ** 2)[:, None])
    return beta, np.sqrt(np.diag(XtX_inv @ meat @ XtX_inv))


def test_recovers_planted_coefficients_and_hc3():
    df = fake_events()
    out = m10.run(df)
    c = out["coefficients"].set_index("term")
    truth = dict(zip(["Intercept"] + m10.PREDICTORS, (-0.01, -0.012, -0.001, 0.004, -0.006)))
    for term, b in truth.items():
        lo, hi = c.loc[term, "ci_low_kwh_hh"], c.loc[term, "ci_high_kwh_hh"]
        assert abs(c.loc[term, "coef_kwh_hh"] - b) < 0.003, (term, c.loc[term, "coef_kwh_hh"], b)
        assert lo < b < hi or abs(c.loc[term, "coef_kwh_hh"] - b) < 0.001, (term, lo, hi, b)
    beta, se = hc3_by_hand(df, m10.PREDICTORS)
    assert np.allclose(c["coef_kwh_hh"].to_numpy(), beta)
    assert np.allclose(c["se_hc3_kwh_hh"].to_numpy(), se)
    assert np.allclose(c["coef_kw"], 2 * c["coef_kwh_hh"])
    print("passed: planted coefficients recovered; HC3 standard errors match the formula; kW = 2 x kWh/hh")


def test_cv_beats_baseline_with_signal():
    out = m10.run(fake_events())
    s = out["summary"]
    assert s["cv_model_beats_baseline"] and s["cv_rmse_model_kwh_hh"] < s["cv_rmse_baseline_kwh_hh"]
    assert out["cv"]["n_test"].sum() == s["n_events"]
    print(f"passed: with a real signal, CV RMSE {s['cv_rmse_model_kwh_hh']:.4f} < baseline {s['cv_rmse_baseline_kwh_hh']:.4f}")


def test_constant_predictor_dropped_for_that_fold_only():
    df = fake_events()
    df["low_before"] = (df["month"] == 5).astype(float)       # only May events have low_before = 1
    out = m10.run(df)
    cv = out["cv"].set_index("held_out_month")
    assert cv.loc[5, "dropped_this_fold"] == "low_before"
    assert (cv.drop(index=5)["dropped_this_fold"] == "").all()
    assert "low_before" in out["summary"]["predictors"]
    print("passed: a predictor constant in one training fold is dropped for that fold only")


def test_vif_rule_drops_hours():
    df = fake_events()
    rng = np.random.default_rng(7)
    df["hours"] = 3 + 3 * df["evening"] + 2 * df["low_before"] + rng.normal(0, 0.05, len(df))
    out = m10.run(df)
    s = out["summary"]
    assert s["hours_dropped"] and "hours" not in s["predictors"] and max(s["vif"].values()) > 5
    assert len(out["coefficients"]) == 4
    print(f"passed: VIF {max(s['vif'].values()):.1f} > 5 -> hours dropped, 4 parameters left")


def test_cooks_flags_planted_outlier():
    df = fake_events()
    i = df.index[(df.hours == 12.0)][0]
    df.loc[i, "effect"] += 0.08                                # one wild event
    out = m10.run(df)
    s = out["summary"]
    flagged = [e["event_id"] for e in s["influential_events"]]
    assert df.loc[i, "event_id"] in flagged
    assert s["cook_refit_n_events"] == len(df) - len(flagged)
    print(f"passed: the planted extreme event {df.loc[i, 'event_id']} is flagged; refit uses {s['cook_refit_n_events']} events")


if __name__ == "__main__":
    test_recovers_planted_coefficients_and_hc3()
    test_cv_beats_baseline_with_signal()
    test_constant_predictor_dropped_for_that_fold_only()
    test_vif_rule_drops_hours()
    test_cooks_flags_planted_outlier()
