"""10_model.py - Stage 6 (Ahmad Jawid): which kinds of High events get bigger reductions?

    python src/10_model.py            (run from the repository root)

Reads   results/event_effects_main.csv   (Stage 3: one row per High event; effect = ToU mean score - Std mean score)
Writes  results/regression_coefficients.csv   coefficients with HC3 standard errors and 95% intervals, in kWh/hh and kW
        results/regression_vif.csv            variance inflation factors
        results/regression_influence.csv      fitted value, residual, leverage and Cook's distance for every event
        results/regression_cook_refit.csv     coefficients with and without the Cook's-flagged events
        results/regression_cv.csv             leave-one-month-out cross-validation, one row per held-out month
        results/results.json                  key p6_regression (every number reported in the report)
        results/test_log.csv                  one row per coefficient test (appended, never deleted)
        figures/reg_resid_vs_fitted.png, figures/reg_qq_residuals.png, figures/reg_cooks_distance.png

Rules (docs/decisions.md section 11, fixed 9 Nov 2026 before any outcome was seen):
    effect ~ evening + hours + winter + low_before, OLS with HC3 standard errors (5 parameters);
    no month predictor; if any VIF > 5, drop `hours`; baseline = mean effect;
    leave-one-month-out CV, RMSE of model vs baseline (a predictor that is constant in a training set
    is dropped for that fold only); diagnostics: residuals vs fitted, Q-Q of residuals,
    Cook's distance > 4/n (refit without), Durbin-Watson in date order.
    Coefficient x 2 = kW per household; more negative = bigger cut.
No random steps, so no seed is needed.
"""
import csv
import datetime
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

ROOT = Path(__file__).resolve().parents[1]
try:  # shared paths (Saniah's config.py)
    from config import RESULTS
except ImportError:
    RESULTS = ROOT / "results"
RESULTS = Path(RESULTS)
FIGURES = ROOT / "figures"

try:  # shared helper (pipeline_lib.py)
    from pipeline_lib import save_result
except ImportError:
    import json

    def save_result(key, value):
        path = RESULTS / "results.json"
        data = json.loads(path.read_text()) if path.exists() else {}
        data[key] = value
        path.write_text(json.dumps(data, indent=2, sort_keys=True, default=float))

try:  # shared helper, once it has been added to pipeline_lib.py (Stage 0)
    from pipeline_lib import log_test
except ImportError:
    def log_test(person, hypothesis, run, test, statistic, p_value, effect, note=""):
        """Append one row to results/test_log.csv. Called for EVERY test, including exploratory ones."""
        path = RESULTS / "test_log.csv"
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, cwd=ROOT).stdout.strip()
        new = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["timestamp", "git_commit", "person", "hypothesis", "run", "test",
                            "statistic", "p_value", "effect", "note"])
            w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), commit, person,
                        hypothesis, run, test, statistic, p_value, effect, note])

PERSON = "Ahmad Jawid"
PREDICTORS = ["evening", "hours", "winter", "low_before"]   # fixed in decisions.md section 11
VIF_LIMIT = 5.0
WHAT = {  # how each coefficient reads, for the kW sentences
    "evening": "events starting at 17:00 or 20:00, compared with other start times",
    "hours": "each extra hour of event length",
    "winter": "events in October-March, compared with April-September",
    "low_before": "events straight after a Low-price period, compared with other events",
}


# ---------------------------------------------------------------- pieces
def load_events(path):
    """High events with an effect, in date order (Durbin-Watson and the CV folds need the order)."""
    df = pd.read_csv(path, parse_dates=["start"])
    df = df[(df["tariff"] == "High") & df["effect"].notna()].sort_values("start").reset_index(drop=True)
    df[PREDICTORS] = df[PREDICTORS].astype(float)
    return df


def vif_table(df, predictors):
    X = sm.add_constant(df[predictors])
    return {c: float(variance_inflation_factor(X.values, i)) for i, c in enumerate(X.columns) if c != "const"}


def formula(predictors):
    return "effect ~ " + (" + ".join(predictors) if predictors else "1")


def coef_table(fit):
    ci = fit.conf_int(alpha=0.05)
    t = pd.DataFrame({
        "term": fit.params.index,
        "coef_kwh_hh": fit.params.values,
        "se_hc3_kwh_hh": fit.bse.values,
        "z": fit.tvalues.values,
        "p_value": fit.pvalues.values,
        "ci_low_kwh_hh": ci[0].values,
        "ci_high_kwh_hh": ci[1].values,
    })
    t["coef_kw"] = 2 * t["coef_kwh_hh"]
    t["ci_low_kw"] = 2 * t["ci_low_kwh_hh"]
    t["ci_high_kw"] = 2 * t["ci_high_kwh_hh"]
    return t


def lomo_cv(df, predictors):
    """Leave-one-month-out CV: model vs the training-mean baseline."""
    rows, err_m, err_b = [], [], []
    for m in sorted(df["month"].unique()):
        tr, te = df[df["month"] != m], df[df["month"] == m]
        use = [p for p in predictors if tr[p].nunique() > 1]       # constant in training -> drop for this fold
        f = smf.ols(formula(use), data=tr).fit()
        e_m = (te["effect"] - f.predict(te)).to_numpy()
        e_b = (te["effect"] - tr["effect"].mean()).to_numpy()
        err_m += list(e_m)
        err_b += list(e_b)
        rows.append({"held_out_month": int(m), "n_test": len(te), "n_train": len(tr),
                     "dropped_this_fold": ",".join(p for p in predictors if p not in use),
                     "rmse_model_kwh_hh": float(np.sqrt(np.mean(e_m ** 2))),
                     "rmse_baseline_kwh_hh": float(np.sqrt(np.mean(e_b ** 2)))})
    rmse_m = float(np.sqrt(np.mean(np.square(err_m))))
    rmse_b = float(np.sqrt(np.mean(np.square(err_b))))
    return pd.DataFrame(rows), rmse_m, rmse_b


def fmt_p(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def kw_sentence(row):
    """Coefficient -> plain words. Reduction = -2 x effect, so an extra cut = -2 x coefficient."""
    cut = -row.coef_kw
    lo, hi = -row.ci_high_kw, -row.ci_low_kw
    if abs(cut) < 0.0005:
        size = "about the same cut (less than 0.001 kW difference)"
    else:
        size = f"{abs(cut):.3f} kW {'more' if cut > 0 else 'less'} cut per household"
    return (f"{WHAT[row.term]}: {size} "
            f"(95% interval for the extra cut: {lo:.3f} to {hi:.3f} kW; {fmt_p(row.p_value)})")


HAC_LAGS = 3   # Newey-West rule of thumb floor(4 (n/100)^(2/9)) for n = 63


def hac_check(df, predictors):
    """EXPLORATORY (not in decisions.md): Newey-West standard errors, used only because Durbin-Watson
    is well below 2. Reported next to the pre-stated HC3 result, never instead of it."""
    h = smf.ols(formula(predictors), data=df).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    t = coef_table(h).rename(columns={"se_hc3_kwh_hh": "se_hac_kwh_hh"})
    return h, t


# ---------------------------------------------------------------- the whole stage
def run(df, figures_dir=None):
    """Everything Stage 6 computes, returned as tables and one summary dict. Writes only figures."""
    n = len(df)
    predictors = list(PREDICTORS)

    # 1. overlap between predictors
    vif = vif_table(df, predictors)
    hours_dropped = max(vif.values()) > VIF_LIMIT
    if hours_dropped:                                  # the pre-agreed choice
        predictors.remove("hours")
        vif_after = vif_table(df, predictors)
    else:
        vif_after = vif

    # 2. model and baseline
    fit = smf.ols(formula(predictors), data=df).fit(cov_type="HC3")
    coefs = coef_table(fit)
    baseline = float(df["effect"].mean())

    # 3. diagnostics
    ols = smf.ols(formula(predictors), data=df).fit()          # same coefficients; influence uses plain OLS
    infl = ols.get_influence()
    cooks = infl.cooks_distance[0]
    threshold = 4 / n
    influence = pd.DataFrame({"event_id": df["event_id"], "start": df["start"], "effect": df["effect"],
                              "fitted": ols.fittedvalues, "residual": ols.resid,
                              "leverage": infl.hat_matrix_diag, "cooks_distance": cooks})
    influence["flagged"] = influence["cooks_distance"] > threshold
    flagged = influence.loc[influence["flagged"], "event_id"].tolist()
    dw = float(durbin_watson(ols.resid))                        # df is in date order

    if flagged:
        refit = smf.ols(formula(predictors), data=df[~influence["flagged"]]).fit(cov_type="HC3")
        rc = coef_table(refit)
        cook = coefs[["term", "coef_kwh_hh", "p_value"]].merge(
            rc[["term", "coef_kwh_hh", "p_value"]], on="term", suffixes=("_all", "_without_flagged"))
        cook["same_sign"] = np.sign(cook["coef_kwh_hh_all"]) == np.sign(cook["coef_kwh_hh_without_flagged"])
        cook["coef_kw_all"] = 2 * cook["coef_kwh_hh_all"]
        cook["coef_kw_without_flagged"] = 2 * cook["coef_kwh_hh_without_flagged"]
    else:
        refit, rc, cook = None, None, pd.DataFrame()

    # 4. leave-one-month-out cross-validation
    cv, rmse_m, rmse_b = lomo_cv(df, predictors)
    beats = rmse_m < rmse_b
    improvement = 100 * (1 - rmse_m / rmse_b)
    folds_won = int((cv["rmse_model_kwh_hh"] < cv["rmse_baseline_kwh_hh"]).sum())

    # 5. exploratory check, only because Durbin-Watson is far from 2
    hac_fit, hac = hac_check(df, predictors)
    sign_changes = cook.loc[~cook["same_sign"], "term"].tolist() if flagged else []
    top_lev = influence.loc[influence["leverage"].idxmax()]

    # 6. figures
    if figures_dir is not None:
        draw_figures(influence, ols, threshold, Path(figures_dir))

    terms = coefs[coefs["term"] != "Intercept"]
    summary = {
        "n_events": n,
        "predictors": predictors,
        "vif": vif,
        "vif_limit": VIF_LIMIT,
        "hours_dropped": hours_dropped,
        "vif_after_drop": vif_after if hours_dropped else None,
        "events_per_parameter": n / (len(predictors) + 1),
        "coefficients": {r.term: {"coef_kwh_hh": r.coef_kwh_hh, "se_hc3_kwh_hh": r.se_hc3_kwh_hh,
                                  "z": r.z, "p_value": r.p_value,
                                  "ci95_kwh_hh": [r.ci_low_kwh_hh, r.ci_high_kwh_hh],
                                  "coef_kw": r.coef_kw, "ci95_kw": [r.ci_low_kw, r.ci_high_kw]}
                         for r in coefs.itertuples()},
        "r_squared": float(fit.rsquared),
        "r_squared_adj": float(fit.rsquared_adj),
        "baseline_mean_effect_kwh_hh": baseline,
        "baseline_mean_effect_kw": 2 * baseline,
        "durbin_watson": dw,
        "durbin_watson_note": ("near 2: neighbouring events do not share errors" if 1.5 <= dw <= 2.5 else
                               "well away from 2: residuals of events close in time are correlated, so the "
                               "HC3 intervals are probably too narrow (see exploratory_hac)"),
        "highest_leverage_event": {"event_id": top_lev["event_id"], "start": str(top_lev["start"]),
                                   "leverage": float(top_lev["leverage"]),
                                   "cooks_distance": float(top_lev["cooks_distance"])},
        "cooks_threshold": threshold,
        "influential_events": [{"event_id": r.event_id, "start": str(r.start), "cooks_distance": r.cooks_distance}
                               for r in influence[influence["flagged"]].itertuples()],
        "cook_refit_n_events": int(n - len(flagged)),
        "cook_refit_coefficients_kw": ({r.term: r.coef_kw for r in rc.itertuples()} if flagged else None),
        "cook_refit_all_signs_same": (bool(cook["same_sign"].all()) if flagged else None),
        "cook_refit_sign_changes": sign_changes,
        "cook_refit_sign_changes_ci_includes_zero": (
            bool(all(coefs.set_index("term").loc[t, "ci_low_kwh_hh"] < 0 < coefs.set_index("term").loc[t, "ci_high_kwh_hh"]
                     for t in sign_changes)) if sign_changes else None),
        "exploratory_hac": {"note": "EXPLORATORY, not in decisions.md: Newey-West (HAC) standard errors, "
                                    f"{HAC_LAGS} lags in date order, because Durbin-Watson is far from 2. "
                                    "No small-sample correction, so not comparable one-to-one with HC3; "
                                    "the HC3 result stays the main one.",
                            "lags": HAC_LAGS,
                            "coefficients": {r.term: {"coef_kw": r.coef_kw, "se_kwh_hh": r.se_hac_kwh_hh,
                                                      "p_value": r.p_value, "ci95_kw": [r.ci_low_kw, r.ci_high_kw]}
                                             for r in hac.itertuples()}},
        "cv_rmse_model_kwh_hh": rmse_m,
        "cv_rmse_baseline_kwh_hh": rmse_b,
        "cv_rmse_model_kw": 2 * rmse_m,
        "cv_rmse_baseline_kw": 2 * rmse_b,
        "cv_model_beats_baseline": bool(beats),
        "cv_improvement_pct": float(improvement),
        "cv_folds": len(cv),
        "cv_folds_model_better": folds_won,
        "cv_folds_with_dropped_predictor": int((cv["dropped_this_fold"] != "").sum()),
        "interpretation_kw": [kw_sentence(r) for r in terms.itertuples()],
        "conclusion": (
            (f"By the pre-stated rule the model beats the baseline: its leave-one-month-out RMSE is "
             f"{improvement:.1f}% lower ({2 * rmse_m:.4f} vs {2 * rmse_b:.4f} kW), and it is better in "
             f"{folds_won} of {len(cv)} months. "
             + ("The margin is small, so treat the model as a rough guide to when signals work best, not a forecast."
                if improvement < 10 else ""))
            if beats else
            "Event timing and length do not predict the response better than the mean "
            "(leave-one-month-out RMSE not below the baseline's), so the coefficients "
            "describe these events but should not be used to choose when to send signals."),
    }
    return {"summary": summary, "coefficients": coefs, "vif": vif, "influence": influence,
            "cook_refit": cook, "cv": cv, "fit": fit, "refit": refit, "hac": hac}


def draw_figures(influence, ols, threshold, figures_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir.mkdir(parents=True, exist_ok=True)
    INK, INK2, GRID, ACCENT, GREY = "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6", "#8a8984"

    def style(ax):
        ax.grid(color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
        for s in ["left", "bottom"]:
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8.5, length=0)

    f2 = influence.assign(fitted_kw=2 * influence.fitted, resid_kw=2 * influence.residual)

    # residuals vs fitted (kW per household)
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=150)
    ax.axhline(0, color=INK2, linewidth=0.9)
    ok = ~f2.flagged
    ax.scatter(f2.fitted_kw[ok], f2.resid_kw[ok], s=26, color=GREY, edgecolor="white", linewidth=0.8, zorder=3)
    ax.scatter(f2.fitted_kw[~ok], f2.resid_kw[~ok], s=34, color=ACCENT, edgecolor="white", linewidth=0.8, zorder=4,
               label="Cook's distance above 4/n")
    for r in f2[~ok].itertuples():
        ax.annotate(f"{r.event_id} ({r.start:%d %b})", (r.fitted_kw, r.resid_kw), xytext=(5, 3),
                    textcoords="offset points", fontsize=7.5, color=INK2)
    ax.set_xlabel("Fitted effect (kW per household, ToU − Std)", fontsize=9, color=INK2)
    ax.set_ylabel("Residual (kW per household)", fontsize=9, color=INK2)
    ax.set_title("Residuals vs fitted values, 63 High events", loc="left", fontsize=11, color=INK)
    if (~ok).any():
        ax.legend(frameon=False, fontsize=8, loc="lower right")
    style(ax)
    fig.tight_layout()
    fig.savefig(figures_dir / "reg_resid_vs_fitted.png", bbox_inches="tight")
    plt.close(fig)

    # Q-Q of residuals
    fig, ax = plt.subplots(figsize=(4.8, 4.2), dpi=150)
    (osm, osr), (slope, icpt, _) = stats.probplot(2 * ols.resid, dist="norm")
    ax.plot(osm, slope * osm + icpt, color=INK2, linewidth=1)
    ax.scatter(osm, osr, s=22, color=ACCENT, edgecolor="white", linewidth=0.7, zorder=3)
    ax.set_xlabel("Normal quantile", fontsize=9, color=INK2)
    ax.set_ylabel("Residual (kW per household)", fontsize=9, color=INK2)
    ax.set_title("Q-Q plot of the regression residuals", loc="left", fontsize=11, color=INK)
    style(ax)
    fig.tight_layout()
    fig.savefig(figures_dir / "reg_qq_residuals.png", bbox_inches="tight")
    plt.close(fig)

    # Cook's distance in date order
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=150)
    colours = np.where(influence.flagged, ACCENT, GREY)
    ax.vlines(influence.start, 0, influence.cooks_distance, color=colours, linewidth=1.6)
    ax.scatter(influence.start, influence.cooks_distance, s=14, color=colours, zorder=3)
    ax.axhline(threshold, color=INK2, linestyle=(0, (4, 3)), linewidth=1)
    ax.text(influence.start.max(), threshold, f"4/n = {threshold:.3f}", va="bottom", ha="right", fontsize=8, color=INK2)
    for r in influence[influence.flagged].itertuples():
        ax.annotate(r.event_id, (r.start, r.cooks_distance), xytext=(4, 2), textcoords="offset points",
                    fontsize=7.5, color=INK2)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_ylabel("Cook's distance", fontsize=9, color=INK2)
    ax.set_title("Influence of each High event on the regression, 2013", loc="left", fontsize=11, color=INK)
    style(ax)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(figures_dir / "reg_cooks_distance.png", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    df = load_events(RESULTS / "event_effects_main.csv")
    out = run(df, figures_dir=FIGURES)
    s = out["summary"]

    out["coefficients"].to_csv(RESULTS / "regression_coefficients.csv", index=False, float_format="%.6g")
    pd.DataFrame({"predictor": list(s["vif"]), "vif": list(s["vif"].values())}).to_csv(
        RESULTS / "regression_vif.csv", index=False, float_format="%.4g")
    out["influence"].to_csv(RESULTS / "regression_influence.csv", index=False, float_format="%.6g")
    out["cook_refit"].to_csv(RESULTS / "regression_cook_refit.csv", index=False, float_format="%.6g")
    out["cv"].to_csv(RESULTS / "regression_cv.csv", index=False, float_format="%.6g")
    out["hac"].to_csv(RESULTS / "regression_hac_exploratory.csv", index=False, float_format="%.6g")
    save_result("p6_regression", s)

    # every coefficient test goes in the test log (planned fit, and the planned Cook's refit)
    for r in out["coefficients"].itertuples():
        if r.term == "Intercept":
            continue
        log_test(PERSON, f"regression: {r.term}", "main (63 High events)",
                 "OLS coefficient, HC3 z-test, two-sided", round(r.z, 4), round(r.p_value, 6), round(r.coef_kw, 6),
                 f"kW per household; 95% CI {r.ci_low_kw:.4f} to {r.ci_high_kw:.4f}; predictors {'+'.join(s['predictors'])}")
    if out["refit"] is not None:
        rc = coef_table(out["refit"])
        for r in rc.itertuples():
            if r.term == "Intercept":
                continue
            log_test(PERSON, f"regression: {r.term}", f"without Cook's-flagged events ({s['cook_refit_n_events']} events)",
                     "OLS coefficient, HC3 z-test, two-sided", round(r.z, 4), round(r.p_value, 6), round(r.coef_kw, 6),
                     "planned diagnostic refit (decisions.md section 11); flagged: "
                     + ", ".join(e["event_id"] for e in s["influential_events"]))
    for r in out["hac"].itertuples():
        if r.term == "Intercept":
            continue
        log_test(PERSON, f"regression: {r.term}", f"exploratory: Newey-West HAC SEs, {HAC_LAGS} lags (63 High events)",
                 "OLS coefficient, HAC z-test, two-sided", round(r.z, 4), round(r.p_value, 6), round(r.coef_kw, 6),
                 f"EXPLORATORY, not pre-stated; run because Durbin-Watson = {s['durbin_watson']:.2f}; "
                 f"95% CI {r.ci_low_kw:.4f} to {r.ci_high_kw:.4f} kW; HC3 result stays the main one")

    # printed summary
    print(f"Stage 6 regression: {s['n_events']} High events, predictors {s['predictors']}")
    print("VIF:", {k: round(v, 2) for k, v in s["vif"].items()},
          "-> hours dropped" if s["hours_dropped"] else "-> all <= 5, hours kept")
    print(out["coefficients"][["term", "coef_kw", "ci_low_kw", "ci_high_kw", "p_value"]].round(4).to_string(index=False))
    print(f"R^2 {s['r_squared']:.3f} (adjusted {s['r_squared_adj']:.3f}); "
          f"Durbin-Watson {s['durbin_watson']:.2f}: {s['durbin_watson_note']}")
    print(f"Cook's distance > {s['cooks_threshold']:.3f}:", [e["event_id"] for e in s["influential_events"]] or "none",
          "| sign changes without them:", s["cook_refit_sign_changes"] or "none",
          "| highest leverage:", s["highest_leverage_event"]["event_id"],
          f"({s['highest_leverage_event']['leverage']:.2f})")
    print(f"LOMO CV RMSE (kW): model {s['cv_rmse_model_kw']:.4f} vs baseline {s['cv_rmse_baseline_kw']:.4f}"
          f" ({s['cv_improvement_pct']:.1f}% lower; better in {s['cv_folds_model_better']} of {s['cv_folds']} months)")
    print("Exploratory Newey-West check:", {t: f"{v['coef_kw']:.4f} kW, p={v['p_value']:.3f}"
                                            for t, v in s["exploratory_hac"]["coefficients"].items() if t != "Intercept"})
    for line in s["interpretation_kw"]:
        print(" -", line)
    print("Conclusion:", s["conclusion"])


if __name__ == "__main__":
    main()
