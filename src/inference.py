"""Shared inference definitions, independent of files and plotting.

Bootstrap units are households. We never sample individual half-hour readings here.
Signed effects are ToU minus Std; High reductions reverse the sign and multiply by two.
"""
import numpy as np
from scipy import stats

from config import BOOTSTRAP_DRAWS, SEED, THRESHOLDS_KW


def boot_diff(tou, std, B=BOOTSTRAP_DRAWS, seed=SEED, batch=128, rng=None):
    """Percentile interval for a difference of equally weighted household means.

    Each draw preserves each group's observed sample size. Batching bounds memory
    and handles the final partial batch (the guideline example dropped leftovers).
    A supplied RNG supports independent, repeatable nested coverage trials.
    """
    if B < 2 or batch < 1:
        raise ValueError("Need B >= 2 and batch >= 1")
    tou, std = np.asarray(tou, float), np.asarray(std, float)
    if min(len(tou), len(std)) < 2 or not all(np.isfinite(x).all() for x in (tou, std)):
        raise ValueError("Bootstrap requires finite household scores in both groups")
    rng = np.random.default_rng(seed) if rng is None else rng
    boot = np.empty(B)
    for first in range(0, B, batch):
        count = min(batch, B - first)
        t = tou[rng.integers(0, len(tou), (count, len(tou)))].mean(axis=1)
        s = std[rng.integers(0, len(std), (count, len(std)))].mean(axis=1)
        boot[first:first + count] = t - s
    return np.percentile(boot, [2.5, 97.5]), boot


def reduction_interval(ci):
    """Multiplying an interval by a negative constant reverses its endpoints."""
    return [-2 * float(ci[1]), -2 * float(ci[0])]


def decision(ci_reduction_kw, threshold=THRESHOLDS_KW["central"]):
    """Exactly implement the prespecified three-way business decision."""
    lo, hi = ci_reduction_kw
    if lo > hi:
        raise ValueError("Interval endpoints must be in ascending order")
    if lo >= threshold:
        return "offer"
    if hi < threshold:
        return "do not offer"
    return "inconclusive: bigger pilot"


def effect_summary(tou, std, normal_tou, ci):
    """Compute units once, so report, tests and sensitivity tables cannot diverge.

    The percent interval fixes normal_tou at its observed value, as prespecified.
    This is a rescaled difference interval, not an interval for an estimated ratio.
    """
    delta = float(np.mean(tou) - np.mean(std))
    ci = np.asarray(ci, float)
    reduction = -2 * delta
    return {"n_tou": len(tou), "n_std": len(std),
            "mean_tou": float(np.mean(tou)), "mean_std": float(np.mean(std)),
            "normal_tou": float(normal_tou), "effect_kwh": delta,
            "ci_kwh": ci.tolist(), "effect_kw": 2 * delta,
            "ci_kw": (2 * ci).tolist(), "pct": 100 * delta / normal_tou,
            "ci_pct": (100 * ci / normal_tou).tolist(),
            "effect_mw_50k": 100 * delta, "ci_effect_mw_50k": (100 * ci).tolist(),
            "reduction_kw": reduction, "ci_reduction_kw": reduction_interval(ci),
            "reduction_pct": -100 * delta / normal_tou,
            "ci_reduction_pct": (-100 * ci[::-1] / normal_tou).tolist(),
            "reduction_mw_50k": reduction * 50,
            "ci_reduction_mw_50k": (np.array(reduction_interval(ci)) * 50).tolist()}


def run_tests(tou, std, tariff):
    """Welch compares means; Mann-Whitney compares rank distributions, not means.

    Agreement supports robustness but does not make the hypotheses identical.
    Cohen's d uses the explicitly requested pooled SD, despite unequal-variance Welch.
    """
    alternative = "less" if tariff == "High" else "greater"
    w = stats.ttest_ind(tou, std, equal_var=False, alternative=alternative)
    m = stats.mannwhitneyu(tou, std, alternative=alternative, method="asymptotic")
    vt, vs = np.var(tou, ddof=1), np.var(std, ddof=1)
    sp = np.sqrt(((len(tou)-1)*vt + (len(std)-1)*vs) / (len(tou)+len(std)-2))
    return {"alternative": alternative, "welch_t": float(w.statistic),
            "welch_df": float(w.df), "welch_p": float(w.pvalue),
            "mannwhitney_u": float(m.statistic), "mannwhitney_p": float(m.pvalue),
            "cohens_d": float((np.mean(tou)-np.mean(std))/sp),
            "sd_tou": float(np.sqrt(vt)), "sd_std": float(np.sqrt(vs)),
            "sd_ratio_tou_over_std": float(np.sqrt(vt/vs))}
