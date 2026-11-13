"""
09_tests.py - Stage 5 hypothesis tests (Arpan). Follows guideline section 13.

Scope: H1 only (High-price events). Low events and H2 were dropped on 10 Nov 2026.

What it does
  1. Assumption checks: Q-Q plots of ToU and Std household scores, a histogram of
     Lin's bootstrap distribution of the difference (results/boot_high.npy), and the
     standard deviation of each group (their ratio justifies Welch).
  2. Main tests for H1: one-sided Welch t-test (primary), one-sided Mann-Whitney
     (check), Cohen's d with the pooled SD.
  3. Sensitivity table for main, A, B, C, D: households per group, reduction in kW,
     95% bootstrap interval (Lin's boot_diff), Welch p, Mann-Whitney p, decision vs T.
  4. Agreement check: do Welch, Mann-Whitney and the interval point the same way?
  5. Every test goes to the test log; every number goes to results.json (full precision).

Inputs (read only, never modified): Lin_Project/src (config, pipeline_lib, inference)
and Lin_Project/results (household_scores_{variant}.csv, boot_high.npy).
Outputs: this folder's results/ and figures/ only.

Run from this folder:
    python src/09_tests.py                 # final run: writes outputs and logs every test
    python src/09_tests.py --no-log        # while checking: writes outputs, logs nothing
    python src/09_tests.py --lin "<path to Lin_Project>"

Sign convention: effect = mean ToU score - mean Std score (kWh per half-hour);
negative = ToU used less. Reduction in kW = -2 x effect. T = 0.043 kW.
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]           # repo root (or Arpan's standalone folder)

ap = argparse.ArgumentParser(description="Stage 5 tests for H1 (Arpan)")
ap.add_argument("--lin", default=None,
                help="Lin_Project folder with src/ and results/ (default: found automatically)")
ap.add_argument("--no-log", action="store_true",
                help="do not append to the test log (use only while checking the script)")
args = ap.parse_args()

# Where Lin's repo can be: the organised project layout
# (Statistics Project/3_Integrated_Repo_Lin/Lin_Project, with this folder in 2_Team_Work/),
# or right next to this folder.
CANDIDATES = [HERE,                                  # team repository: run from its root
              HERE.parents[1] / "3_Integrated_Repo_Lin" / "Lin_Project",
              HERE.parent / "3_Integrated_Repo_Lin" / "Lin_Project",
              HERE.parent / "Lin_Project"]
if args.lin:
    LIN = Path(args.lin).resolve()
else:
    LIN = next((c.resolve() for c in CANDIDATES if (c / "src" / "config.py").exists()), None)
    if LIN is None:
        sys.exit("Could not find Lin_Project; pass --lin \"<path to Lin_Project>\"")
sys.path.insert(0, str(LIN / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(HERE / "tmp" / "matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

import pipeline_lib
from config import RESULTS as LIN_RESULTS, SEED, BOOTSTRAP_DRAWS, THRESHOLDS_KW
from inference import boot_diff, decision

# Inputs come from Lin's results; outputs are redirected to this folder, so Lin's
# results.json and test_log.csv are never touched. pipeline_lib's functions read these
# module-level names when they run, so overriding them here is enough.
OUT = HERE / "results"
FIG = HERE / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
IN_REPO = LIN == HERE.resolve()
if not IN_REPO:
    # standalone folder: keep the shared results.json and test_log.csv untouched
    pipeline_lib.RESULTS_JSON = OUT / "results.json"
    pipeline_lib.TEST_LOG = OUT / "test_log.csv"
    pipeline_lib.ROOT = HERE      # not a git repo -> git_commit is recorded as "unavailable"
# in the team repository the team results.json and test_log.csv are used (merge by key)
from pipeline_lib import group_scores, log_test, save_result

PERSON = "Arpan"
T_KW = THRESHOLDS_KW["central"]   # 0.043 kW per household
VARIANTS = {"main": "main analysis (matched days within +/-14)",
            "A": "matched days within +/-21",
            "B": "without the off-grid days 29 Jan, 9 Feb, 21 Mar",
            "C": "without high night-use homes",
            "D": "only households with >=300 days of 2013 data"}


def log(run, test, statistic, p, effect, note):
    if not args.no_log:
        log_test(PERSON, "H1", run, test, statistic, p, effect, note)


def h1_tests(tou, std):
    """Welch (primary), Mann-Whitney (check) and Cohen's d. ToU is always passed first."""
    w = stats.ttest_ind(tou, std, equal_var=False, alternative="less")
    m = stats.mannwhitneyu(tou, std, alternative="less")
    n1, n2 = len(tou), len(std)
    sp = np.sqrt(((n1 - 1) * tou.var(ddof=1) + (n2 - 1) * std.var(ddof=1)) / (n1 + n2 - 2))
    delta = tou.mean() - std.mean()
    return {"n_tou": n1, "n_std": n2,
            "mean_tou_kwh": float(tou.mean()), "mean_std_kwh": float(std.mean()),
            "effect_kwh": float(delta), "reduction_kw": float(-2 * delta),
            "welch_t": float(w.statistic), "welch_df": float(w.df), "welch_p": float(w.pvalue),
            "mannwhitney_u": float(m.statistic), "mannwhitney_p": float(m.pvalue),
            # common-language effect size: share of (ToU, Std) pairs where ToU is lower
            "prob_tou_lower": float(1 - m.statistic / (n1 * n2)),
            "cohens_d": float(delta / sp), "pooled_sd_kwh": float(sp),
            "sd_tou_kwh": float(tou.std(ddof=1)), "sd_std_kwh": float(std.std(ddof=1)),
            "sd_ratio_tou_over_std": float(tou.std(ddof=1) / std.std(ddof=1))}


# ------------------------------------------------------------------ 1. assumption checks
def assumption_checks(tou, std, normal_tou):
    boot = np.load(LIN_RESULTS / "boot_high.npy")

    # Q-Q plots of household scores (one value per household, as the tests use)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, x, label, n in zip(axes, [tou, std], ["ToU", "Std"], [len(tou), len(std)]):
        stats.probplot(x, dist="norm", plot=ax)
        ax.get_lines()[0].set(markersize=2.5, alpha=0.5, color="#146c70")
        ax.get_lines()[1].set(color="#b03a2e", linewidth=1.2)
        ax.set_title(f"{label} household scores (n = {n:,})", fontsize=11)
        ax.set_xlabel("Normal quantiles")
        ax.set_ylabel("Score (kWh per half-hour)")
    fig.suptitle("High events: household scores vs a normal distribution", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG / "qq_household_scores_high.png", dpi=160)
    plt.close(fig)

    # Histogram of the bootstrap distribution of the difference (should be bell-shaped)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.hist(boot, bins=50, density=True, color="#146c70", edgecolor="white", alpha=0.85)
    grid = np.linspace(boot.min(), boot.max(), 300)
    ax.plot(grid, stats.norm.pdf(grid, boot.mean(), boot.std(ddof=1)),
            color="#b03a2e", linewidth=1.5, label="normal curve, same mean and SD")
    ax.set_xlabel("Bootstrap difference, ToU - Std (kWh per half-hour)")
    ax.set_ylabel("Density")
    ax.set_title(f"High events: {len(boot):,} bootstrap resamples of the difference", fontsize=11)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "bootstrap_hist_high.png", dpi=160)
    plt.close(fig)

    sd_t, sd_s = tou.std(ddof=1), std.std(ddof=1)
    res = {"sd_tou_kwh": float(sd_t), "sd_std_kwh": float(sd_s),
           "sd_ratio_tou_over_std": float(sd_t / sd_s),
           "skew_tou": float(stats.skew(tou)), "skew_std": float(stats.skew(std)),
           "excess_kurtosis_tou": float(stats.kurtosis(tou)),
           "excess_kurtosis_std": float(stats.kurtosis(std)),
           "bootstrap_draws": int(len(boot)),
           "bootstrap_mean_kwh": float(boot.mean()), "bootstrap_sd_kwh": float(boot.std(ddof=1)),
           "bootstrap_skew": float(stats.skew(boot)),
           "bootstrap_excess_kurtosis": float(stats.kurtosis(boot)),
           "normal_use_tou_kwh": float(normal_tou),
           "independence": "one value per household by design; households are the "
                           "independent units. Shared event days are a remaining limitation.",
           "figures": ["figures/qq_household_scores_high.png", "figures/bootstrap_hist_high.png"]}
    save_result("p5_assumptions_high", res)
    return res, boot


# ------------------------------------------------------------------ 2-4. tests and sensitivity
def main():
    tou, std, normal_tou = group_scores("main", "High")
    assumptions, boot = assumption_checks(tou, std, normal_tou)

    rows = []
    for v, label in VARIANTS.items():
        tou, std, normal = group_scores(v, "High")
        r = h1_tests(tou, std)
        ci_kwh, _ = boot_diff(tou, std, B=BOOTSTRAP_DRAWS, seed=SEED)
        red_lo, red_hi = -2 * ci_kwh[1], -2 * ci_kwh[0]       # reduction interval in kW
        r.update({"run": v, "description": label,
                  "normal_use_tou_kwh": float(normal),
                  "pct_of_normal_use": float(-100 * r["effect_kwh"] / normal),
                  "ci_lo_kwh": float(ci_kwh[0]), "ci_hi_kwh": float(ci_kwh[1]),
                  "reduction_ci_lo_kw": float(red_lo), "reduction_ci_hi_kw": float(red_hi),
                  "decision_vs_T": decision([red_lo, red_hi], T_KW)})
        # Agreement: all three point to "ToU uses less" (or all do not)
        welch_says = r["welch_p"] < 0.05
        mw_says = r["mannwhitney_p"] < 0.05
        ci_says = ci_kwh[1] < 0                                  # whole interval below 0
        r["welch_supports_h1"], r["mw_supports_h1"], r["ci_excludes_zero"] = welch_says, mw_says, bool(ci_says)
        r["methods_agree"] = bool(welch_says == mw_says == ci_says)
        r["note"] = ("removes 10.7% of Std homes (476 of 4,443) but only 6.7% of ToU homes "
                     "(75 of 1,123)" if v == "C" else "")
        rows.append(r)

        kind = "prespecified main test" if v == "main" else f"sensitivity run {v}: re-test of H1, not a new hypothesis"
        unit = "effect = ToU - Std, kWh per half-hour"
        log(v, "welch_less", r["welch_t"], r["welch_p"], r["effect_kwh"], f"{kind}; {unit}")
        log(v, "mannwhitney_less", r["mannwhitney_u"], r["mannwhitney_p"], r["effect_kwh"], f"{kind}; check test; {unit}")

    cols = ["run", "description", "n_tou", "n_std", "mean_tou_kwh", "mean_std_kwh", "effect_kwh",
            "reduction_kw", "reduction_ci_lo_kw", "reduction_ci_hi_kw", "pct_of_normal_use",
            "welch_t", "welch_df", "welch_p", "mannwhitney_u", "mannwhitney_p", "prob_tou_lower",
            "cohens_d", "sd_tou_kwh", "sd_std_kwh", "sd_ratio_tou_over_std", "ci_lo_kwh", "ci_hi_kwh",
            "decision_vs_T", "welch_supports_h1", "mw_supports_h1", "ci_excludes_zero",
            "methods_agree", "note"]
    table = pd.DataFrame(rows)[list(dict.fromkeys(cols))]
    table.to_csv(OUT / "sensitivity_table.csv", index=False, float_format="%.17g")

    # One sentence for the agreement check
    if table.methods_agree.all():
        agreement = ("In all five runs, Welch, Mann-Whitney and the bootstrap interval point the same "
                     "way: ToU households used less than Std households during High events.")
    else:
        bad = ", ".join(table.loc[~table.methods_agree, "run"])
        agreement = (f"The methods disagree in run(s) {bad}; check whether a few extreme households "
                     "pull the mean (Welch) differently from the ranks (Mann-Whitney).")
    decisions = sorted(set(table.decision_vs_T))

    main_row = table[table.run == "main"].iloc[0].to_dict()
    save_result("p5_h1_main", {k: main_row[k] for k in cols if k in main_row})
    save_result("p5_sensitivity_table", table.to_dict(orient="records"))
    save_result("p5_agreement_check", {"all_agree": bool(table.methods_agree.all()),
                                       "sentence": agreement,
                                       "decisions_across_runs": decisions})

    # Short human-readable summary
    lines = ["Stage 5 tests (Arpan) - H1, High events only", "",
             f"Main: n = {main_row['n_tou']:,} ToU, {main_row['n_std']:,} Std",
             f"  effect (ToU - Std) = {main_row['effect_kwh']:.6f} kWh per half-hour",
             f"  reduction = {main_row['reduction_kw']:.4f} kW per household "
             f"(95% CI {main_row['reduction_ci_lo_kw']:.4f} to {main_row['reduction_ci_hi_kw']:.4f}), "
             f"{main_row['pct_of_normal_use']:.2f}% of normal use",
             f"  Welch t = {main_row['welch_t']:.3f}, df = {main_row['welch_df']:.1f}, one-sided p = {main_row['welch_p']:.3g}",
             f"  Mann-Whitney U = {main_row['mannwhitney_u']:.0f}, one-sided p = {main_row['mannwhitney_p']:.3g}; "
             f"P(ToU score < Std score) = {main_row['prob_tou_lower']:.3f}",
             f"  Cohen's d = {main_row['cohens_d']:.3f}",
             f"  SD ToU {assumptions['sd_tou_kwh']:.4f}, Std {assumptions['sd_std_kwh']:.4f}, "
             f"ratio {assumptions['sd_ratio_tou_over_std']:.2f}",
             f"  Bootstrap distribution: skew {assumptions['bootstrap_skew']:.3f}, "
             f"excess kurtosis {assumptions['bootstrap_excess_kurtosis']:.3f}",
             f"  Decision vs T = {T_KW} kW: {main_row['decision_vs_T']}", "",
             "Sensitivity runs (reduction in kW, 95% CI, Welch p, MW p, d, decision):"]
    for r in rows:
        lines.append(f"  {r['run']:>4}: {r['n_tou']:>5,} / {r['n_std']:>5,}  {r['reduction_kw']:.4f} "
                     f"[{r['reduction_ci_lo_kw']:.4f}, {r['reduction_ci_hi_kw']:.4f}]  "
                     f"{r['welch_p']:.2e}  {r['mannwhitney_p']:.2e}  {r['cohens_d']:.3f}  {r['decision_vs_T']}")
    lines += ["", "Run C " + rows[3]["note"] + ".", "", "Agreement: " + agreement,
              "", "Test log: " + ("not written (--no-log)" if args.no_log else str(pipeline_lib.TEST_LOG.name))]
    (OUT / "tests_summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
