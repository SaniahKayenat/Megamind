# Lin's results and interpretation

## Main finding

The central decision rule does not support offering the tariff on these assumptions.

- High-event reduction: **0.0293 kW/home**, 95% CI **0.0256 to 0.0332**.
- High reduction relative to normal use: **6.20%**, conditional CI **5.42 to 7.03%**.
- Reduction for 50,000 comparable homes: **1.463 MW**.
- Low-event signed change: **0.0332 kW/home**, 95% CI **0.0292 to 0.0375**.
- Low signed percent change: **8.75%**.

## All prespecified sensitivity results

| Tariff | Run | ToU / Std | Signed effect (kW) | High reduction or Low change, 95% CI (kW) | Welch p | MW p | Cohen's d | Decision |
|---|---|---:|---:|---|---:|---:|---:|---|
| High | main | 1114 / 4396 | -0.0293 | 0.0293 [0.0256 to 0.0332] | 1.97e-47 | 1.01e-68 | -0.636 | do not offer |
| High | A | 1114 / 4398 | -0.0283 | 0.0283 [0.0246 to 0.0321] | 2.05e-46 | 2.29e-67 | -0.624 | do not offer |
| High | B | 1114 / 4396 | -0.0289 | 0.0289 [0.0252 to 0.0328] | 5.4e-47 | 2.31e-65 | -0.618 | do not offer |
| High | C | 1039 / 3921 | -0.0295 | 0.0295 [0.0255 to 0.0336] | 2.69e-44 | 4.61e-65 | -0.644 | do not offer |
| High | D | 1047 / 4140 | -0.0287 | 0.0287 [0.0250 to 0.0324] | 8.05e-48 | 1.36e-67 | -0.694 | do not offer |
| Low | main | 1114 / 4395 | 0.0332 | 0.0332 [0.0292 to 0.0375] | 1.92e-52 | 4.3e-84 | 0.796 | not applicable |
| Low | A | 1114 / 4396 | 0.0315 | 0.0315 [0.0276 to 0.0355] | 7.7e-52 | 2.03e-84 | 0.780 | not applicable |
| Low | B | 1114 / 4395 | 0.0344 | 0.0344 [0.0302 to 0.0389] | 3.48e-51 | 2e-81 | 0.792 | not applicable |
| Low | C | 1039 / 3920 | 0.0341 | 0.0341 [0.0298 to 0.0385] | 3.34e-50 | 5.71e-82 | 0.823 | not applicable |
| Low | D | 1047 / 4140 | 0.0320 | 0.0320 [0.0281 to 0.0361] | 1.93e-49 | 2.31e-79 | 0.825 | not applicable |

High reduction is positive for a cut. The signed-effect column uses ToU minus Std,
so negative means a cut. Low uses signed change. A widens matching to ±21 days,
B removes off-grid events, C removes high night-use homes and D requires 300 days.
Run C removes different proportions from the groups, as the exclusion tables show.
No run was selected or removed based on its result.

## Assumptions and checks

High score SDs are 0.03089 (ToU) and
0.02054 (Std) kWh per half-hour. Their ratio is
1.504, supporting an unequal-variance test.
Low SDs are 0.03382 and 0.01596.
The bootstrap difference distributions have skewness
-0.084 (High) and
0.083 (Low). Inspect the Q-Q and bootstrap
plots in `figures/assumptions_*.png`; these are diagnostics, not proof of independence.

Welch is a mean comparison. Mann-Whitney is a rank-distribution check. Their p-values
need not agree, and a one-sided 5% test need not agree with a two-sided 95% interval.
All tests appear in `results/test_log.csv`, including clearly labelled imported tests.

## Interval coverage

High empirical coverage: 94.2%, check pass: True.
Low empirical coverage: 94.6%, check pass: True.
There are 1,000 outer trials per tariff and 2,000
inner draws per trial. The true target in this check is the observed Delta imposed
on the empirical populations. This is not direct knowledge of population truth.

## Supporting event model

The model used 63 High events and 5 parameters.
Predictors: evening, hours, winter, low_before. Held-out-month RMSE was
0.0200 kW for the model and
0.0203 kW for the training-mean baseline.
Conclusion: **timing/length predict response better than the mean baseline**, but the RMSE improvement is only
1.4%. Date-ordered Durbin-Watson was
1.271; HC3 handles unequal variance, not serial dependence.
Influential events: H016.
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

If we repeated this study many times, 95% of intervals built this way would contain the true effect.
