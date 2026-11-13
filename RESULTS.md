# Results: what the project found

This is Part 3 of the README: read it after running `python run_all.py`. Every number here comes from `results/results.json`. Effects are ToU minus Std: negative means tariff households used less. Results are stored in kWh per half-hour; × 2 gives kW per household.

## The answer

> During High-price events, households on the dynamic tariff used **0.029 kW less** per household than flat-tariff households (95% CI 0.026 to 0.033 kW; **6.2%** of their normal use). The whole interval is below the break-even threshold **T = 0.043 kW**, so the decision is **do not offer** the tariff to all customers.

*If we repeated this study many times, 95% of intervals built this way would contain the true effect.*

The rest of this file goes stage by stage.

---

## 1. Data (EDA and Stages 1–3: Saniah, Ahmad Jawid)

| | ToU (dynamic tariff) | Std (flat tariff) |
|---|---|---|
| Households in the trial | 1,123 | 4,443 |
| Median daily use in 2012, before the tariff | 8.14 kWh | 8.43 kWh |
| Zero readings in 2013 | 1.18% | 1.27% |
| **Households in the main High-event analysis** | **1,114** | **4,396** |

- **Data cleaned:** 93 million 2013 readings. 105,173 duplicate rows were all identical, and 12 `Null` readings were treated as missing.
- **Events:** 2013 had **69 High events**. Six have fewer than 3 comparison days and cannot be scored, which leaves **63 usable events**. The median usable event has 9 matched normal days, out of 212 normal days in the year.
- **Groups before the tariff:** in 2012 the groups used electricity in the same daily pattern. ToU homes used 3% less in the evening (17:00–23:00) and 19% less at night (00:00–06:00), which is why sensitivity run C removes high night-use homes.
- **Who the results apply to:** households chose their group (opt-in, confirmed by Schofield 2015), so the results apply to households likely to sign up.

Figures:
- `figures/eda/fig2_load_curve_2012.png`: 2012 daily load curve.
- `figures/eda/fig1_high_by_hour.png`: when High events happen. 52% of High half-hours are between 17:00 and 23:00.
- `figures/stage2_matched_days.png`: matched days.

Details: `README_P1.md`, `DATA_CARD.md`.

---

## 2. Can we trust the method? (Stage 4: Nyo)

**Distribution fit.**
- **Which model:** for 200 random households, the **lognormal** fits half-hourly use better than the gamma for 86% of households, by AIC.
- **Fit is not exact:** the bootstrap KS test rejects both models for almost every household. The misfit is at the bottom (a standby "floor"), in the top tail, and in the zeros.
- **Why this is fine:** the tests use household averages, not raw readings.

Figures: `figures/qq_p10.png`, `qq_p50.png`, `qq_p90.png` and `qq_worst.png`, each with lognormal and gamma side by side.

**Simulation.** We ran 1,000 fake studies per scenario where the true answer was known. Each was scored with the real code and tested with the real test.

| Scenario | Result | Required | Pass |
|---|---|---|---|
| No effect: false positives | 5.9% | 3.6–6.4% | ✅ |
| Effect = T: interval coverage | 94.7% | 93.6–96.4% | ✅ |
| Effect = T: power | 100% | reported | — |
| Stress test (zeros + heavy tail), no effect | 6.1% false positives | 3.6–6.4% | ✅ |
| Stress test, effect = T | 94.6% coverage | 93.6–96.4% | ✅ |

**Meaning:** the test makes false alarms at the planned 5% rate, the intervals can be trusted, and an effect as large as T would be found. This holds even when the data is messier than the model.

Details: `README_P4.md`.

---

## 3. How big is the effect? (Stage 5a: Lin)

| High events | Value | 95% interval |
|---|---|---|
| Reduction per household | **0.029 kW** | 0.026 to 0.033 kW |
| As % of normal use | **6.2%** | 5.4% to 7.0% |
| For 50,000 sign-ups | **1.46 MW** less peak demand | 1.28 to 1.66 MW |

**Decision against the three thresholds** (`decisions.md` §8):

| Threshold case | T | Decision |
|---|---|---|
| **Central (used for the decision)** | 0.043 kW | **Do not offer**: the whole interval is below T |
| Low (high value: top network value plus generation capacity) | 0.017 kW | Offer: the whole interval is above T |
| High (low network value plus £5 running costs) | 0.179 kW | Do not offer |

So the decision depends on the economics. On the central case the reduction is real but too small to pay for the tariff. It would pay only in the optimistic case, where avoided generation capacity is counted on top of the highest network value.

**Second check of the intervals:** resampling the real household scores gives **94.2%** coverage, within the planned 93.6–96.4%.

Figure: `figures/decision.png`, the reduction and its interval against the three thresholds.

Details: `reports/LIN_RESULTS.md`, `reports/REPORT_SECTIONS.md`.

---

## 4. Is the effect real? (Stage 5b: Arpan)

**H1:** during High events, ToU households use less than Std households.

| Test | Result |
|---|---|
| One-sided Welch t-test (main) | t = −14.99, p = 2.0 × 10⁻⁴⁷ |
| One-sided Mann–Whitney (check) | p = 1.0 × 10⁻⁶⁸. A ToU home scores lower than a Std home in 67% of pairs |
| Effect size | Cohen's d = −0.64 (medium) |
| Assumptions | SDs 0.031 vs 0.021 (ratio 1.50), which is why Welch is used. The bootstrap distribution is bell-shaped (skew −0.08) |

**H1 is supported.** All three methods agree.

**Sensitivity runs:** every run gives the same answer.

| Run | Change | Reduction (kW) | 95% interval | Decision |
|---|---|---|---|---|
| Main | ±14 matched days | 0.029 | 0.026–0.033 | do not offer |
| A | ±21 matched days | 0.028 | 0.025–0.032 | do not offer |
| B | without off-grid event days | 0.029 | 0.025–0.033 | do not offer |
| C | without high night-use homes | 0.030 | 0.026–0.034 | do not offer |
| D | only households with ≥300 days | 0.029 | 0.025–0.032 | do not offer |

Figures:
- `figures/qq_household_scores_high.png`: household scores.
- `figures/bootstrap_hist_high.png`: bootstrap distribution.

Details: `README_P5.md`, `docs/stage5_arpan/`.

---

## 5. When do signals work best? (Stage 6: Ahmad Jawid)

Each of the 63 usable High events was regressed on its features. "Extra cut" is in kW per household, other features held fixed.

| Feature | Extra cut | 95% interval | p |
|---|---|---|---|
| **Winter (Oct–Mar)** | **0.015** | 0.005 to 0.025 | **0.003** |
| Evening start (17:00 or 20:00) | 0.008 | −0.001 to 0.018 | 0.07 |
| Low period just before | −0.007 | −0.018 to 0.005 | 0.27 |
| Each extra hour of length | 0.000 | −0.001 to 0.001 | 0.85 |

- **Main finding:** only winter has a clear link. Winter events get a bigger cut.
- **Explained variation:** the four features explain 15% of the variation between events (R² = 0.15).
- **Cross-validation:** the model is only slightly better than predicting the average (leave-one-month-out RMSE 0.0200 vs 0.0203 kW; better in 6 of 12 months). Treat it as a rough guide, not a forecast.
- **Diagnostics:**
  - One influential event (H016, 3 Feb). Removing it changes no conclusion.
  - Durbin–Watson is 1.27: events close in time share some error, so the intervals may be a little too narrow. An exploratory check (Newey–West) keeps winter clear (p = 0.008).

Figures: `figures/reg_resid_vs_fitted.png`, `reg_qq_residuals.png`, `reg_cooks_distance.png`.

Details: `README_P6.md`.

---

## 6. Low events (H2, for information)

During Low-price (cheap) events, ToU households used **0.033 kW more** per household (95% CI 0.029 to 0.037 kW; 8.7% of normal use). Welch p = 1.9 × 10⁻⁵², and the result holds in every sensitivity run. Households shift use into cheap hours as well as away from expensive ones.

`decisions.md` §8 gives H2 no threshold, so it does not change the decision. The team still has to confirm whether the report includes H2 (see the README, "Open items").

Details: `results/sensitivity_table_high_low.csv`, `figures/assumptions_low.png`.

---

## 7. Limits of these results

1. **Opt-in households.** The groups chose themselves, so the results apply to households likely to sign up, not to everyone.
2. **Shared events.** All households share the same events and comparison days, so the intervals may be somewhat too narrow (see also Durbin–Watson in Section 5).
3. **The simulation is optimistic about power.** Simulated households do not vary their response from event to event, so real power is probably lower than 100%.
4. **Average over the event, not the network peak.** The reduction is averaged over each event's hours. It is not measured at the exact time of the network's peak.
5. **The thresholds are assumptions.** They rest on published cost figures, not costs measured in the trial. That is why all three cases are reported.
6. **The order of rules and results cannot be proved from Git.** See `docs/decisions.md`, "Changes", 13 Nov.
