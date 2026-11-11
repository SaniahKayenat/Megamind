"""
06_distribution.py - Stage 4, Part A: distribution model for household half-hourly use.

    python src/06_distribution.py            # full run (~80,000 fits, 10-30 min)
    python src/06_distribution.py --B 19     # quick check of the code (not for the report)

What it does (guideline section 12, Part A; rules in docs/decisions.md "Distribution"):
    1. 200 households with >= 300 days of 2013 data, sorted by LCLid, rng = default_rng(2013),
       rng.choice(ids, 200, replace=False)                              -> results/dist_sample.csv
    2. each household's readings on the 212 all-Normal days; record the share of exact zeros,
       then drop zeros (neither model allows a 0)
    3. 500 readings per household drawn at random (same rng, same household order every run)
    4. lognormal and gamma by maximum likelihood with location fixed at 0; AIC = 2k - 2 logL, k = 2
    5. parametric-bootstrap KS test (B = 199, refit on every simulated sample)
    6. results/dist_fits.csv (one row per household)
    7. figures/qq_p10.png, qq_p50.png, qq_p90.png, qq_worst.png (both models side by side)
    8. summary numbers -> results.json under "p4_distribution"
    9. "where the fit breaks" numbers -> results.json under "p4_fit_breaks" and
       results/dist_where_it_breaks.txt

Inputs: data/interim/H2013.npy, results/households_index.csv, results/normal_days.csv
Nothing here touches the household scores or compares ToU with Std (results gate).
"""
import argparse
import time
import warnings
import os
from config import ROOT
os.environ.setdefault("MPLCONFIGDIR", str(ROOT/"tmp"/"matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from config import H2013, HOUSEHOLDS, MIN_DAYS_2013, RESULTS, ROOT, SEED
from pipeline_lib import save_result

N_HOUSEHOLDS = 200
N_READINGS = 500
FIGURES = ROOT / "figures"
MODELS = {"lognormal": stats.lognorm, "gamma": stats.gamma}

# chart colours (reference categorical palette: slot 1 blue, slot 2 orange; text inks)
C_LN, C_GA, INK, INK2, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"


# ------------------------------------------------------------------ fitting
def fit(x, dist):
    """MLE with location fixed at 0. Returns (params, AIC) with 2 free parameters."""
    p = dist.fit(x, floc=0)                      # (shape, 0, scale)
    ll = dist.logpdf(x, *p).sum()
    return p, 2 * 2 - 2 * ll


def ks_boot(x, dist, rng, B=199):
    """
    Parametric-bootstrap KS p-value. The textbook KS table assumes the parameters were known
    in advance; ours are estimated from the same data, which makes the fit look too good.
    So: simulate from the fitted model, REFIT to each simulated sample, recompute KS, and see
    how often the simulated KS is at least as large as the observed one.
    (The guideline's code block has `hits +=` dedented outside the loop by a typo; it belongs
     inside, as here.)
    """
    p = dist.fit(x, floc=0)
    d_obs = stats.kstest(x, dist.cdf, args=p).statistic
    hits = 0
    for _ in range(B):
        y = dist.rvs(*p, size=len(x), random_state=rng)
        q = dist.fit(y, floc=0)                  # refit every time: this is what makes it valid
        hits += stats.kstest(y, dist.cdf, args=q).statistic >= d_obs
    return (1 + hits) / (B + 1), d_obs


def normal_day_columns(normal_days_csv):
    """Columns of H2013 on the all-Normal days: date d covers slots 48*day_of_year .. +47."""
    nd = pd.read_csv(normal_days_csv, parse_dates=["date"])
    doy = (nd.date - pd.Timestamp("2013-01-01")).dt.days.to_numpy()
    cols = (doy[:, None] * 48 + np.arange(48)[None, :])
    return cols, len(nd)


# ------------------------------------------------------------------ plots
def qq_figure(x, row, label, path):
    """Q-Q plots on log axes, lognormal and gamma side by side, for one household."""
    xs = np.sort(x)
    n = len(xs)
    pp = (np.arange(1, n + 1) - 0.5) / n
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), sharex=True, sharey=True)
    lo, hi = xs.min() * 0.7, xs.max() * 1.4
    for ax, (name, dist), colour in zip(axes, MODELS.items(), (C_LN, C_GA)):
        if name == "lognormal":
            p = (row.ln_sigma, 0, np.exp(row.ln_mu))
            pval, aic = row.ln_ks_p, row.ln_aic
        else:
            p = (row.ga_shape, 0, row.ga_scale)
            pval, aic = row.ga_ks_p, row.ga_aic
        q = dist.ppf(pp, *p)
        lo, hi = min(lo, q.min() * 0.7), max(hi, q.max() * 1.4)
        ax.plot([1e-4, 100], [1e-4, 100], color=INK2, lw=1, ls="--", zorder=1)
        ax.scatter(q, xs, s=9, color=colour, linewidth=0, zorder=2)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_title(f"{name}   KS p = {pval:.3f}   AIC = {aic:,.0f}", fontsize=10, color=INK)
        ax.set_xlabel("model quantile (kWh per half-hour)", color=INK2, fontsize=9)
        ax.grid(True, which="major", color=GRID, lw=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(colors=INK2, labelsize=8)
    axes[0].set_ylabel("observed reading (kWh per half-hour)", color=INK2, fontsize=9)
    for ax in axes:
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    fig.suptitle(f"{label}: household {row.LCLid} ({row.group}), {row.daily_kwh:.1f} kWh/day, "
                 f"{N_READINGS} non-zero normal-day readings", fontsize=10.5, color=INK)
    fig.text(0.5, -0.02, "Points on the dashed line = perfect fit. Points above it at the right = "
             "more large readings than the model expects.", ha="center", fontsize=8.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=199, help="bootstrap simulations per KS test")
    args = ap.parse_args()
    t0 = time.time()
    FIGURES.mkdir(exist_ok=True)

    # 1. sample of households
    hh = pd.read_csv(HOUSEHOLDS)
    ids = np.sort(hh.loc[hh.days_2013 >= MIN_DAYS_2013, "LCLid"].to_numpy())
    rng = np.random.default_rng(SEED)
    chosen = list(rng.choice(ids, N_HOUSEHOLDS, replace=False))
    H = np.load(H2013, mmap_mode="r")
    cols, n_days = normal_day_columns(RESULTS / "normal_days.csv")
    flat_cols = cols.ravel()
    hx = hh.set_index("LCLid")

    # A household needs at least 500 non-zero normal-day readings to be fitted. A meter that
    # records only zeros (one such household turns up in the draw) cannot be fitted by either
    # model; it is replaced by a further draw from the remaining eligible households with the
    # same rng, and the replacement is recorded (decisions.md: log this rule).
    def n_nonzero(lcl):
        v = np.asarray(H[int(hx.at[lcl, "row"]), flat_cols], dtype=np.float64)
        return int((v[~np.isnan(v)] > 0).sum())

    replaced = []
    for j in range(len(chosen)):
        while n_nonzero(chosen[j]) < N_READINGS:
            pool = np.setdiff1d(ids, chosen)
            new = rng.choice(pool)
            replaced.append({"dropped": chosen[j], "nonzero_readings": n_nonzero(chosen[j]), "replacement": new})
            chosen[j] = new
    sample = hx.loc[chosen, ["group", "row", "days_2013", "high_night"]].reset_index()
    sample["replacement_for"] = ""
    for rp in replaced:
        sample.loc[sample.LCLid == rp["replacement"], "replacement_for"] = rp["dropped"]
    sample.to_csv(RESULTS / "dist_sample.csv", index=False)
    print(f"{len(ids)} eligible households; sampled {len(sample)} "
          f"({(sample.group == 'ToU').sum()} ToU, {(sample.group == 'Std').sum()} Std); "
          f"replaced {len(replaced)}: {replaced}")

    # 2-3. normal-day readings, zero share, 500 non-zero readings each
    rows, draws = [], []
    for r in sample.itertuples(index=False):
        v = np.asarray(H[r.row, flat_cols], dtype=np.float64)
        v_day = v.reshape(n_days, 48)
        ok = ~np.isnan(v)
        x_all = v[ok]
        zero_share = float((x_all == 0).mean())
        nz = x_all[x_all > 0]
        x = rng.choice(nz, N_READINGS, replace=False)
        draws.append(x)
        # day-to-day spread of mean log-use (used by the simulation): one value per normal day
        with np.errstate(divide="ignore", invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)   # days with no reading
            lv = np.where(v_day > 0, np.log(v_day), np.nan)
            day_mean = np.nanmean(lv, axis=1)
        day_mean = day_mean[np.isfinite(day_mean) & ((v_day > 0).sum(axis=1) >= 24)]
        rows.append({
            "LCLid": r.LCLid, "group": r.group, "high_night": r.high_night,
            "n_normal_readings": int(ok.sum()), "n_zero": int((x_all == 0).sum()),
            "zero_share": zero_share,
            "daily_kwh": float(x_all.mean() * 48),
            "sd_day_mean_log": float(np.std(day_mean, ddof=1)),
            # discreteness at the low end (recorded in 0.001 kWh steps)
            "share_le_0p01": float((x <= 0.010 + 1e-9).mean()),
            "distinct_le_0p05": int(len(np.unique(x[x <= 0.05 + 1e-9]))),
            "n_le_0p05": int((x <= 0.05 + 1e-9).sum()),
        })
    del H

    # 4-5. fits, AIC, bootstrap KS
    for i, (row, x) in enumerate(zip(rows, draws)):
        (s, _, sc), aic_ln = fit(x, stats.lognorm)
        (a, _, gsc), aic_ga = fit(x, stats.gamma)
        p_ln, d_ln = ks_boot(x, stats.lognorm, rng, args.B)
        p_ga, d_ga = ks_boot(x, stats.gamma, rng, args.B)
        row.update({"ln_mu": np.log(sc), "ln_sigma": s, "ga_shape": a, "ga_scale": gsc,
                    "ln_aic": aic_ln, "ga_aic": aic_ga, "ln_ks_d": d_ln, "ga_ks_d": d_ga,
                    "ln_ks_p": p_ln, "ga_ks_p": p_ga})
        # where along the range the fit is off: observed / model quantile at 1%, 50%, 99%
        for pct in (1, 50, 99):
            q_obs = np.quantile(x, pct / 100)
            row[f"ln_ratio_q{pct}"] = q_obs / stats.lognorm.ppf(pct / 100, s, 0, sc)
            row[f"ga_ratio_q{pct}"] = q_obs / stats.gamma.ppf(pct / 100, a, 0, gsc)
        # skewness of log readings (lognormal => symmetric on log scale)
        row["skew_log"] = float(stats.skew(np.log(x)))
        if (i + 1) % 20 == 0:
            print(f"  fitted {i + 1}/{len(rows)} households  ({time.time() - t0:.0f} s)")

    fits = pd.DataFrame(rows)
    fits["aic_diff_ln_minus_ga"] = fits.ln_aic - fits.ga_aic      # negative = lognormal better
    fits.to_csv(RESULTS / "dist_fits.csv", index=False, float_format="%.6g")

    # 7. Q-Q plots: 10th / 50th / 90th percentile of daily use, and the worst lognormal p-value
    order = fits.sort_values(["daily_kwh", "LCLid"]).reset_index(drop=True)
    picks = {}
    for tag, pct in (("p10", 10), ("p50", 50), ("p90", 90)):
        k = int(round(pct / 100 * (len(order) - 1)))
        picks[tag] = (f"{pct}th percentile of daily use", order.iloc[k].LCLid)
    worst = fits.sort_values(["ln_ks_p", "ln_ks_d"], ascending=[True, False]).iloc[0].LCLid
    picks["worst"] = ("Worst lognormal fit (lowest KS p, largest KS distance)", worst)
    for tag, (label, lcl) in picks.items():
        i = fits.index[fits.LCLid == lcl][0]
        qq_figure(draws[i], fits.loc[i], label, FIGURES / f"qq_{tag}.png")

    # 8. summary
    summary = {
        "households": int(len(fits)),
        "households_tou": int((fits.group == "ToU").sum()),
        "households_std": int((fits.group == "Std").sum()),
        "readings_per_household": N_READINGS,
        "households_replaced": replaced,
        "bootstrap_B": args.B,
        "share_lognormal_lower_aic": float((fits.aic_diff_ln_minus_ga < 0).mean()),
        "median_aic_diff_ln_minus_ga": float(fits.aic_diff_ln_minus_ga.median()),
        "share_not_rejected_5pct_lognormal": float((fits.ln_ks_p > 0.05).mean()),
        "share_not_rejected_5pct_gamma": float((fits.ga_ks_p > 0.05).mean()),
        "median_zero_share": float(fits.zero_share.median()),
        "median_ln_sigma": float(fits.ln_sigma.median()),
        "median_skew_log": float(fits.skew_log.median()),
        "sigma_day_median": float(fits.sd_day_mean_log.median()),
        "qq_households": {k: v[1] for k, v in picks.items()},
    }
    save_result("p4_distribution", summary)

    # 9. where the fit breaks (numbers for the report sentences)
    hn = fits.high_night.fillna(False).astype(bool)
    breaks = {
        "zeros_median_share": float(fits.zero_share.median()),
        "zeros_pooled_share": float(fits.n_zero.sum() / fits.n_normal_readings.sum()),
        "zeros_max_share": float(fits.zero_share.max()),
        "zeros_share_households_any": float((fits.zero_share > 0).mean()),
        "zeros_share_households_over_5pct": float((fits.zero_share > 0.05).mean()),
        "low_end_median_share_readings_le_0p01kwh": float(fits.share_le_0p01.median()),
        "low_end_median_distinct_values_le_0p05kwh": float(fits.distinct_le_0p05.median()),
        "low_end_median_readings_le_0p05kwh": float(fits.n_le_0p05.median()),
        "ln_median_ratio_obs_to_model_q1": float(fits.ln_ratio_q1.median()),
        "ln_median_ratio_obs_to_model_q50": float(fits.ln_ratio_q50.median()),
        "ln_median_ratio_obs_to_model_q99": float(fits.ln_ratio_q99.median()),
        "ga_median_ratio_obs_to_model_q1": float(fits.ga_ratio_q1.median()),
        "ga_median_ratio_obs_to_model_q50": float(fits.ga_ratio_q50.median()),
        "ga_median_ratio_obs_to_model_q99": float(fits.ga_ratio_q99.median()),
        "ln_share_households_q99_obs_over_model_by_20pct": float((fits.ln_ratio_q99 > 1.2).mean()),
        "ln_share_households_q99_obs_under_model_by_20pct": float((fits.ln_ratio_q99 < 1 / 1.2).mean()),
        "ln_reject_rate_high_night_homes": float((fits.ln_ks_p[hn] <= 0.05).mean()) if hn.any() else None,
        "ln_reject_rate_other_homes": float((fits.ln_ks_p[~hn] <= 0.05).mean()),
        "n_high_night_in_sample": int(hn.sum()),
    }
    save_result("p4_fit_breaks", breaks)

    lines = [f"Stage 4 Part A summary ({time.time() - t0:.0f} s)", ""]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "Where the fit breaks:"] + [f"{k}: {v}" for k, v in breaks.items()]
    (RESULTS / "dist_where_it_breaks.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
