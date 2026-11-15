# Analysis Decisions — High-Price Events (Stage 0)

**Project:** Do Price Signals Cut Household Demand?  
**Team:** Megamind  
**Final analysis scope:** High-price events only (H1)  
**Implementation:** `src/config.py` and the integrated analysis scripts.

This document records the study design, data-processing rules, statistical methods, and decision criteria used for the High-price event analysis.

## 1. Research Question and Decision

**Research question:** When a household on a dynamic time-of-use (ToU) tariff receives a High-price signal, how much less electricity does it consume during those hours compared with a household on the standard (Std) tariff?

**Decision-maker:** A utility product manager deciding whether to offer the dynamic tariff to residential customers.

**Target population:** Households likely to voluntarily sign up for a dynamic tariff.

The primary objective is to estimate the reduction in electricity demand during High-price events and determine whether that reduction meets the economic break-even threshold.

## 2. Household Assignment

Households joined the dynamic tariff voluntarily rather than through random assignment.

The comparison is therefore between self-selected ToU and Std households. The 2012 consumption patterns are used to describe group comparability before the tariff, but do not establish that the groups are identical.

The analysis is interpreted primarily for households likely to sign up for a similar tariff.

Schofield (2015), Chapter 4, confirms that recruitment to the dynamic tariff was opt-in.

## 3. Data Preparation Rules

| Topic                            | Decision                                                              |
| -------------------------------- | --------------------------------------------------------------------- |
| Main analysis year               | 2013                                                                  |
| Baseline year                    | 2012, for group comparisons and identifying high night-use households |
| Duplicate household-time records | Keep the first valid reading; report duplicate counts                 |
| Missing consumption (`Null`)     | Treat as missing, never as zero                                       |
| Outliers                         | Do not remove zero or unusually large valid readings                  |
| Time zone                        | Fixed GMT; no daylight-saving adjustment                              |
| Households without 2013 data     | Exclude and report (6 ToU, 32 Std)                                    |

All consumption values are measured in kWh per half-hour.

## 4. High-Price Event Definition

A **High-price event** is a continuous sequence of half-hour intervals labelled High in the tariff schedule.

There are **69 scheduled High-price events in 2013**.

| Variable       | Definition                                                    |
| -------------- | ------------------------------------------------------------- |
| Day type       | Weekday or weekend/bank holiday, based on event start date    |
| Bank holidays  | 1 Jan, 29 Mar, 1 Apr, 6 May, 27 May, 26 Aug, 25 Dec, 26 Dec   |
| Off-grid event | Event starting or ending outside the standard three-hour grid |
| Evening        | 1 if the event starts at 17:00 or 20:00                       |
| Winter         | 1 if the event starts in October–March                        |
| `low_before`   | 1 if the immediately preceding half-hour was Low-priced       |

The off-grid events occur on 29 January, 9 February, and 21 March.

The `low_before` variable is retained only as a predictor in the High-event regression model.

## 5. Matched Normal Days

To estimate how much electricity a household would normally consume during the same hours, each High event is compared with nearby Normal-price days.

**Normal day:** A calendar day containing 48 Normal-price half-hours. There are 212 such days in 2013.

**Matching rules:**

1. Use the same clock-time intervals as the High event.
2. Select Normal-price comparison days within ±14 calendar days.
3. Require the same day type as the event's start date.
4. For events crossing midnight, every date touched by the shifted comparison window must be Normal-priced.
5. Require at least three matched days.

Six High events do not have enough matched days and are excluded:

7 January, 29 September, 8 December, 15 December, 21 December, and 28 December.

Therefore, **63 High events** enter the main analysis.

## 6. Event and Household Scores

### Event score

For each household and High event:

**Event score = Mean electricity consumption during the High event − Mean consumption during matched Normal-price intervals**

A negative score means the household consumed less electricity during the High event than during comparable Normal-price periods.

**Validity rules:**

- At least 80% of the event's half-hours must have valid readings.
- A matched day must cover at least 80% of the available event intervals.
- At least three matched days must be valid.
- Missing event intervals are also excluded from the corresponding matched-day comparison.

### Household score

The household score is the average of its valid High-event scores.

Each household must have **at least five valid High events** to be included in the main analysis.

### Group effect

\[
\Delta=\overline{S}_{ToU}-\overline{S}_{Std}
\]

where \(S\) represents household scores in kWh per half-hour.

The estimated High-event demand reduction is:

\[
R=-2\Delta
\]

where \(R\) is measured in kW per household.

The factor of 2 converts kWh per half-hour into average kW.

Percentage reduction is calculated relative to mean matched-day consumption for ToU households.

## 7. Hypothesis Testing and Confidence Intervals

### Primary hypothesis (H1)

\[
H*0:\mu*{ToU}\geq\mu\_{Std}
\]

\[
H*1:\mu*{ToU}<\mu\_{Std}
\]

The alternative hypothesis states that ToU households have lower mean scores during High events than Std households.

**Primary test:** One-sided Welch's t-test with significance level \(\alpha=0.05\).

**Supporting test:** One-sided Mann–Whitney test.

**Effect-size reporting:**

- Difference in kWh per half-hour
- Reduction in kW per household
- Percentage of normal consumption
- Cohen's \(d\), using the pooled standard deviation

### Confidence intervals

Use a 95% percentile bootstrap confidence interval with:

- 10,000 bootstrap resamples.
- Households resampled separately within the ToU and Std groups.
- Random seed 2013.

Confidence intervals are interpreted using their repeated-sampling coverage, not as probabilities that a fixed parameter lies within a particular observed interval.

All statistical tests are recorded in `results/test_log.csv`.

## 8. Economic Decision Threshold

The break-even threshold is defined as:

\[
T=\frac{\text{Annual tariff cost per household}}{\text{Annual value of 1 kW avoided peak demand}}
\]

### Economic assumptions

| Input                                                  | Value                     |
| ------------------------------------------------------ | ------------------------- |
| In-home display                                        | £15 per household         |
| Display lifetime                                       | 7 years                   |
| Annual display cost                                    | £2.14                     |
| Tariff revenue                                         | Assumed revenue-neutral   |
| Avoided network reinforcement                          | £40–60 per kW per year    |
| Central network value                                  | £50 per kW per year       |
| Additional generation capacity value (optimistic case) | £63 per kW per year       |
| Additional running cost (conservative case)            | £5 per household per year |

### Break-even thresholds

| Scenario                        | Threshold (kW/household) |
| ------------------------------- | -----------------------: |
| Central                         |                **0.043** |
| Optimistic / lower threshold    |                    0.017 |
| Conservative / higher threshold |                    0.179 |

### Decision rule

The central decision is based on the 95% confidence interval for the positive High-event reduction \(R\).

- **Offer:** Lower confidence bound is at least 0.043 kW.
- **Do not offer:** Upper confidence bound is below 0.043 kW.
- **Inconclusive:** Confidence interval contains 0.043 kW; recommend a larger pilot.

The optimistic and conservative thresholds are used for economic sensitivity analysis.

## 9. Sensitivity Analyses

Four sensitivity analyses are performed using the High-event outcome.

| Run | Change                                                                                          | Purpose                                       |
| --- | ----------------------------------------------------------------------------------------------- | --------------------------------------------- |
| A   | Use ±21-day matching instead of ±14 days                                                        | Assess matching-window choice                 |
| B   | Exclude off-grid event dates (29 Jan, 9 Feb, 21 Mar)                                            | Assess unusual event timing                   |
| C   | Exclude the top 10% of 2012 night-use share among households with at least 60 days of 2012 data | Assess influence of high night-use households |
| D   | Include only households with at least 300 days of 2013 readings                                 | Assess influence of data completeness         |

The ±21-day alternative replaces the original proposal's ±7-day sensitivity because the shorter window would leave 16 of 69 High events without enough comparison days.

All sensitivity results are reported regardless of their direction or statistical significance.

## 10. Distribution Fitting and Simulation

### Distribution fitting

- Sample 200 households with at least 300 days of 2013 data.
- Use random seed 2013.
- Select 500 positive readings per household from all-Normal days.
- Fit lognormal and gamma distributions using maximum likelihood estimation.
- Fix the location parameter at zero.
- Compare models using AIC.
- Evaluate goodness of fit using a parametric-bootstrap Kolmogorov–Smirnov test with 199 simulations per household and model.
- Produce Q-Q plots for four representative households.

The fitted distributions are used to generate synthetic consumption data for the simulation study. The main hypothesis test does not require consumption to follow either distribution.

### Simulation

Use 1,000 simulated trials per scenario, with the real household group sizes and the same scoring procedure as the main analysis.

| Scenario              | True reduction | Evaluation                              |
| --------------------- | -------------- | --------------------------------------- |
| Null / false-positive | 0 kW           | Rejection rate                          |
| Threshold coverage    | 0.043 kW       | Confidence-interval coverage            |
| Threshold power       | 0.043 kW       | Rejection rate                          |
| Stress scenarios      | 0 and 0.043 kW | False-positive rate, coverage and power |

The stress scenarios add 1.2% zero readings and scale the highest-use 5% of households by a factor of 3.

**Evaluation criteria:**

- False-positive rate: 3.6%–6.4%.
- Confidence-interval coverage: 93.6%–96.4%.
- Power: reported as observed.

Reported confidence intervals use 10,000 bootstrap resamples; simulation coverage trials use 2,000 bootstrap resamples each.

## 11. High-Event Regression

The regression investigates whether High-event response varies with event characteristics.

**Unit of analysis:** One row per eligible High event.

**Outcome:** Mean ToU event score minus mean Std event score.

**Model:**

```text
effect ~ evening + hours + winter + low_before
```

Fit ordinary least squares with HC3 robust standard errors.

The model contains five parameters, including the intercept.

### Predictor rules

- `evening`: Event starts at 17:00 or 20:00.
- `hours`: Duration of the event.
- `winter`: Event starts during October–March.
- `low_before`: Immediately preceding half-hour has a Low price.

If any variance inflation factor exceeds 5, drop `hours` and report the change.

### Model evaluation

- Baseline model predicts the overall mean event effect.
- Leave-one-month-out cross-validation compares regression and baseline RMSE.
- Diagnostics include residual-versus-fitted plots, residual Q-Q plots, Cook's distance and Durbin–Watson.
- Observations with Cook's distance greater than \(4/n\) are flagged for an additional fit without them.
- Regression coefficients are multiplied by 2 to express signed demand differences in kW.

An exploratory Newey–West standard-error check was added after the Durbin–Watson statistic indicated possible temporal correlation. The primary HC3 results are retained.

## 12. Random Seeds and Reproducibility

All random procedures use seed **2013**, including:

- Household sampling
- Reading sampling
- Bootstrap confidence intervals
- Distribution goodness-of-fit simulations
- Simulation trials

Independent random streams may be created using trial-specific `SeedSequence` children for parallel simulation.

Leave-one-month-out cross-validation is deterministic.

The integrated repository includes the analysis scripts, saved results, test logs and supporting documentation.

## 13. Implementation and Integration Notes

The following details are retained from the team's stage documentation:

- Nyo's distribution-fitting implementation replaced an all-zero sampled household (`MAC003627`) with `MAC004517`, corrected the bootstrap KS loop, used observed missingness masks, compact simulation storage and stress scaling before effect application.
- Lin's estimation uses 10,000 bootstrap draws and preserves full floating-point precision in stored outputs.
- Arpan's `src/09_tests.py` supplies the primary High-event hypothesis tests and sensitivity analyses.
- Ahmad Jawid's `src/10_model.py` supplies the High-event regression.
- Shared result-saving and test-logging functions are implemented in `src/pipeline_lib.py`.
- The raw matrix writer received duplicate-handling and row-count repairs during integration.
- The team confirmed the final report and presentation would focus on High-price events.

These implementation notes describe work completed during the project; they are not presented as decisions independently verified to have been made before analysis.
