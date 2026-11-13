"""Supporting work for Javed: prespecified High-event regression and validation.

One event is one row, not one household. HC3 addresses unequal residual variance.
Leave-one-month-out predictions test generalisation to an unseen month and compare
against the training mean. Calendar month is a fold label, never a predictor.
This descriptive observational model is not a causal model of timing or a forecast.
"""
import os
from config import ROOT
os.environ.setdefault("MPLCONFIGDIR", str(ROOT/"tmp"/"matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from matplotlib.ticker import MaxNLocator
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

from check_gate import require_gate
from config import FIGURES, RESULTS
from pipeline_lib import log_test, save_result


def design(d,predictors):
    return sm.add_constant(d[predictors].astype(float),has_constant="add")


def coefficients(fit,label):
    """Signed kW effects and reduction changes are both explicit in the output."""
    ci=fit.conf_int()
    rows=[]
    for name in fit.params.index:
        b=float(fit.params[name]); lo,hi=ci.loc[name].to_numpy(dtype=float)
        p=float(fit.pvalues[name]); t=float(fit.tvalues[name])
        rows.append({"fit":label,"term":name,"coefficient_kwh":b,"se_hc3":float(fit.bse[name]),
            "ci_lo_kwh":float(lo),"ci_hi_kwh":float(hi),"p":p,
            "signed_effect_change_kw":2*b,"signed_ci_lo_kw":2*float(lo),"signed_ci_hi_kw":2*float(hi),
            "reduction_change_kw":-2*b,"reduction_ci_lo_kw":-2*float(hi),"reduction_ci_hi_kw":-2*float(lo)})
        log_test("Lin (supporting Javed)","event regression",label,f"HC3 coefficient: {name}",t,p,b,
                 "Prespecified descriptive OLS; effect in kWh per half-hour; coefficient p-values exploratory.")
    return rows


def independent_columns(d,predictors):
    """In a CV training fold, drop unidentifiable terms without examining the outcome."""
    kept=[]; rank=1
    for p in predictors:
        candidate=design(d,kept+[p])
        new_rank=np.linalg.matrix_rank(candidate)
        if new_rank>rank:
            kept.append(p); rank=new_rank
    return kept


def main():
    require_gate()
    d=pd.read_csv(RESULTS/"event_effects_main.csv",parse_dates=["start"])
    d=d[(d.tariff=="High") & d.effect.notna()].sort_values("start").reset_index(drop=True)
    predictors=["evening","hours","winter","low_before"]
    x=design(d,predictors)
    vifs={p:float(variance_inflation_factor(x.to_numpy(),i))
          for i,p in enumerate(x.columns) if p!="const"}
    dropped=[]
    if any(v>5 for v in vifs.values()):
        predictors.remove("hours"); dropped.append("hours")
    if np.linalg.matrix_rank(design(d,predictors))!=len(predictors)+1:
        raise ValueError("Main regression not identified; document before changing the fixed model")
    fit=sm.OLS(d.effect,design(d,predictors)).fit(cov_type="HC3")
    rows=coefficients(fit,"main")
    cooks=np.asarray(fit.get_influence().cooks_distance[0])
    influential=cooks>4/len(d)
    reduced=d.loc[~influential]
    if influential.any() and len(reduced)>len(predictors)+1:
        refit=sm.OLS(reduced.effect,design(reduced,predictors)).fit(cov_type="HC3")
        rows+=coefficients(refit,"without influential events")

    # Each held-out month must use the mean and fitted coefficients from other months.
    predictions=[]
    folds=[]
    for month in sorted(d.month.unique()):
        train=d[d.month!=month]; test=d[d.month==month]
        kept=independent_columns(train,predictors)
        f=sm.OLS(train.effect,design(train,kept)).fit()
        pred=f.predict(design(test,kept)); base=float(train.effect.mean())
        for index,value in pred.items():
            predictions.append({"event_id":d.loc[index,"event_id"],"month":int(month),
                                "observed":float(d.loc[index,"effect"]),"model":float(value),"baseline":base})
        folds.append({"month":int(month),"train_events":len(train),"test_events":len(test),
                      "dropped_in_fold":[p for p in predictors if p not in kept]})
    pred=pd.DataFrame(predictions)
    rmse=float(np.sqrt(np.mean((pred.observed-pred.model)**2)))
    baseline=float(np.sqrt(np.mean((pred.observed-pred.baseline)**2)))
    conclusion=("timing/length predict response better than the mean baseline" if rmse<baseline
                else "timing/length don't predict response")
    result={"n_events":len(d),"predictors":predictors,"n_parameters":len(fit.params),
            "vif_before_drop":vifs,"dropped_predictors":dropped,"coefficients":rows,
            "durbin_watson":float(durbin_watson(fit.resid)),"cooks_cutoff":4/len(d),
            "influential_events":d.loc[influential,"event_id"].tolist(),
            "cv_rmse_model_kwh":rmse,"cv_rmse_baseline_kwh":baseline,
            "cv_rmse_model_kw":2*rmse,"cv_rmse_baseline_kw":2*baseline,
            "cv_rmse_improvement_fraction":1-rmse/baseline,
            "cv_folds":folds,"conclusion":conclusion}
    pd.DataFrame(rows).to_csv(RESULTS/"regression_coefficients_supporting.csv",index=False,float_format="%.17g")
    pred.to_csv(RESULTS/"regression_cv_predictions_supporting.csv",index=False,float_format="%.17g")
    pd.DataFrame({"event_id":d.event_id,"cooks_distance":cooks,"flagged":influential}).to_csv(
        RESULTS/"regression_influence_supporting.csv",index=False,float_format="%.17g")
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    axes[0].scatter(fit.fittedvalues,fit.resid,color="#146c70")
    axes[0].axhline(0,color="gray",ls="--")
    axes[0].set(xlabel="Fitted effect (kWh per half-hour)",ylabel="Residual",title="Residuals vs fitted")
    stats.probplot(fit.resid,dist="norm",plot=axes[1]); axes[1].set_title("Residual Q-Q")
    axes[2].stem(np.arange(len(d)),cooks)
    axes[2].axhline(4/len(d),color="#b45309",ls="--")
    axes[2].set(xlabel="Events in date order",ylabel="Cook's distance",title="Influential events")
    axes[0].xaxis.set_major_locator(MaxNLocator(4))
    for ax in axes:
        ax.tick_params(labelsize=9)
        ax.xaxis.label.set_fontsize(9)
        ax.yaxis.label.set_fontsize(9)
    fig.tight_layout(); fig.savefig(FIGURES/"model_diagnostics_supporting.png",dpi=170); plt.close(fig)
    save_result("regression",result)
    print(f"{len(d)} High events; CV model RMSE={rmse:.6g}, baseline={baseline:.6g}. {conclusion}")


if __name__=="__main__":
    main()
