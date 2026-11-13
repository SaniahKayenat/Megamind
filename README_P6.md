# Stage 6: Regression (Ahmad Jawid)

**Status: done (11 Nov 2026).** The pre-stated model from `decisions.md` §11 was fitted exactly as written, with every planned diagnostic. All 5 tests on made-up data pass, and every number was rechecked by hand with plain numpy.

**Scope:** High events only, as in Stage 3. There is no Low-event model, because the project dropped Low events on 10 Nov (see "Changes to log" below).

---

## 1. What this step does, in one paragraph

Stage 5 gives one average effect over all High events. A utility manager also chooses *when* to send signals and *how long* to make them. This step asks which kinds of event go with a bigger cut. Each of the 63 usable High events is one row. Its outcome is the event's **effect**: the mean ToU household score minus the mean Std household score, in kWh per half-hour (negative = ToU households cut more). That effect is regressed on four event features fixed in advance: an evening start, the event's length, winter, and a Low-price period just before.

## 2. How it fits with the other stages

- **Input:** `results/event_effects_main.csv` from Saniah's Stage 3. This folder has a copy; in the repository the script reads Saniah's file directly. Its event features come from Stage 2.
- **Plan:** `decisions.md` §11, written on 9 Nov before any outcome was seen. The plan was checked against the event features on 10 Nov (VIFs below 2, all 12 cross-validation folds estimable), without looking at any effect.
- **Results gate:** Nyo's simulation passes all four scenarios, and `decisions.md` and T were fixed on 9 Nov. The team is sharing files on Google Drive for now, uploaded in this order: `decisions.md` (with T), then the Stage 4 results, then these Stage 6 files. Drive's upload dates then show the rules came first. Don't re-save `decisions.md`, so it keeps its 9 Nov date; add any change under its "Changes" section. When the project moves to git, commit in the same order.

## 3. Results

### Coefficients (OLS, HC3 standard errors, 63 events)

"Extra cut" = −2 × coefficient, in kW per household. A positive extra cut means ToU households cut **more** during that kind of event, with the other features held fixed.

| Feature | Extra cut per household (kW) | 95% interval (kW) | p |
|---|---|---|---|
| Winter (starts October–March) | **0.015** | 0.005 to 0.025 | 0.003 |
| Evening (starts 17:00 or 20:00) | 0.008 | −0.001 to 0.018 | 0.070 |
| Low-price period just before | −0.007 | −0.018 to 0.005 | 0.267 |
| Each extra hour of length | 0.000 | −0.001 to 0.001 | 0.850 |

- R² = 0.151 (adjusted 0.092): the four features explain about 15% of the variation between events.
- Coefficients in kWh per half-hour, with standard errors, are in `results/regression_coefficients.csv`.

### Overlap between predictors

All variance inflation factors are below 2 (evening 1.61, hours 1.03, winter 1.24, low_before 1.87). None is above 5, so `hours` stays in. That leaves 5 parameters, about 13 events each.

### Leave-one-month-out cross-validation

| | RMSE (kW per household) |
|---|---|
| Model | 0.0200 |
| Baseline (mean effect of the training months) | 0.0203 |

The model's error is **1.4% lower** than the baseline's, and it does better in 6 of the 12 held-out months. By the pre-stated rule it beats the baseline, so the "timing and length don't predict the response" conclusion does not apply. But the margin is small: treat the model as a rough guide, not a forecast. No fold had to drop a predictor. Per-month results are in `results/regression_cv.csv`.

### Diagnostics

| Check | Result | What it means |
|---|---|---|
| Residuals vs fitted (`figures/reg_resid_vs_fitted.png`) | No curve or funnel | The straight-line model is reasonable |
| Q-Q of residuals (`figures/reg_qq_residuals.png`) | Close to the line, except one low point (H016) | Residuals are roughly normal |
| Cook's distance > 4/63 = 0.063 (`figures/reg_cooks_distance.png`) | One event: **H016** (Sun 3 Feb, 11:00–14:00), Cook's distance 0.145 | See refit below |
| Refit without H016 (62 events) | Winter 0.013 kW (p = 0.006); evening 0.009 kW (p = 0.054) | No conclusion changes. Only `hours` changes sign, and it is about zero either way |
| Highest leverage | H073, the 24-hour event (7 Jun), leverage 0.52 | Its Cook's distance (0.062) is just under the cut-off, so it does not drive the result |
| Durbin–Watson, in date order | **1.27** | Well below 2: events close in time share part of their error (shared weather and season), so the HC3 intervals are probably somewhat too narrow |

### Exploratory check (not in the plan, logged as exploratory)

The plan didn't say what to do if Durbin–Watson was far from 2. So the model was refitted with Newey–West standard errors (3 lags, date order), which allow neighbouring events to share errors.

- Winter stays clear: 0.015 kW, 95% interval 0.004 to 0.026, p = 0.008.
- Evening's p falls to 0.03. Newey–West has no small-sample correction, unlike HC3, so the pre-stated HC3 result (p = 0.07) **stays the main one**. Evening should not be called significant.

All 12 coefficient tests (main fit, Cook's refit and Newey–West check) are in `results/test_log.csv`.

## 4. Checks

- **Tests on made-up data** (`tests/test_10_model.py`), all passing:
  1. planted coefficients are recovered;
  2. HC3 standard errors match the textbook formula;
  3. the model beats the baseline when a real signal is planted;
  4. a predictor that is constant in one training fold is dropped for that fold only;
  5. `hours` is dropped when its VIF is above 5, and a planted extreme event is flagged by Cook's distance.
- **Independent recheck on the real data:** coefficients, HC3 standard errors, Cook's distances, Durbin–Watson, R² and both cross-validation RMSEs were recomputed with plain numpy and agree exactly.
- **Two set-ups, same output:** the script was run inside the repository layout (with Saniah's `config.py` and `pipeline_lib.py`) and on its own in this folder. The output files are identical, and the test log differs only in timestamps.

## 5. Text for the report (section 6, about half a page)

> **6. Which events get bigger cuts?**
>
> To see whether event features go with a bigger response, we regressed each usable High event's effect (mean ToU score − mean Std score; 63 events) on four features fixed before the results were seen: an evening start (17:00 or 20:00), length in hours, winter (October–March) and a Low-price period just before. The model has 5 parameters, about 13 events each. It is fitted by OLS with HC3 standard errors, which allow some events to be noisier than others, and has no month term, so that leave-one-month-out cross-validation is possible. All variance inflation factors were below 2.
>
> | Feature | Extra cut per household (kW) | 95% interval | p |
> |---|---|---|---|
> | Winter event | 0.015 | 0.005 to 0.025 | 0.003 |
> | Evening start | 0.008 | −0.001 to 0.018 | 0.07 |
> | Low period just before | −0.007 | −0.018 to 0.005 | 0.27 |
> | Each extra hour | 0.000 | −0.001 to 0.001 | 0.85 |
>
> *Extra cut = −2 × coefficient; positive = a bigger reduction, other features held fixed. If we repeated this study many times, 95% of intervals built this way would contain the true effect.*
>
> Only winter has a clear association: during October–March events, ToU households cut about 0.015 kW more per household than during April–September events. One possible reason, not tested here, is that homes use more electricity in winter, so there is more to cut. Evening starts may add a little (0.008 kW), but the interval includes zero, and event length makes no detectable difference. The four features explain 15% of the variation between events (adjusted R² 0.09). Out of sample, the model is only slightly better than predicting the mean for every event (leave-one-month-out RMSE 0.0200 vs 0.0203 kW; better in 6 of 12 months), so it is a rough guide to timing, not a forecast.
>
> The residuals show no curve or funnel, and their Q-Q plot is close to a straight line apart from one event, H016 (3 February), the only one above the Cook's distance cut-off of 4/63. Without it, winter stays at 0.013 kW (p = 0.006) and no conclusion changes. The Durbin–Watson statistic is 1.27: events close in time share part of their error, so the HC3 intervals are probably somewhat too narrow. An exploratory check with Newey–West standard errors, which allow for this, keeps winter clear (p = 0.008). We keep the pre-stated HC3 results as the main ones.

**For slide 9 (When signals work best), one message:** "Winter High events get bigger cuts (about 0.015 kW more per household); start time and length add little."

## 6. Changes to log in `decisions.md` (for Sabrina)

1. **Exploratory Newey–West check added (11 Nov 2026).** Run only because Durbin–Watson = 1.27. Reported next to the pre-stated HC3 result, never instead of it, and logged as exploratory in `test_log.csv`.
2. **No Low-event regression.** `decisions.md` §11 said "Low events: modelled only if time allows". Stage 3 dropped Low events from the project on 10 Nov (`config.py`: `TARIFFS_USED = ["High"]`). That change also removes H2 from §7, so it needs its own dated entry if it isn't there yet.
3. **`log_test` helper.** `pipeline_lib.py` doesn't have `log_test` yet (Stage 0, step 5). `10_model.py` uses the guideline's version as a fallback. Once `log_test` is added to `pipeline_lib.py`, the script picks it up automatically.

## 7. How to run it

From the repository root, with `results/event_effects_main.csv` from Stage 3 in place:

```
python tests/test_10_model.py     # 5 checks on made-up data, a few seconds; writes nothing to results/
python src/10_model.py            # the real fit, a few seconds
```

Needs pandas, numpy, scipy, statsmodels and matplotlib. There are no random steps, so every run gives the same numbers. Each run appends 12 rows to `results/test_log.csv`, as the project's rules require.

## 8. Files

| File | What it is |
|---|---|
| `src/10_model.py` | The Stage 6 script (the `run_all.py` step `src/10_model.py`) |
| `tests/test_10_model.py` | Five checks on made-up events with known answers |
| `results/event_effects_main.csv` | Input: copy of Saniah's Stage 3 file |
| `results/regression_coefficients.csv` | Coefficients, HC3 standard errors, z, p and 95% intervals, in kWh/hh and kW |
| `results/regression_vif.csv` | Variance inflation factors |
| `results/regression_influence.csv` | Every event: effect, fitted value, residual, leverage, Cook's distance, flag |
| `results/regression_cook_refit.csv` | Coefficients with and without H016 |
| `results/regression_cv.csv` | Leave-one-month-out cross-validation, one row per held-out month |
| `results/regression_hac_exploratory.csv` | Exploratory Newey–West check |
| `results/results.json` | Key `p6_regression`: every number above |
| `results/test_log.csv` | The 12 logged coefficient tests |
| `figures/reg_resid_vs_fitted.png`, `reg_qq_residuals.png`, `reg_cooks_distance.png` | Diagnostic figures (appendix) |
