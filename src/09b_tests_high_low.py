"""Supporting work for Arpan: assumptions, H1/H2 and all sensitivity runs.

One-sided Welch is primary. Mann-Whitney provides a rank-based check whose null
hypothesis differs. Every computed test, including reruns, is appended to the log.
Q-Q plots show shape and outliers; they do not establish household independence.
"""
import os
from config import ROOT
os.environ.setdefault("MPLCONFIGDIR", str(ROOT/"tmp"/"matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from matplotlib.ticker import MaxNLocator

from check_gate import require_gate
from config import FIGURES, RESULTS
from inference import boot_diff, decision, effect_summary, run_tests
from pipeline_lib import group_scores, log_test, save_result


def assumption_figures(tou,std,tariff):
    """Show observed household tails beside the sampling distribution of the mean difference."""
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,x,label in zip(axes[:2],[tou,std],["ToU","Std"]):
        stats.probplot(x,dist="norm",plot=ax)
        ax.set_title(f"{label}: household scores")
        ax.set_ylabel("Score (kWh per half-hour)")
    boot=np.load(RESULTS/f"boot_{tariff.lower()}.npy")
    axes[2].hist(boot,bins=45,color="#146c70",edgecolor="white")
    axes[2].set_title("Bootstrap difference of means")
    axes[2].set_xlabel("ToU minus Std (kWh per half-hour)")
    axes[2].xaxis.set_major_locator(MaxNLocator(4))
    for ax in axes:
        ax.tick_params(labelsize=9)
        ax.xaxis.label.set_fontsize(9)
        ax.yaxis.label.set_fontsize(9)
    fig.suptitle(f"{tariff} events: assumptions and sampling uncertainty")
    fig.tight_layout()
    fig.savefig(FIGURES/f"assumptions_{tariff.lower()}.png",dpi=160)
    plt.close(fig)
    return {"score_skew_tou":float(stats.skew(tou)),"score_skew_std":float(stats.skew(std)),
            "bootstrap_skew":float(stats.skew(boot)),
            "bootstrap_excess_kurtosis":float(stats.kurtosis(boot)),
            "independence": "assumed across households; shared event shocks remain a limitation"}


def main():
    require_gate()
    FIGURES.mkdir(exist_ok=True)
    rows=[]
    assumptions={}
    for tariff in ["High","Low"]:
        for variant in ["main","A","B","C","D"]:
            tou,std,normal=group_scores(variant,tariff)
            ci,_=boot_diff(tou,std)
            effect=effect_summary(tou,std,normal,ci)
            tests=run_tests(tou,std,tariff)
            hypothesis="H1" if tariff=="High" else "H2"
            for label,stat,p in [("welch_"+tests["alternative"],tests["welch_t"],tests["welch_p"]),
                                  ("mannwhitney_"+tests["alternative"],tests["mannwhitney_u"],tests["mannwhitney_p"])]:
                log_test("Lin (supporting Arpan)",hypothesis,variant,label,stat,p,effect["effect_kwh"],
                         "Prespecified. Effect unit: kWh per half-hour. No multiple-testing correction.")
            agrees=bool((tests["welch_p"]<0.05)==(tests["mannwhitney_p"]<0.05))
            interval_support=bool(ci[1]<0 if tariff=="High" else ci[0]>0)
            row={"tariff":tariff,"run":variant,**effect,**tests,
                 "ci_lo_kwh":float(ci[0]),"ci_hi_kwh":float(ci[1]),
                 "ci_lo_kw":float(2*ci[0]),"ci_hi_kw":float(2*ci[1]),
                 "reduction_ci_lo_kw":effect["ci_reduction_kw"][0],
                 "reduction_ci_hi_kw":effect["ci_reduction_kw"][1],
                 "decision":decision(effect["ci_reduction_kw"]) if tariff=="High" else "not applicable",
                 "tests_agree_at_5pct":agrees,"two_sided_ci_supports_direction":interval_support,
                 "agreement_note":"Welch and MW test different nulls; a one-sided 5% test need not agree with a two-sided 95% CI."}
            # Tables use scalar columns; full structured estimates remain in results.json.
            rows.append({k:v for k,v in row.items() if not isinstance(v,list)})
            if variant=="main":
                assumptions[tariff]={**assumption_figures(tou,std,tariff),**tests}
    table=pd.DataFrame(rows)
    table.to_csv(RESULTS/"sensitivity_table_high_low.csv",index=False,float_format="%.17g")
    save_result("tests_and_sensitivity",table.to_dict(orient="records"))
    save_result("assumption_checks",assumptions)
    print(table[["tariff","run","effect_kw","welch_p","mannwhitney_p","decision"]].to_string(index=False))


if __name__=="__main__":
    main()
