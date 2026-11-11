"""Generate Lin's readable deliverables from saved analysis results.

No statistical calculation happens in prose. The script first saves count/reporting
context, then reads results.json for every reported finding. Rounding is display-only.
"""
import json
from pathlib import Path

import pandas as pd

from config import REPORTS, RESULTS, ROOT, SEED, THRESHOLDS_KW
from pipeline_lib import save_result

CI_WORDING="If we repeated this study many times, 95% of intervals built this way would contain the true effect."


def interval(ci,places=3):
    return f"{ci[0]:.{places}f} to {ci[1]:.{places}f}"


def pvalue(p):
    return f"{p:.3g}" if p>=1e-300 else "<1e-300"


def write(name,text):
    (REPORTS/name).write_text(text.strip()+"\n")


def main():
    REPORTS.mkdir(exist_ok=True)
    events=pd.read_csv(RESULTS/"events.csv")
    counts=pd.read_csv(RESULTS/"matched_counts.csv")
    exclusions={v:pd.read_csv(RESULTS/f"exclusions_{v}.csv").fillna(0).to_dict(orient="records")
                for v in ["main","A","B","C","D"]}
    settings={"seed":SEED,"thresholds_kw":THRESHOLDS_KW,"scale_households":50_000,
              "events_total":events.groupby("tariff").size().to_dict(),
              "events_usable_14":counts[counts.n_matched_14>=3].groupby("tariff").size().to_dict(),
              "events_usable_21":counts[counts.n_matched_21>=3].groupby("tariff").size().to_dict(),
              "normal_days":len(pd.read_csv(RESULTS/"normal_days.csv")),"exclusions":exclusions}
    save_result("reporting_context",settings)
    d=json.loads((RESULTS/"results.json").read_text())
    high,low=d["estimates"]["High"],d["estimates"]["Low"]
    ch,cl=d["coverage_resampling"]["High"],d["coverage_resampling"]["Low"]
    main_tests={r["tariff"]:r for r in d["tests_and_sensitivity"] if r["run"]=="main"}
    model=d["regression"]
    contexts=d["reporting_context"]
    conclusion={"offer":"The central decision rule supports offering the tariff to similar likely sign-ups.",
                "do not offer":"The central decision rule does not support offering the tariff on these assumptions.",
                "inconclusive: bigger pilot":"The central decision rule is inconclusive and supports a bigger pilot."}[d["decision_central"]]

    report=f"""
# Lin's sections for the team report

## 4. Estimates and uncertainty

The main High analysis retained {high['n_tou']:,} ToU and {high['n_std']:,} Std households
across {contexts['events_usable_14']['High']} usable events. The ToU-minus-Std difference
was {high['effect_kwh']:.5f} kWh per half-hour. This corresponds to a demand reduction
of **{high['reduction_kw']:.3f} kW per household** (95% percentile bootstrap CI
**{interval(high['ci_reduction_kw'])} kW**), or {high['reduction_pct']:.1f}% of matched-day
ToU use. At {contexts['scale_households']:,} similar households this scales to
{high['reduction_mw_50k']:.2f} MW (CI {interval(high['ci_reduction_mw_50k'],2)} MW).

For Low events, {low['n_tou']:,} ToU and {low['n_std']:,} Std households across
{contexts['events_usable_14']['Low']} usable events gave a signed change of
{low['effect_kw']:.3f} kW per household (95% CI {interval(low['ci_kw'])} kW), or
{low['pct']:.1f}% of normal use. These intervals use {high['bootstrap_draws']:,}
within-group household resamples, seed {contexts['seed']}. {CI_WORDING}

In {ch['trials']:,} empirical resampling trials per tariff, interval coverage was
{100*ch['coverage']:.1f}% for High and {100*cl['coverage']:.1f}% for Low, with roughly
±{100*ch['nominal_95pct_margin_at_1000_trials']:.1f} percentage points of simulation
error. The checks are conditional on the observed household distributions. Percentage
intervals fix the observed normal-use denominator as specified in advance.

## 8. Conclusion (with Sabrina)

{conclusion} The High reduction interval is {interval(high['ci_reduction_kw'])} kW
against the central break-even threshold of {contexts['thresholds_kw']['central']:.3f} kW.
The corresponding decisions at the low ({contexts['thresholds_kw']['low']:.3f} kW) and high
({contexts['thresholds_kw']['high']:.3f} kW) thresholds are **{d['decision_low_T']}** and
**{d['decision_high_T']}**. Figure `decision.png` shows the estimated reduction and its
interval alongside these economic assumptions.

The result describes opt-in households and average response during the studied High
hours. It does not establish the benefit for every residential customer or the exact
system-peak capacity saving. Shared shocks, household independence and comparability
of counterfactual group changes remain assumptions. The event model concludes:
**{model['conclusion']}**, with only a {100*model['cv_rmse_improvement_fraction']:.1f}%
reduction in held-out-month RMSE. This is a small predictive improvement.
A further pilot should test recruitment beyond volunteers and
measure coincident network-peak savings and actual operating costs before a broad rollout.
"""
    write("REPORT_SECTIONS.md",report)

    table=["| Tariff | Run | ToU / Std | Signed effect (kW) | High reduction or Low change, 95% CI (kW) | Welch p | MW p | Cohen's d | Decision |",
           "|---|---|---:|---:|---|---:|---:|---:|---|"]
    for r in d["tests_and_sensitivity"]:
        ci=([r["reduction_ci_lo_kw"],r["reduction_ci_hi_kw"]] if r["tariff"]=="High"
             else [r["ci_lo_kw"],r["ci_hi_kw"]])
        point=r["reduction_kw"] if r["tariff"]=="High" else r["effect_kw"]
        table.append(f"| {r['tariff']} | {r['run']} | {r['n_tou']} / {r['n_std']} | {r['effect_kw']:.4f} | {point:.4f} [{interval(ci,4)}] | {pvalue(r['welch_p'])} | {pvalue(r['mannwhitney_p'])} | {r['cohens_d']:.3f} | {r['decision']} |")
    results=f"""
# Lin's results and interpretation

## Main finding

{conclusion}

- High-event reduction: **{high['reduction_kw']:.4f} kW/home**, 95% CI **{interval(high['ci_reduction_kw'],4)}**.
- High reduction relative to normal use: **{high['reduction_pct']:.2f}%**, conditional CI **{interval(high['ci_reduction_pct'],2)}%**.
- Reduction for {contexts['scale_households']:,} comparable homes: **{high['reduction_mw_50k']:.3f} MW**.
- Low-event signed change: **{low['effect_kw']:.4f} kW/home**, 95% CI **{interval(low['ci_kw'],4)}**.
- Low signed percent change: **{low['pct']:.2f}%**.

## The main calculation, step by step

1. Mean ToU High household score: **{high['mean_tou']:.8f} kWh per half-hour**.
2. Mean Std High household score: **{high['mean_std']:.8f} kWh per half-hour**.
3. Subtract Std from ToU: **Delta = {high['effect_kwh']:.8f} kWh per half-hour**.
   This compares the groups' changes from their own normal use, not their raw demand.
4. Convert half-hour energy to power by multiplying by two:
   **signed change = {high['effect_kw']:.8f} kW**. Reverse its sign to describe a cut:
   **reduction = {high['reduction_kw']:.8f} kW**.
5. Divide Delta by the mean ToU normal-use value,
   **{high['normal_tou']:.8f} kWh per half-hour**, and multiply by 100:
   signed change **{high['pct']:.4f}%**, or reduction **{high['reduction_pct']:.4f}%**.
6. Scale the reduction to {contexts['scale_households']:,} similar homes and divide
   kW by 1,000: **{high['reduction_mw_50k']:.6f} MW** during these event hours.
7. The bootstrap interval for Delta is **{interval(high['ci_kwh'],8)} kWh per half-hour**.
   Multiplying by minus two and reversing endpoints gives the reduction interval
   **{interval(high['ci_reduction_kw'],8)} kW**.
8. Its upper endpoint, **{high['ci_reduction_kw'][1]:.8f} kW**, is below the fixed central
   threshold, **{contexts['thresholds_kw']['central']:.3f} kW**. The rule therefore returns
   **{d['decision_central']}**, despite evidence that demand does fall.

For Low events the same subtraction uses mean scores {low['mean_tou']:.8f} (ToU)
and {low['mean_std']:.8f} (Std). Delta is **{low['effect_kwh']:.8f} kWh per half-hour**,
or **{low['effect_kw']:.8f} kW**. A positive signed value means higher use. There is
no rollout threshold for the Low question.

## All prespecified sensitivity results

{chr(10).join(table)}

High reduction is positive for a cut. The signed-effect column uses ToU minus Std,
so negative means a cut. Low uses signed change. A widens matching to ±21 days,
B removes off-grid events, C removes high night-use homes and D requires 300 days.
Run C removes different proportions from the groups, as the exclusion tables show.
No run was selected or removed based on its result.

## Assumptions and checks

High score SDs are {main_tests['High']['sd_tou']:.5f} (ToU) and
{main_tests['High']['sd_std']:.5f} (Std) kWh per half-hour. Their ratio is
{main_tests['High']['sd_ratio_tou_over_std']:.3f}, supporting an unequal-variance test.
Low SDs are {main_tests['Low']['sd_tou']:.5f} and {main_tests['Low']['sd_std']:.5f}.
The bootstrap difference distributions have skewness
{d['assumption_checks']['High']['bootstrap_skew']:.3f} (High) and
{d['assumption_checks']['Low']['bootstrap_skew']:.3f} (Low). Inspect the Q-Q and bootstrap
plots in `figures/assumptions_*.png`; these are diagnostics, not proof of independence.

Welch is a mean comparison. Mann-Whitney is a rank-distribution check. Their p-values
need not agree, and a one-sided 5% test need not agree with a two-sided 95% interval.
All tests appear in `results/test_log.csv`, including clearly labelled imported tests.

## Interval coverage

High empirical coverage: {100*ch['coverage']:.1f}%, check pass: {ch['within_prespecified_range']}.
Low empirical coverage: {100*cl['coverage']:.1f}%, check pass: {cl['within_prespecified_range']}.
There are {ch['trials']:,} outer trials per tariff and {ch['inner_bootstrap_draws']:,}
inner draws per trial. The true target in this check is the observed Delta imposed
on the empirical populations. This is not direct knowledge of population truth.

In the inherited simulation, stress-null coverage was
{100*d['p4_simulation']['scenarios']['stress_null']['coverage']:.1f}%. This falls below the
nominal coverage check range. That null scenario's prespecified gate criterion was
false positives, which passed, rather than coverage. Keep this supplementary weakness
visible instead of treating gate passage as proof of perfect calibration.

## Supporting event model

The model used {model['n_events']} High events and {model['n_parameters']} parameters.
Predictors: {', '.join(model['predictors'])}. Held-out-month RMSE was
{model['cv_rmse_model_kw']:.4f} kW for the model and
{model['cv_rmse_baseline_kw']:.4f} kW for the training-mean baseline.
Conclusion: **{model['conclusion']}**, but the RMSE improvement is only
{100*model['cv_rmse_improvement_fraction']:.1f}%. Date-ordered Durbin-Watson was
{model['durbin_watson']:.3f}; HC3 handles unequal variance, not serial dependence.
The value below two suggests possible positive residual correlation, so coefficient
uncertainty needs caution even though the required HC3 fit is retained.
Influential events: {', '.join(model['influential_events']) or 'none'}.
Coefficient and refit tables remain available for review.

## Limits that affect interpretation

Households opted in. Counterfactual group comparability and household independence
remain assumptions. Reused dates and shared shocks can create dependencies outside
the household bootstrap. The lognormal simulation is an approximation, and its power
depends on its model of response variation. Economic thresholds are prespecified
cost/value scenarios. Scaling average High-hour response is not a measured coincident
network-peak reduction. Historical pre-scoring Git evidence and the raw-data rerun are
unavailable from the supplied folder. See `docs/PROVENANCE.md`.

## Correct interval wording

{CI_WORDING}
"""
    write("LIN_RESULTS.md",results)

    speaker=f"""
# Lin's speaker notes and Q&A

Use these with the three Lin slides, inserted as team slides 7, 10 and 11.
The allocated total is about 2.5 minutes. Rehearse aloud and trim to the team's clock.

## Slide 7: Effect and uncertainty (about 90 seconds)

We compare each household with its usual use at the same clock times on nearby normal
days, then subtract the change seen in flat-tariff households. This gives one score per
household, so repeated half-hour readings do not count as independent observations.

For High events, the estimated reduction is {high['reduction_kw']:.3f} kilowatts per
household. The 95% bootstrap interval runs from {high['ci_reduction_kw'][0]:.3f} to
{high['ci_reduction_kw'][1]:.3f} kilowatts. That is {high['reduction_pct']:.1f}% of the
dynamic-tariff households' normal use. For {contexts['scale_households']:,} similar homes,
the estimate scales to {high['reduction_mw_50k']:.2f} megawatts during these event hours.

The bootstrap resamples whole households within each group. {CI_WORDING}
Our separate resampling exercise obtained coverage of {100*ch['coverage']:.1f}% for High
and {100*cl['coverage']:.1f}% for Low under the observed household distributions.

## Slide 10: Recommendation (about 30 seconds)

Our decision compares the whole reduction interval with a break-even threshold fixed
before this analysis. The central threshold is {contexts['thresholds_kw']['central']:.3f}
kilowatts per home. The rule gives: {d['decision_central']}.
Using the lower cost threshold gives {d['decision_low_T']}; the higher threshold gives
{d['decision_high_T']}. The recommendation therefore depends on the economic assumptions
as well as the measured reduction.

## Slide 11: Limits and next evidence (about 30 seconds)

These households volunteered for the tariff. Our conclusion applies most directly to
similar households likely to sign up. It does not prove that every customer would
respond the same way. We measured average response during High-price events, rather
than directly measuring avoided network upgrades. A broader pilot should test who
joins, response at the actual network peak and the real costs of running the tariff.

## Q&A

**Why is a reduction positive if Delta is negative?** Delta is ToU minus Std. Multiply
by two to convert half-hour energy to power, then reverse the sign to describe a cut.

**Why do the interval endpoints reverse?** Multiplying by a negative constant reverses
their order. [-a,-b] must be reordered when a was the smaller endpoint.

**Why bootstrap homes?** Repeated readings within a home depend on one another. The
analysis unit is a household, not a reading. Shared shocks across homes remain a limit.

**Does 95% mean a 95% probability for this interval?** Use the repeated-study statement
above. It describes the method's long-run performance, subject to its assumptions.

**What did the extra coverage check prove?** It checked the method under centered
empirical household populations with a known imposed difference. It cannot establish
the unknown true effect or fix the study's observational design.

**Do small p-values justify rollout?** The decision is based on the effect interval
relative to break-even, not on statistical significance alone.

**Why Low events?** They were in the original blueprint as a separately reported
directional question. They have no economic rollout threshold.

**What exactly did you add?** Lin's estimates, intervals, coverage, decision figure,
writing, speaking material and reproduction check, plus missing shared and supporting
tests/model code. The original ZIPs remain unchanged and local history records edits.
"""
    write("SPEAKER_NOTES.md",speaker)
    start=f"""
# Lin: start here

**Main result:** {high['reduction_kw']:.3f} kW less demand per household during High events
(95% CI {interval(high['ci_reduction_kw'])}). Central decision: **{d['decision_central']}**.

## Files to use

| Need | File |
|---|---|
| Copy your report sections | [REPORT_SECTIONS.md](REPORT_SECTIONS.md) |
| Understand results and every sensitivity run | [LIN_RESULTS.md](LIN_RESULTS.md) |
| Rehearse your contribution | [SPEAKER_NOTES.md](SPEAKER_NOTES.md) |
| Open the three editable slides | [PRESENTATION.md](PRESENTATION.md) |
| Explain the statistics | [STATISTICS_EXPLAINED.md](../docs/STATISTICS_EXPLAINED.md) |
| Explain each program and action | [PROGRAM_GUIDE.md](../docs/PROGRAM_GUIDE.md) |
| Run the project | [README.md](../README.md) |
| Review boundaries and provenance | [PROVENANCE.md](../docs/PROVENANCE.md) |
| Inspect source numbers | [results.json](../results/results.json) |
| Use the decision figure | [decision.png](../figures/decision.png) |
| See reproduction evidence | [REPRODUCIBILITY.md](REPRODUCIBILITY.md) |

## What is complete

Both High and Low estimates, all required unit conversions and percentile intervals,
all three High threshold decisions, the decision figure, empirical coverage checks,
Arpan-compatible bootstrap draws, report sections and speaking notes. Missing shared
helpers, supporting tests/sensitivity analysis and the High-event model are supplied.

## Team actions remaining

Review and merge this local branch with the team's actual repository. Confirm the
documented restoration of the original High-and-Low scope. Have another teammate review
the numbers and code. Supply original household CSVs for the stronger raw-data rerun
and raw hand-check. Combine Lin's slides with the team deck and rehearse together.
No deadline was present in the supplied materials, so none is assumed.
"""
    write("START_HERE.md",start)
    print("Generated Lin's report sections, interpretation, speaker notes and start guide.")


if __name__=="__main__": main()
