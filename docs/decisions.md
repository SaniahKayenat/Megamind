# Analysis decisions (Stage 0)

**Status:** fixed before any outcome is computed. Commit this file before running any scoring code (Stage 3), so the commit history shows it came first. Any later change is added at the bottom under "Changes", with the date and the reason, and never edits the text above.

Decided: 9 November 2026. Code that implements these rules: `src/config.py`.

---

## 1. Question and decision

- **Question:** when a household on the dynamic tariff is sent a High-price signal, how much less electricity does it use during those hours than a similar household on the flat tariff?
- **Decision-maker:** a utility product manager deciding whether to offer a dynamic tariff to all residential customers.
- **Who the answer applies to:** households likely to sign up for such a tariff (see §2).

## 2. How households were assigned

Tariff households **chose to join**; they were not randomly assigned. A study of the same trial data describes the 2013 sample as "4,756 smart metered households … of which 988 opted to receive the experimental dToU tariff" (Bhattacharya et al., arXiv:1605.08078). We could not read the sampling section of Schofield (2015, Ch. 4) online; whoever has the full thesis should check §4.4 and add a line under "Changes" if it says otherwise.

**Consequence:**
- The comparison is between self-selected groups, so results are framed as "for households likely to sign up".
- The 2012 comparison (similar daily use, same daily pattern) is reported as evidence the groups are comparable, not as proof.

## 3. Data rules

| Topic | Rule |
| --- | --- |
| Years | 2013 for all analysis. 2012 only to describe the groups before the tariff and to define high night-use homes. |
| Duplicate (household, time) rows | Keep the first valid reading. Report how many duplicates exist and how many have identical values. |
| `Null` kWh | Missing. Never treated as zero. |
| Outliers | None removed. Zeros and very large readings are real readings. |
| Clock | Readings and tariff file both use a fixed clock (GMT). No daylight-saving shift. Times in results are GMT. |
| Households with no 2013 data | Dropped (6 ToU, 32 Std). Reported. |

## 4. Events

| Topic | Rule |
| --- | --- |
| Event | A run of consecutive half-hours with the same non-Normal price (High or Low). 2013 has 69 High and 92 Low events. |
| Day type | Weekday, or weekend/bank holiday, taken from the event's **start** date. |
| Bank holidays 2013 (England) | 1 Jan, 29 Mar, 1 Apr, 6 May, 27 May, 26 Aug, 25 Dec, 26 Dec. Treated as weekend days. |
| Off-grid event | Starts or ends off the 3-hour grid (23:00, 02:00, 05:00 … 20:00). These fall on 29 Jan, 9 Feb and 21 Mar. |
| Low before | 1 if the half-hour immediately before the event is Low-priced. |
| Evening | 1 if the event starts at 17:00 or 20:00. |
| Winter | 1 if the event starts in October–March. |

## 5. Matched normal days

| Topic | Rule |
| --- | --- |
| Normal day | A calendar day whose 48 half-hours are all Normal-priced (212 days in 2013). |
| Matched day | The event's half-hours shifted by a whole number of days *k*, where every date the shifted window touches is a normal day and the shifted start date has the same day type. |
| Window (main) | \|*k*\| ≤ 14 days. |
| Too few matched days | An event with fewer than 3 matched days cannot be scored and is dropped. With the real schedule this drops **6 High events** (7 Jan, 29 Sep, 8 Dec, 15 Dec, 21 Dec, 28 Dec) and 15 Low events. The report states how many events enter the analysis. |

## 6. Scores

- **Event score** for a household = mean kWh per half-hour during the event − mean kWh per half-hour at the same half-hours on its matched days.
- **Same half-hours on both sides:** a half-hour missing on the event day is also dropped from the matched days.
- **A matched day counts** if it has readings for at least 80% of the half-hours present on the event day.
- **A score is valid** if at least 80% of the event's half-hours have readings and at least 3 matched days count.
- **Household score** = mean of the household's valid event scores, calculated separately for High and Low events. A household needs **at least 5 valid events** of that type, otherwise it is excluded from that hypothesis and counted in the exclusion table.
- **Units:**
    - Scores are in kWh per half-hour; × 2 = kW.
    - "% of normal use" = effect ÷ mean matched-day use of ToU households × 100.

## 7. Hypotheses and tests

| | Statement | Test |
| --- | --- | --- |
| **H1** | During High events, mean ToU household score < mean Std household score | One-sided Welch t-test, α = 0.05 |
| **H2** | During Low events, mean ToU household score > mean Std household score | One-sided Welch t-test, α = 0.05 |

- **Check:** one-sided Mann–Whitney test for each.
- **Effect sizes reported with every p-value:** difference in kWh per half-hour, in kW per household, as % of normal use, and Cohen's *d* (pooled SD).
- **No multiple-testing correction.** H1 and H2 answer separate questions, and both results are reported whatever they show.
- **Intervals:** 95% percentile bootstrap, resampling households within each group separately, 10,000 resamples.
- **Interval wording, used everywhere:** "If we repeated this study many times, 95% of intervals built this way would contain the true effect." Never "a 95% probability that the effect is in this interval."
- **Test log:** every test anyone runs is appended to `results/test_log.csv`, and nothing is deleted.

## 8. Decision threshold and rule

The threshold *T* is the **break-even reduction per household**:

*T* = yearly cost of the tariff per household ÷ yearly value of 1 kW less peak demand

| Input | Value | Source |
| --- | --- | --- |
| In-home display | £15 per unit | DECC (2014) smart-meter impact assessment, Table 3-1 |
| Display lifetime | 7 years → £2.14 per household per year | BEIS (2016) smart-meter cost-benefit update, §2.12.1 |
| Tariff revenue | Assumed revenue-neutral: cheap Low hours and expensive High hours cancel out over a year | Assumption |
| Value of avoided network reinforcement | £40–60 per kW per year (central £50) | Sustainability First (2012), Paper 4, p. 31 |
| Value of avoided generation capacity (upper case only) | £63 per kW per year | GB Capacity Market T-4 clearing price, delivery year 2026/27 (EnAppSys) |
| Running costs (signals, billing, support) | £5 per household per year (high case only) | Assumption; no published figure found |

| Case | Cost / value | *T* (kW per household) | *T* (kWh per half-hour) |
| --- | --- | --- | --- |
| **Central (used for the decision)** | £2.14 ÷ £50 | **0.043** | **0.021** |
| Low threshold | £2.14 ÷ (£60 + £63) | 0.017 | 0.009 |
| High threshold | (£2.14 + £5) ÷ £40 | 0.179 | 0.089 |

**Decision rule**, applied to the High-event reduction per household in kW (reduction = −2 × effect):

- **Offer the tariff** if the lower end of the 95% interval is at least 0.043 kW.
- **Don't offer it** if the upper end is below 0.043 kW.
- **Inconclusive** if the interval contains 0.043 kW: recommend a larger pilot instead of a rollout.

The low and high cases are reported as a sensitivity check on the decision. H2 (Low events) has no threshold; it is reported for information.

## 9. Sensitivity runs

| Run | Change from the main analysis | Reason |
| --- | --- | --- |
| A | Matched days within ±21 instead of ±14 | Tests the window choice. **Changed from the proposal's ±7:** with the real schedule, ±7 leaves 16 of 69 High events with fewer than 3 matched days, so any difference would mostly reflect lost events. ±21 keeps all but 2. |
| B | Without the off-grid event days (29 Jan, 9 Feb, 21 Mar) | Non-standard event timing |
| C | Without high night-use homes: top 10% of 2012 night share (00:00–06:00 ÷ total), among households with ≥60 days of 2012 data | The Std group had more timer-driven night loads |
| D | Only households with ≥300 days of 2013 data | Checks that drop-out doesn't drive the result |

Every run is reported in one table, whatever it shows.

## 10. Distribution model (criterion 3) and simulation

- **Sample:** 200 households with ≥300 days of 2013 data, drawn with seed 2013.
- **Readings used:** non-zero readings on all-Normal days only, so the tariff can't influence the fit. 500 per household, drawn at random with seed 2013, to reduce dependence between consecutive half-hours.
- **Models:** lognormal and gamma, fitted by maximum likelihood with location fixed at 0.
- **Comparison:** AIC.
- **Goodness of fit:** parametric-bootstrap Kolmogorov–Smirnov test, 199 simulations per household and model, refitting each time, at 5%.
- **Q-Q plots** for 4 households: the 10th, 50th and 90th percentile of daily use, and the worst lognormal fit.
- **Purpose:** the fitted model drives the simulation study. The hypothesis tests do not assume it.
- **Simulation:** 1,000 simulated trials per scenario, using the same scoring code as the real analysis and the real group sizes.

| Scenario | True effect | Pass criterion |
| --- | --- | --- |
| False-positive rate | 0 | Rejection rate between 3.6% and 6.4% |
| Coverage | *T* | Between 93.6% and 96.4% of intervals contain *T* |
| Power | *T* | Reported as is |
| Stress test | 0 and *T* | 1.2% zeros added and top 5% of households scaled ×3; same criteria |

The pass ranges are 5% ± 1.4 and 95% ± 1.4 percentage points: the simulation's own margin of error for 1,000 trials.

## 11. Regression (criterion 6)

- **Data:** one row per High event that has valid scores. The outcome is the event's mean ToU score − mean Std score, using households in the main analysis.
- **Model:** `effect ~ evening + hours + winter + low_before`, fitted by ordinary least squares with HC3 standard errors. That is **5 parameters**, about 13 events each after the 6 dropped events. **No month predictor:** it would add 11 parameters and break leave-one-month-out cross-validation.
- **Overlapping predictors:** if any variance inflation factor exceeds 5, drop `hours` (the one most likely to overlap with `evening`) and report it.
- **Baseline:** predict the mean effect for every event.
- **Validation:** leave-one-month-out cross-validation; root-mean-square error of model vs baseline.
- **Diagnostics:** residuals vs fitted values, Q-Q of residuals, Cook's distance (flag > 4 ÷ number of events and refit without them), Durbin–Watson in date order.
- **Interpretation:** coefficients × 2 = kW per household. If the model does not beat the baseline, report that event timing and length do not predict the response.
- **Low events:** modelled only if time allows; otherwise the report says it was not done.

## 12. Seeds

All random steps use **2013**, each with its own `np.random.default_rng(2013)`:
- the 200-household sample;
- the 500-reading draw;
- the bootstrap intervals;
- the goodness-of-fit simulations;
- the simulation study.

Leave-one-month-out cross-validation has no random step.

---

## Sources

- Bhattacharya et al., *A baseline-free method to identify responsive customers*, arXiv:1605.08078 — <https://ar5iv.labs.arxiv.org/html/1605.08078>
- Schofield (2015), PhD thesis, Imperial College London — <https://spiral.imperial.ac.uk/handle/10044/1/25575>
- DECC (2014), *Smart meter roll-out for the domestic and small and medium non-domestic sectors: impact assessment* — <https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/276656/smart_meter_roll_out_for_the_domestic_and_small_and_medium_and_non_domestic_sectors.pdf>
- BEIS (2016), *Smart meter roll-out cost-benefit analysis, Part I* — <https://assets.publishing.service.gov.uk/media/5a7f59f9ed915d74e6229eef/OFFSEN_2016_smart_meters_cost-benefit-update_Part_I_FINAL_VERSION.PDF>
- Sustainability First (2012), *GB Electricity Demand, Paper 4* — <https://sustainabilityfirst.org.uk/wp-content/uploads/2012/06/Sustainability-First-GB-Electricity-Demand-Paper-4-What-demand-side-services-can-provide-value-to-the-electricity-sector-June-2012.pdf>
- EnAppSys, *T-4 Capacity Market auction for 2026-27 cleared at £63/kW/year* — <https://www.enappsys.com/t-4-capacity-market-auction-for-the-delivery-year-2026-27-has-cleared-at-an-all-time-high-price-of-63-kw-year/>

## Changes

(none recorded in the supplied file)

### 11 November 2026 — documented continuation before new effects

1. Restore both High and Low scoring, as required by the original blueprint and this
   document. Saniah's 10 November handoff/config narrowed the scope to High without
   an entry here. The continuation restores the prespecified scope; it does not choose
   a scope based on significance. Nyo's simulation remains High-only, matching H1.
2. Preserve the original division: Lin owns estimates, intervals, coverage and decision;
   Arpan owns tests and sensitivity. Lin's continuation also supplies those missing
   supporting scripts on behalf of the team, with authorship recorded honestly.
3. Record Nyo's inherited implementation details: replacement of an all-zero sampled
   home (MAC003627 by MAC004517), bootstrap KS loop correction, real missingness
   masks, compact simulation storage, stress scaling before effect application.
   These originated in README_P4.md; they were not newly chosen after real effects.
4. Use 10,000 bootstrap draws for reported intervals; 2,000 draws in each of 1,000
   coverage trials, as the detailed guideline specifies. All random roots are 2013.
   Trial-specific SeedSequence children permit reproducible parallel execution.
5. Keep signed effects (`effect_*_kw = 2*Delta`) distinct from positive High reductions
   (`reduction_high_kw = -2*Delta`). Threshold decisions use reductions only. The
   fixed percentage denominator is mean ToU normal use, following the guideline;
   its rescaled interval is conditional on that denominator, not a ratio bootstrap.
6. Missing log helpers and input validation are integration repairs. Reported results
   retain full floating-point precision; rounding happens only in human-readable text.
7. The supplied Git history is absent. The new local pre-analysis checkpoint proves
   order only for this continuation. It cannot certify historical preregistration.
