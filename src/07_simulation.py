"""
07_simulation.py - Stage 4, Part B: simulation study (false positives, coverage, power, stress test).

    python src/07_simulation.py                       # full run: 4 scenarios x 1,000 trials
    python src/07_simulation.py --trials 20           # quick check of the code (not for the report)
    python src/07_simulation.py --summarise-only      # redo the summary from simulation_trials.csv

Idea: build fake trials that look like ours but where WE set the true effect, run the real scoring
code (pipeline_lib.score_event, unchanged) and the same test and interval as Stage 5, and count how
often the method gets the right answer.

Ingredients from real data (all from before the results gate; no outcome is used):
    - the 200 fitted lognormal (mu, sigma) pairs from Part A        results/dist_fits.csv
    - sigma_day = median over the 200 households of the SD across normal days of that day's
      mean log-use                                                   results/dist_fits.csv
    - the real kept households and their group (1,114 ToU, 4,396 Std): ONLY the LCLid and group
      columns of results/household_scores_main.csv are read; the scores are never loaded
    - the real 63 usable High events (>= 3 matched days within +/-14), their half-hours and their
      matched days                                                   results/events.csv, matched_days.csv
    - each real household's real pattern of MISSING readings at those half-hours (H2013.npy), so the
      80%-coverage, matched-day and >=5-events rules act on the simulated data exactly as on the real
      data. Only which readings are missing is used, never their values.

One trial (guideline section 12, Part B):
    1. each simulated household gets a (mu, sigma) drawn at random from the 200 fitted pairs
    2. sigma_within = sqrt(max(sigma^2 - sigma_day^2, 0.01))
    3. for each event, for the event day and each matched day: one day effect d ~ N(0, sigma_day) per
       household; each half-hour = exp(mu + d + sigma_within * z), z ~ N(0, 1)
    4. ToU households, event day only: readings x (1 - delta / expected use), so the average
       reduction is delta kWh per half-hour (delta = 0 or T = 0.0215)
    5. the values go into a small matrix and score_event() is called exactly as in Stage 3
    6. household score = mean of valid event scores if >= 5; one-sided Welch t-test (H1: ToU mean <
       Std mean, alpha 0.05) and 95% percentile bootstrap interval for ToU - Std (households
       resampled within each group, 2,000 resamples)
    7. record: was H1 rejected? did the interval contain the true effect -delta?

Stress scenarios add, on top: 1.2% of readings set to exactly 0, and the top 5% of households (by
expected use) multiplied by 3 (a heavy upper tail across homes).

The small matrix: score_event reads column s + 48*k for "the same clock time k days away". The
simulated matrix holds the event day as day-block 0 and the m matched days as day-blocks 1..m, so it
is called with shifts 1..m. Columns not used by score_event are never read. This is a storage
shortcut only; the function and its rules are untouched.
"""
import argparse
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy import stats

from config import (EVENTS, H2013, HOUSEHOLDS, MATCHED, MATCH_WINDOW_MAIN, MIN_EVENTS,
                    MIN_MATCHED_DAYS, RESULTS, SEED, TARIFFS_USED)
from pipeline_lib import save_result, score_event

T_KW = 0.043                 # break-even threshold, kW per household
T = T_KW / 2                 # = 0.0215 kWh per half-hour
ALPHA = 0.05
N_BOOT = 2000
ZERO_SHARE_STRESS = 0.012
TOP_SHARE_STRESS = 0.05
TOP_FACTOR_STRESS = 3.0
SCENARIOS = {                # name: (true delta, stress?)
    "null": (0.0, False),
    "threshold": (T, False),
    "stress_null": (0.0, True),
    "stress_threshold": (T, True),
}
PASS_FP = (0.036, 0.064)
PASS_COV = (0.936, 0.964)
OUT_TRIALS = RESULTS / "simulation_trials.csv"

G = {}                       # read-only inputs shared with worker processes (set in load_inputs)


# ------------------------------------------------------------------ inputs
def load_inputs():
    fits = pd.read_csv(RESULTS / "dist_fits.csv")
    pairs = fits[["ln_mu", "ln_sigma"]].to_numpy()
    sigma_day = float(fits.sd_day_mean_log.median())

    # kept households and their group: LCLid and group columns only (results gate)
    kept = pd.read_csv(RESULTS / "household_scores_main.csv", usecols=["LCLid", "group", "tariff"])
    kept = kept[kept.tariff == "High"].drop(columns="tariff")
    hh = pd.read_csv(HOUSEHOLDS)
    kept = kept.merge(hh[["LCLid", "row"]], on="LCLid", how="left").sort_values(["group", "LCLid"])
    is_tou = (kept.group == "ToU").to_numpy()
    rows = kept.row.to_numpy()

    ev = pd.read_csv(EVENTS)
    ev = ev[ev.tariff == "High"]  # H1 calibration remains High-only when Low scores are restored
    md = pd.read_csv(MATCHED)
    md = md[md.shift_days.abs() <= MATCH_WINDOW_MAIN]
    shifts = md.groupby("event_id").shift_days.apply(lambda s: sorted(s)).to_dict()

    H = np.load(H2013, mmap_mode="r")
    events = []
    for e in ev.itertuples(index=False):
        ks = shifts.get(e.event_id, [])
        if len(ks) < MIN_MATCHED_DAYS:          # cannot give a valid score to anyone (6 events)
            continue
        S = np.arange(int(e.first_slot), int(e.first_slot) + int(e.n_slots))
        days = [0] + list(ks)                    # event day first, then the matched days
        cols = np.stack([S + 48 * k for k in days])                     # (m+1) x n_slots
        present = ~np.isnan(np.asarray(H[np.ix_(rows, cols.ravel())], dtype=np.float32))
        present = present.reshape(len(rows), len(days), len(S))
        events.append({"event_id": e.event_id, "offset": int(e.first_slot) % 48,
                       "n_slots": len(S), "m": len(ks), "present": present})
    del H
    G.update(pairs=pairs, sigma_day=sigma_day, is_tou=is_tou, events=events,
             n_tou=int(is_tou.sum()), n_std=int((~is_tou).sum()))
    return G


# ------------------------------------------------------------------ the test (same as Stage 5)
def welch_and_interval(tou, std, rng, n_boot=N_BOOT):
    """One-sided Welch t-test (H1: mean ToU < mean Std) and 95% percentile bootstrap interval for
    mean ToU - mean Std, resampling households within each group. Keep identical to Stage 5."""
    t, p = stats.ttest_ind(tou, std, equal_var=False, alternative="less")
    bt = tou[rng.integers(0, len(tou), size=(n_boot, len(tou)))].mean(axis=1)
    bs = std[rng.integers(0, len(std), size=(n_boot, len(std)))].mean(axis=1)
    lo, hi = np.percentile(bt - bs, [2.5, 97.5])
    return float(tou.mean() - std.mean()), float(t), float(p), float(lo), float(hi)


# ------------------------------------------------------------------ one trial
def run_trial(task):
    scenario, trial, seed = task
    delta, stress = SCENARIOS[scenario]
    rng = np.random.default_rng(seed)
    pairs, sd_day, is_tou = G["pairs"], G["sigma_day"], G["is_tou"]
    n = len(is_tou)

    # 1-2. household parameters
    k = rng.integers(0, len(pairs), size=n)
    mu, sig = pairs[k, 0], pairs[k, 1]
    sig_w = np.sqrt(np.maximum(sig ** 2 - sd_day ** 2, 0.01))
    expected = np.exp(mu + (sd_day ** 2 + sig_w ** 2) / 2)   # mean reading of the simulated household
    scale = np.ones(n)
    zero_p = 0.0
    if stress:
        top = expected >= np.quantile(expected, 1 - TOP_SHARE_STRESS)
        scale[top] = TOP_FACTOR_STRESS
        zero_p = ZERO_SHARE_STRESS
    exp_use = expected * scale * (1 - zero_p)                # expected reading after the stress changes
    # 4. multiplier for ToU event-day readings; a household using less than delta on average can
    #    cut at most all of it (never happened with the fitted pairs, but guarded)
    factor = np.where(is_tou, 1 - np.minimum(delta / exp_use, 1.0), 1.0)
    true_effect = -float(np.mean(np.minimum(delta, exp_use)[is_tou])) if delta > 0 else 0.0
    n_clipped = int(np.sum(is_tou & (exp_use < delta))) if delta > 0 else 0

    sums = np.zeros(n)
    counts = np.zeros(n, dtype=np.int64)
    for e in G["events"]:
        m, ns, off = e["m"], e["n_slots"], e["offset"]
        nd = m + 1
        # 3. day effects and half-hours
        d = rng.normal(0.0, sd_day, size=(n, nd))
        z = rng.standard_normal(size=(n, nd, ns))
        X = np.exp(mu[:, None, None] + d[:, :, None] + sig_w[:, None, None] * z) * scale[:, None, None]
        if stress:
            X[rng.random(size=X.shape) < zero_p] = 0.0
        X[:, 0, :] *= factor[:, None]
        X[~e["present"]] = np.nan                            # the real missing-reading pattern
        # 5. small matrix: day-block j starts at column 48*j; event at offset .. offset+ns-1
        Hs = np.empty((n, 48 * m + off + ns))
        S = off + np.arange(ns)
        for j in range(nd):
            Hs[:, S + 48 * j] = X[:, j, :]
        r = score_event(Hs, S, list(range(1, nd)))
        v = r["valid"]
        sums[v] += r["score"][v]
        counts[v] += 1

    # 6. household scores and the test
    ok = counts >= MIN_EVENTS
    score = np.where(ok, sums / np.maximum(counts, 1), np.nan)
    tou, std = score[ok & is_tou], score[ok & ~is_tou]
    est, t, p, lo, hi = welch_and_interval(tou, std, rng)
    return {
        "scenario": scenario, "trial": trial, "delta": delta, "true_effect": true_effect,
        "n_tou": len(tou), "n_std": len(std), "estimate": est, "t": t, "p": p,
        "ci_lo": lo, "ci_hi": hi, "rejected": p < ALPHA,
        "covers_true": lo <= true_effect <= hi, "covers_minus_delta": lo <= -delta <= hi,
        "n_clipped": n_clipped,
    }


def init_worker():
    load_inputs()


# ------------------------------------------------------------------ summary
def wilson(k, n, z=1.96):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [float(c - h), float(c + h)]


def summarise(df):
    out = {}
    lines = ["Stage 4 Part B: simulation study", "",
             f"{'scenario':<18}{'trials':>7}{'true effect':>13}{'mean est.':>11}{'rejected':>10}"
             f"{'coverage':>10}{'pass':>6}"]
    for sc, d in df.groupby("scenario", sort=False):
        delta = float(d.delta.iloc[0])
        n = len(d)
        rej, cov = int(d.rejected.sum()), int(d.covers_true.sum())
        s = {
            "trials": n, "delta": delta, "true_effect_mean": float(d.true_effect.mean()),
            "mean_estimate": float(d.estimate.mean()),
            "bias": float((d.estimate - d.true_effect).mean()),
            "sd_estimate": float(d.estimate.std(ddof=1)),
            "mean_interval_width": float((d.ci_hi - d.ci_lo).mean()),
            "rejection_rate": rej / n, "rejection_rate_95ci": wilson(rej, n),
            "coverage": cov / n, "coverage_95ci": wilson(cov, n),
            "coverage_vs_minus_delta": float(d.covers_minus_delta.mean()),
            "households_tou_median": float(d.n_tou.median()),
            "households_std_median": float(d.n_std.median()),
            "trials_with_clipped_households": int((d.n_clipped > 0).sum()),
        }
        if delta == 0:
            s["false_positive_rate"] = s["rejection_rate"]
            # smallest true reduction detected with 80% power (one-sided 5%), from the spread of
            # the estimate when there is no effect: (z_0.95 + z_0.80) x SD
            z = stats.norm.ppf(1 - ALPHA) + stats.norm.ppf(0.80)
            s["min_detectable_effect_80pct_kwh_per_hh"] = float(z * s["sd_estimate"])
            s["min_detectable_effect_80pct_kw"] = float(2 * z * s["sd_estimate"])
            s["pass_false_positive"] = PASS_FP[0] <= s["rejection_rate"] <= PASS_FP[1]
            s["pass_coverage"] = PASS_COV[0] <= s["coverage"] <= PASS_COV[1]
            ok = s["pass_false_positive"]
        else:
            s["power"] = s["rejection_rate"]
            s["pass_coverage"] = PASS_COV[0] <= s["coverage"] <= PASS_COV[1]
            ok = s["pass_coverage"]
        s["pass"] = bool(ok)
        out[sc] = s
        lines.append(f"{sc:<18}{n:>7}{s['true_effect_mean']:>13.4f}{s['mean_estimate']:>11.4f}"
                     f"{s['rejection_rate']:>10.3f}{s['coverage']:>10.3f}{'yes' if ok else 'NO':>6}")
    lines += ["", f"Pass ranges: false positives {PASS_FP[0]:.1%}-{PASS_FP[1]:.1%} (delta = 0); "
              f"coverage {PASS_COV[0]:.1%}-{PASS_COV[1]:.1%} (delta = T).",
              "Effects in kWh per half-hour, ToU minus Std (negative = ToU uses less). "
              f"T = {T_KW} kW = {T} kWh per half-hour."]
    return out, "\n".join(lines)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=1000)
    ap.add_argument("--scenarios", nargs="+", default=list(SCENARIOS), choices=list(SCENARIOS))
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--out", default=str(OUT_TRIALS))
    ap.add_argument("--summarise-only", action="store_true")
    args = ap.parse_args()
    out = pd.io.common.stringify_path(args.out)

    if not args.summarise_only:
        t0 = time.time()
        # one independent, reproducible seed per (scenario, trial): results do not depend on the
        # number of workers or the order trials finish in
        root = np.random.SeedSequence(SEED)
        scen_seqs = root.spawn(len(SCENARIOS))
        tasks = []
        for name, ss in zip(SCENARIOS, scen_seqs):
            if name in args.scenarios:
                tasks += [(name, i, s) for i, s in enumerate(ss.spawn(args.trials))]
        print(f"{len(tasks)} trials on {args.workers} worker(s)")
        rows = []
        with Pool(args.workers, initializer=init_worker) as pool:
            for i, r in enumerate(pool.imap_unordered(run_trial, tasks, chunksize=4)):
                rows.append(r)
                if (i + 1) % 50 == 0 or i + 1 == len(tasks):
                    pd.DataFrame(rows).to_csv(out + ".partial", index=False)
                    el = time.time() - t0
                    print(f"  {i + 1}/{len(tasks)} trials, {el / 60:.1f} min, "
                          f"~{el / (i + 1) * (len(tasks) - i - 1) / 60:.0f} min left", flush=True)
        df = pd.DataFrame(rows)
        df["scenario"] = pd.Categorical(df.scenario, categories=list(SCENARIOS), ordered=True)
        df = df.sort_values(["scenario", "trial"])
        df.to_csv(out, index=False, float_format="%.6g")
        if os.path.exists(out + ".partial"):
            os.remove(out + ".partial")
        print(f"wrote {out} ({(time.time() - t0) / 60:.1f} min)")

    df = pd.read_csv(out, keep_default_na=False, na_values=[""])   # "null" is a scenario name, not NaN
    df["scenario"] = pd.Categorical(df.scenario, categories=list(SCENARIOS), ordered=True)
    summary, text = summarise(df.sort_values(["scenario", "trial"]))
    if out == str(OUT_TRIALS):
        G_sigma = float(pd.read_csv(RESULTS / "dist_fits.csv").sd_day_mean_log.median())
        save_result("p4_simulation", {"sigma_day": G_sigma, "T_kWh_per_half_hour": T,
                                      "bootstrap_resamples": N_BOOT, "scenarios": summary})
        (RESULTS / "simulation_summary.txt").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
