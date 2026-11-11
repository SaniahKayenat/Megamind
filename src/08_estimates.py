"""Lin's estimates, percentile intervals, business decision and coverage check.

Run from the project root: python src/08_estimates.py
Inputs: household_scores_main.csv, committed simulation evidence.
Outputs: estimates.csv, boot_{high,low}.npy, coverage_trials.csv, results.json,
         decision.png and sensitivity-ready shared inference functions.

The coverage exercise draws from centered empirical household distributions. Its known
target is the observed difference, not an unknown population effect. It assesses the
bootstrap under that empirical model and cannot remove self-selection or shared shocks.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from check_gate import require_gate
from config import (BOOTSTRAP_DRAWS, COVERAGE_BOOTSTRAP_DRAWS, COVERAGE_TRIALS,
                    FIGURES, RESULTS, SEED, THRESHOLDS_KW)
from inference import boot_diff, decision, effect_summary
from pipeline_lib import group_scores, save_result

G = {}


def initialise_coverage(inputs):
    """Each worker receives household arrays once; no files are mutated by workers."""
    G.update(inputs)


def coverage_trial(task):
    """One outer resample plus its own inner bootstrap, both seeded independently."""
    tariff, trial, seed = task
    tou, std = G[tariff]
    delta = float(tou.mean() - std.mean())
    # Remove each empirical group mean, then impose the known target on ToU.
    population_tou = tou - tou.mean() + delta
    population_std = std - std.mean()
    rng = np.random.default_rng(seed)
    t = rng.choice(population_tou, len(tou), replace=True)
    s = rng.choice(population_std, len(std), replace=True)
    ci, _ = boot_diff(t, s, B=COVERAGE_BOOTSTRAP_DRAWS, rng=rng)
    return {"tariff": tariff, "trial": trial, "target": delta,
            "estimate": float(t.mean()-s.mean()), "ci_lo": float(ci[0]),
            "ci_hi": float(ci[1]), "covers_target": bool(ci[0] <= delta <= ci[1])}


def coverage_summary(trials):
    """Keep failed checks and their uncertainty, rather than rerunning to improve them."""
    summaries = {}
    for tariff, d in trials.groupby("tariff", sort=True):
        rate = float(d.covers_target.mean())
        mc_se = float(np.sqrt(rate*(1-rate)/len(d)))
        summaries[tariff] = {"trials": len(d), "inner_bootstrap_draws": COVERAGE_BOOTSTRAP_DRAWS,
            "coverage": rate, "mc_se": mc_se,
            "mc_95_interval_normal": [max(0,rate-1.96*mc_se), min(1,rate+1.96*mc_se)],
            "nominal_95pct_margin_at_1000_trials": 0.014,
            "within_prespecified_range": bool(0.936 <= rate <= 0.964),
            "target": float(d.target.iloc[0]),
            "interpretation": "conditional on empirical household distributions"}
    return summaries


def decision_figure(high):
    """A point and whisker against the economic threshold, with costs shown as a band."""
    FIGURES.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    lo, hi = high["ci_reduction_kw"]
    point = high["reduction_kw"]
    ax.axvspan(THRESHOLDS_KW["low"], THRESHOLDS_KW["high"], color="#e2e8f0",
               label="Range of break-even thresholds")
    ax.axvline(THRESHOLDS_KW["central"], color="#b45309", ls="--", lw=2,
               label="Central threshold: 0.043 kW")
    ax.errorbar(point, 0, xerr=[[point-lo], [hi-point]], fmt="o", color="#146c70",
                 markersize=10, capsize=9, lw=3)
    ax.annotate(f"{point:.3f} kW\n95% CI {lo:.3f} to {hi:.3f}", (point,0),
                xytext=(0,28), textcoords="offset points", ha="center", fontsize=12)
    ax.set_xlim(min(-0.01,lo-0.025), max(0.20,hi+0.025))
    ax.set_ylim(-0.5,0.65)
    ax.set_yticks([])
    ax.set_xlabel("High-event demand reduction per household (kW)", fontsize=12)
    ax.set_title("Demand reduction and the break-even decision", loc="left", fontsize=16)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    for side in ["top","left","right"]: ax.spines[side].set_visible(False)
    fig.text(0.12,0.02,"Households likely to sign up. Interval resamples households within tariff groups.",
             fontsize=9,color="#475569")
    fig.tight_layout(rect=(0,0.06,1,1))
    fig.savefig(FIGURES/"decision.png", dpi=180)
    fig.savefig(FIGURES/"decision.svg")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers",type=int,default=min(2,os.cpu_count() or 1))
    args=ap.parse_args()
    if args.workers < 1: ap.error("--workers must be positive")
    require_gate()
    summaries, inputs = {}, {}
    for tariff in ["High","Low"]:
        tou,std,normal=group_scores("main",tariff)
        ci,boot=boot_diff(tou,std)
        np.save(RESULTS/f"boot_{tariff.lower()}.npy",boot)
        result=effect_summary(tou,std,normal,ci)
        result["bootstrap_draws"]=BOOTSTRAP_DRAWS
        if tariff=="High":
            result["decisions"]={case:decision(result["ci_reduction_kw"],t)
                                 for case,t in THRESHOLDS_KW.items()}
        summaries[tariff]=result
        inputs[tariff]=(tou,std)
        prefix=tariff.lower()
        for key in ["effect_kwh","effect_kw","ci_kw","pct","effect_mw_50k"]:
            # Keep the guideline's simple keys in addition to the complete structured result.
            mapped={"effect_kwh":f"effect_{prefix}_kwh","effect_kw":f"effect_{prefix}_kw",
                    "ci_kw":f"ci_{prefix}_kw","pct":f"pct_{prefix}",
                    "effect_mw_50k":f"mw_50k_{prefix}"}[key]
            save_result(mapped,result[key])
        print(f"{tariff}: estimates and 10,000 bootstrap draws saved.",flush=True)
    high=summaries["High"]
    for case,value in high["decisions"].items():
        save_result({"central":"decision_central","low":"decision_low_T","high":"decision_high_T"}[case],value)
    for key in ["reduction_kw","ci_reduction_kw","reduction_mw_50k"]:
        save_result(key.replace("reduction_","reduction_high_"),high[key])
    decision_figure(high)
    pd.DataFrame([dict(tariff=t,**r) for t,r in summaries.items()]).to_csv(
        RESULTS/"estimates.csv",index=False,float_format="%.17g")
    save_result("estimates",summaries)

    # Independent trial seeds make output independent of scheduling and core count.
    roots=np.random.SeedSequence(SEED).spawn(2)
    tasks=[(tariff,i,seed) for tariff,root in zip(["High","Low"],roots)
           for i,seed in enumerate(root.spawn(COVERAGE_TRIALS))]
    rows=[]
    with ProcessPoolExecutor(max_workers=args.workers,initializer=initialise_coverage,
                             initargs=(inputs,)) as pool:
        for row in pool.map(coverage_trial,tasks,chunksize=5):
            rows.append(row)
            if len(rows)%100==0:
                print(f"Coverage check: {len(rows)}/{len(tasks)} trials complete.",flush=True)
    trials=pd.DataFrame(rows).sort_values(["tariff","trial"])
    trials.to_csv(RESULTS/"coverage_trials.csv",index=False,float_format="%.17g")
    cov=coverage_summary(trials)
    save_result("coverage_resampling",cov)
    print(json.dumps(cov,indent=2),flush=True)


if __name__=="__main__":
    main()
