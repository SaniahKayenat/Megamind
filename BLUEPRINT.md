# BLUEPRINT — "Do Price Signals Cut Household Demand?"

> **To the AI assistant reading this:** this file is the complete specification of a university statistics project. Treat it as the single source of truth. Every rule in §5 is **fixed in advance and must not be changed** to get a nicer result; if something seems wrong, say so and propose a dated entry for the "Changes" log instead of silently changing it. When asked to write code, follow the file names, column names, units, seeds and conventions exactly (§7–§8), so pieces written by different people fit together. Never invent data or results; every number in the report must come from code.

---

## 1. Project summary

| Item | Value |
|---|---|
| Course | Modern Applied Statistics for Data Science (Dr Sein Minn, Asian Institute of Technology) |
| Team (6) | Saniah, Sabrina, Javed (Ahmad Jawid Fedayi), Arpan, Lin (Lin Htet Aung), Nyo (Nyo Lae Hnin) |
| Repository | https://github.com/SaniahKayenat/Megamind |
| Question | When a household on a dynamic tariff is sent a High-price signal, how much less electricity does it use during those hours than a similar household on a flat tariff? |
| Decision-maker | A utility product manager deciding whether to offer a dynamic tariff to all residential customers |
| Decision rule | Compare the reduction per household (kW) and its 95% interval with a break-even threshold T = 0.043 kW (§5.8) |
| Deliverables | (1) report, 3–4 pages + appendices; (2) repository that reproduces every figure and number with one command; (3) 12-min talk + 5-min Q&A |
| Proposal | Submitted 18 Oct 2026; feedback received (§6) |

### Grading (100 marks)
1 Research question & decision (10) · 2 Data & EDA (10) · 3 Distributional modelling (15) · 4 Estimation & uncertainty (15) · 5 Hypothesis testing (15) · 6 Modelling & validation (15) · 7 Ethics & data handling (10) · 8 Documentation & reproducibility (10).
Course's central rule: *a p-value without evidence about its assumptions cannot pass.* Also penalised: interpreting a 95% CI as a 95% probability; reporting only significant runs; removing outliers to force a fit; "X3 was significant" without units.

---

## 2. Background

- Household demand peaks in the early evening; networks are sized for the peak. A **dynamic time-of-use tariff** announces High prices a day ahead on stressed days (and Low prices at other times) to shift demand.
- **Low Carbon London trial** (UK Power Networks, 2011–2014): ~5,500 London households with half-hourly smart meters. In **2013**, ~1,100 (**ToU** group) were on the dynamic tariff, signalled by in-home display and SMS. The rest (**Std**) paid a flat 14.23 p/kWh.
- Prices: **High 67.20**, **Normal 11.76**, **Low 3.99** p/kWh.
- ToU households **opted in** (not randomised): "988 opted to receive the experimental dToU tariff" (arXiv:1605.08078). Results apply to households likely to sign up.

---

## 3. Data

**Source:** London Datastore, "SmartMeter Energy Consumption Data in London Households" (https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d). Licence **CC BY 4.0** (credit UK Power Networks). Raw data (~10 GB) is NOT committed; it lives in `data/raw/`.

### 3.1 Household readings — 168 CSVs (~1M rows each; a 169th non-readings file must be skipped)
| Column | Notes |
|---|---|
| `LCLid` | household code, e.g. `MAC000002` (pseudonymous) |
| `stdorToU` | `Std` or `ToU`; constant per household in all years (no household switches) |
| `DateTime` | e.g. `2013-01-01 00:30:00.0000000` → parse first 19 chars; **fixed GMT clock (no daylight saving)** |
| `KWH/hh (per half hour) ` | **text**, column name has a **trailing space**, missing = `Null`, resolution 0.001 kWh |

### 3.2 Tariff schedule — `Tariffs.xlsx`
Two columns (timestamp, `High`/`Low`/`Normal`), **17,520 rows** = every half-hour of 2013, no gaps, fixed clock.
- High: 788 half-hours (4.5%) in **69 events**; lengths 3h×26, 4h×1, 6h×34, 12h×7, 24h×1.
- Low: 1,660 half-hours in **92 events**. Normal: 15,072. **212 all-Normal days.**
- 52% of High half-hours fall 17:00–23:00 (rest spread over the day) → measure each event's own hours, not a fixed evening window.
- Events start/end on a 3-hour grid (23, 02, 05, 08, 11, 14, 17, 20 h) except on **2013-01-29, 2013-02-09, 2013-03-21** ("off-grid").

### 3.3 EDA results (already computed by `profile_households.py`)
| Measure | Value |
|---|---|
| Rows 2012 / 2013 | 60,410,060 / 93,087,837 |
| Null kWh | 5,548 (2012) / 12 (2013) |
| Duplicate (household,time) rows | 105,173 (0.07%) |
| Households | ToU 1,123; Std 4,443; mixed labels 0 |
| No 2013 data | ToU 6; Std 32 |
| ≥300 days 2013 | ToU 1,047 (93%); Std 4,140 (93%) |
| Drop-out during 2013 | ToU 1,111→1,047 (−6%); Std 4,404→4,087 (−7%) |
| Meter installation | Jan–Oct 2012 (few before May 2012) |
| Median daily kWh 2012 | ToU 8.14; Std 8.43; standardised diff −0.09 |
| 2012 daily shape | Same; ToU 19% lower 00:00–06:00, 3% lower 17:00–23:00; Std spike at 00:30 (timed night loads) |
| 2013 half-hourly kWh | median ≈0.12; p95 0.79; p99 1.47; log-scale skewness −0.07 (→ lognormal) |
| Zeros | ToU 1.18%; Std 1.27% |
| >5 kWh readings | 2,678 |
| Clock check | 99.7% of households have 48 readings on 2013-03-31 and 2013-10-27 → fixed clock, same as tariff |

---

## 4. Study design (and why)

1. **Event score** (household h, event e) = mean kWh per half-hour during the event's half-hours − mean kWh per half-hour at the **same clock half-hours** on its **matched normal days**. Negative = used less than usual.
2. **Household score** = mean of the household's valid event scores (High and Low separately).
3. **Tariff effect** Δ = mean ToU household score − mean Std household score (kWh per half-hour).
4. **Reduction per household (kW)** = −2 × Δ (for High events). Scale: × 50,000 households ÷ 1,000 = MW.
5. **Decision:** compare the reduction's 95% CI with T = 0.043 kW.

Why:
- **Self-comparison** removes fixed household differences.
- **Same clock times on nearby same-type days** remove time-of-day, season and weekday effects.
- **The Std group** removes the "busy day" effect (events placed on high-demand days) → difference-in-differences.
- **One value per household** because readings within a household are dependent; households are the independent units.
- **Missing readings are never zero**; the same half-hours are used on both sides.
- **One-sided tests** because the question is directional and stated in advance.

Rejected alternatives:
- a fixed evening window (only half the High hours are in the evening);
- ToU 2012 vs 2013 (confounded by year);
- a year-on-year difference-in-differences (weaker, loses data);
- two separate paired tests (not a group comparison);
- a 2012 placebo test (dropped by team decision);
- pooling all readings into one test (pseudo-replication).

---

## 5. FIXED DECISIONS (from `docs/decisions.md`, 9 Nov 2026)

### 5.1 Data rules
- Analysis uses **2013**. 2012 only describes groups and defines high night-use homes.
- **Duplicates:** keep the **first** valid reading; report the count and how many are identical.
- `Null` = missing, never 0. **No outlier removal.**
- **Fixed GMT clock**; no adjustment. Times reported as GMT.
- Households with no 2013 data are dropped (6 ToU, 32 Std).

### 5.2 Events
- **Event** = a run of consecutive half-hours with the same non-Normal price.
- **day_type** = weekday, or weekend (Sat/Sun or 2013 England bank holiday: 01-01, 03-29, 04-01, 05-06, 05-27, 08-26, 12-25, 12-26), taken from the **start date**.
- **off_grid** = start or end not on the 3-hour grid.
- **low_before** = the half-hour just before the event is Low.
- **evening** = starts at 17:00 or 20:00.
- **winter** = starts in Oct–Mar.

### 5.3 Matched days
- **Normal day** = all 48 half-hours Normal (212 days).
- **Matched shift k** (days, k ≠ 0): the event slots + 48k stay inside 2013, every date touched is a normal day, and the shifted start date has the same day_type.
- **Main window |k| ≤ 14.** Sensitivity A: |k| ≤ 21.
- **Events with < 3 matched days are dropped**: 6 High (2013-01-07, 09-29, 12-08, 12-15, 12-21, 12-28) and 15 Low at ±14 → **63 usable High events** (median 9 matched days). At ±21: 2 High and 5 Low lack 3 days.

### 5.4 Scores
- A matched day counts if it has ≥80% of the half-hours that are present on the event day.
- A **valid** event score needs event coverage ≥80% and ≥3 counted matched days.
- **Household score** needs **≥5 valid events** of that type.
- **Units:** kWh per half-hour in files; ×2 = kW; % of normal use = Δ ÷ mean matched-day use of ToU households × 100.

### 5.5 Hypotheses & tests
- **H1** (High): mean ToU score < mean Std score. **H2** (Low): mean ToU score > mean Std score.
- Primary: **one-sided Welch t-test**, α = 0.05. Check: one-sided **Mann–Whitney**.
- **No multiple-testing correction** (separate questions; both reported).
- Effect sizes with every p-value: Δ in kWh/hh, kW, %, and **Cohen's d** (pooled SD).
- **CI:** 95% percentile bootstrap, households resampled **within each group**, **10,000** resamples.
- **CI wording (mandatory):** "If we repeated this study many times, 95% of intervals built this way would contain the true effect." Never "95% probability".
- **Every test** is logged to `results/test_log.csv`; nothing is deleted.

### 5.6 Sensitivity runs (all reported in one table)
| Run | Change |
|---|---|
| A | matched window ±21 (proposal said ±7; changed because ±7 leaves 16/69 High events unusable) |
| B | exclude off-grid events |
| C | exclude high night-use homes: top 10% of 2012 night share (kWh 00:00–06:00 ÷ total) among households with ≥60 days of 2012 data |
| D | only households with ≥300 days of 2013 data |

### 5.7 Distribution (criterion 3) & simulation
- **Sample:** 200 households with ≥300 days of 2013 data, `rng = np.random.default_rng(2013)`, `rng.choice(sorted_ids, 200, replace=False)`.
- **Readings:** normal-day readings only, non-zero; draw **500 per household** at random (same rng).
- **Models:** lognormal and gamma, maximum likelihood, `floc=0`. Compare with **AIC** = 4 − 2·logL.
- **Goodness of fit:** parametric-bootstrap KS (B = 199, refit each time), p = (1 + #{D* ≥ D}) / 200, α = 0.05.
- **Q-Q plots:** households at the 10th/50th/90th percentile of daily use + the worst lognormal fit.
- **Why lognormal:** positive, right-skewed, multiplicative mechanism (occupancy × appliances × duration); log-scale skewness −0.07. **Why gamma:** competing additive mechanism (sum of appliance loads).
- **Purpose:** the fit drives the **simulation**; the tests on household means don't assume it (central limit theorem).
- **Simulation:** 1,000 trials per scenario, using the real `score_event()` and real group sizes, events and matched shifts. Readings = exp(μ + d + σ_within·z), with d ~ N(0, σ_day) per household-day; σ_day = median across sampled households of the SD of daily mean log-use on normal days; σ_within = √max(σ² − σ_day², 0.01). The effect is applied to ToU event-day readings multiplicatively, so the mean reduction = δ.

| Scenario | δ | Pass if |
|---|---|---|
| Null | 0 | rejection rate 3.6–6.4% |
| Threshold | T = 0.0215 kWh/hh | coverage 93.6–96.4%; power reported |
| Stress null / stress threshold | 0 / T, plus 1.2% zeros and the top 5% of households ×3 | same |

### 5.8 Threshold T and decision rule
T = yearly cost per household ÷ yearly value of 1 kW less peak.

| Input | Value | Source |
|---|---|---|
| In-home display cost | £15 | DECC 2014 IA, Table 3-1 |
| Display lifetime | 7 years → £2.14/yr | BEIS 2016 CBA §2.12.1 |
| Tariff revenue | revenue-neutral | assumption |
| Avoided network reinforcement | £40–60 per kW per year (central £50) | Sustainability First 2012, p.31 |
| Generation capacity (upper case) | £63 per kW per year | GB Capacity Market T-4 2026/27 |
| Running cost (high case) | £5/yr | assumption |

- **Central T = 2.14/50 = 0.043 kW** (0.021 kWh/hh). Low case 0.017 (2.14/123); high case 0.179 (7.14/40).
- **Rule** (High-event reduction in kW): **offer** if the CI's lower end ≥ 0.043; **don't offer** if its upper end < 0.043; otherwise **inconclusive → bigger pilot**. Also report the decision under the low and high cases. H2 has no threshold.

### 5.9 Regression (criterion 6)
- One row per **usable High event** (~63).
- Outcome = event's mean ToU score − mean Std score (households in the main analysis).
- `effect ~ evening + hours + winter + low_before`, OLS, **HC3** SEs → **5 parameters** (~13 events each).
- **No month predictor:** it adds 11 parameters and breaks leave-one-month-out CV.
- If any **VIF > 5**, drop `hours`.
- **Baseline** = mean effect.
- **Validation:** leave-one-month-out CV, RMSE of model vs baseline.
- **Diagnostics:** residuals vs fitted; Q-Q of residuals; Cook's distance > 4/n (refit without); Durbin–Watson in date order.
- **Interpretation:** coefficient × 2 = kW per household (more negative = bigger cut). If the model doesn't beat the baseline, report "timing/length don't predict response".

### 5.10 Seeds
2013 for every random step (sample, reading draw, bootstrap, KS simulations, simulation study, resampling coverage). Leave-one-month-out CV has no random step.

---

## 6. Feedback on the proposal → response
Praised: the self-comparison + control design, pre-stated H1/H2, the worked example. Raised:
1. **No threshold** → T = 0.043 kW + three-way rule (§5.8).
2. **Regression with 69 rows and month vs LOMO CV** → 5 parameters, no month (§5.9).
3. **"What is the lognormal fit for?"** → it drives the simulation that checks false positives, coverage and power (§5.7).

Other changes from the proposal:
- no Holm correction;
- placebo test dropped;
- ±7 → ±21 for run A;
- all Std households used (not a sample of 1,500).

---

## 7. Repository layout, scripts, file formats

```
data/raw/            168 CSVs + Tariffs.xlsx (gitignored)
data/interim/        H2013.npy, H2012.npy (gitignored)
docs/decisions.md    fixed rules (commit BEFORE scoring)
src/                 scripts below
tests/test_score_event.py
results/             small tables, results.json, test_log.csv
figures/
run_all.py, requirements.txt, DATA_CARD.md, README.md
```

| Script | Stage | Owner | Status |
|---|---|---|---|
| `src/config.py`, `src/pipeline_lib.py` | shared | Saniah | written (`score_event`, `save_result`, `clean_chunk`, `raw_files`) |
| `src/profile_households.py`, `src/make_figures.py` | EDA | — | done |
| `src/01_events.py`, `src/02_matched_days.py` | 2 | Javed | written & tested on real Tariffs.xlsx |
| `src/03_matrix.py` | 1 | Saniah | written, not yet run on real data |
| `src/04_event_scores.py`, `src/05_household_scores.py`, `src/run_p1.py` | 3 | Saniah | written, tested on synthetic data |
| `src/06_distribution.py`, `src/07_simulation.py` | 4 | Nyo | to write |
| `src/08_estimates.py` | 5 | Lin | to write |
| `src/09_tests.py` | 5 | Arpan | to write |
| `src/10_model.py` | 6 | Javed | to write |
| `run_all.py` | 7 | Sabrina | to write |

### File formats (column names are contracts)
| File | Columns |
|---|---|
| `results/events.csv` | event_id (H000/L001…), tariff, start, first_slot (0–17519), n_slots, end, hours, day_type, off_grid, low_before, evening, month, winter |
| `results/normal_days.csv` | date, day_type |
| `results/matched_days.csv` | event_id, shift_days (\|k\| ≤ 21) |
| `results/matched_counts.csv` | event_id, tariff, start, n_matched_14, n_matched_21 |
| `data/interim/H2013.npy` | float32 [households × 17,520], NaN = missing; row order = households_index.row |
| `results/households_index.csv` | LCLid, group, readings_2013, days_2013, readings_2012, days_2012, kwh_2012, kwh_night_2012, row, mixed_label, night_share_2012, high_night |
| `results/event_scores_w{14,21}.csv.gz` | LCLid, group, event_id, tariff, event_mean, matched_mean, score, cover, n_days, valid |
| `results/household_scores_{main,A,B,C,D}.csv` | LCLid, group, tariff, n_events, score, normal_use, event_use |
| `results/exclusions_{variant}.csv` | tariff, group, households, dropped: <reason>…, kept |
| `results/event_effects_{variant}.csv` | event columns + tou_mean, std_mean, n_tou, n_std, effect |
| `results/test_log.csv` | timestamp, git_commit, person, hypothesis, run, test, statistic, p_value, effect, note |
| `results/results.json` | one key per reported number |

**Slot** = (timestamp − 2013-01-01 00:00) / 30 min; slot 34 = 17:00; a shift of k days = +48k slots.

### `score_event(H, slots, shifts)` — the single scoring definition (in `pipeline_lib.py`)
```
ev = H[:, slots]; present = ~isnan(ev); cover = present.mean(1)
M = stack(H[:, slots + 48k] for k in shifts)            # households × days × half-hours
M[~present broadcast] = NaN                             # same half-hours on both sides
day_ok = count_nonnan(M, axis=half-hours) >= 0.8 * present.sum(1)
M[~day_ok] = NaN
score = nanmean(ev) - nanmean(M over days × half-hours)
valid = cover >= 0.8 and day_ok.sum(1) >= 3 and isfinite(score)
```
The real analysis, sensitivity runs and simulation **must** all call this function.

---

## 8. Conventions
- `rng = np.random.default_rng(2013)`; never `np.random.seed` or unseeded calls.
- Every reported number → `save_result(key, value)` → `results/results.json`. The report uses only these numbers.
- Every test → `log_test(person, hypothesis, run, test, statistic, p_value, effect, note)`.
- Paths only from `config.py`. Run scripts from the repo root as `python src/<script>.py`.
- **Sign convention:** Δ = ToU − Std; High-event reduction (kW) = −2Δ. In `scipy` one-sided tests, pass **ToU first** (`alternative="less"` for H1, `"greater"` for H2).
- **Results gate:** nobody computes or looks at real effects, CIs, tests or the regression until `decisions.md`, T and the simulation results are committed.
- Git: a branch per person, a pull request reviewed by one other person, never commit raw or interim data.
- Python ≥3.11; pandas, numpy, scipy, statsmodels, matplotlib, openpyxl; exact versions pinned in `requirements.txt`.

---

## 9. Stages, owners and acceptance checks

| Stage | Owner | Output | Must match / pass |
|---|---|---|---|
| 0 Decisions | Sabrina (+Javed) | `docs/decisions.md` committed; Schofield §4.4 checked; `log_test` added | commit precedes any scoring |
| 1 Matrix | Saniah | H2013/H2012, households_index, duplicates_check | ToU 1,123 / Std 4,443; mixed 0; rows_2013 ≈ 93.09M; null_2013 = 12; duplicates ≈ 105k; no-2013-data ToU 6 / Std 32 |
| 2 Events | Javed | events, normal_days, matched_days, matched_counts | 69/92 events; off-grid dates as §3.2; 212 normal days; 6 High & 15 Low with <3 matched at ±14; 63 usable High |
| 3 Scores | Saniah | event_scores_w14/w21, household_scores_*, exclusions_*, event_effects_* | ~1,100 ToU / ~4,400 Std High scores; one score hand-checked from the raw CSV |
| 4 Distribution + simulation | Nyo (+Saniah) | dist_fits.csv, Q-Q figures, simulation_trials.csv | false positives 3.6–6.4%; coverage 93.6–96.4%; power reported |
| — Results gate | all | everything above committed | — |
| 5a Estimates | Lin | Δ, kW, %, MW, bootstrap CI (High, Low); decision vs T (central/low/high); resampling coverage; decision figure | numbers in results.json |
| 5b Tests | Arpan | assumption plots; Welch + MWU for H1/H2; Cohen's d; sensitivity table (main, A–D) | all runs in test_log |
| 6 Regression | Javed | coefficients (HC3), VIFs, diagnostics, LOMO-CV RMSE vs baseline, kW interpretation | 5 parameters; no month |
| 7 Reproducibility | Sabrina; fresh-clone test by Lin | run_all.py, requirements.txt, seeds in README, DATA_CARD.md | fresh clone reproduces results.json exactly |
| 8–9 Report & talk | everyone | report ≤4 pages + appendices; 12-min deck | numbers checked against results.json |

Runtime: matrix ~30 min; simulation 1–2 h; everything else minutes. `run_all.py` total ≈ 2–3 h.

---

## 10. Current progress (9 Nov 2026)
- Done: dataset/question; EDA run on full data; figures; proposal submitted; feedback received; `decisions.md` written (**to commit**); Stage 1–3 code written and tested on synthetic data in the real format (5 unit tests pass; one score hand-verified from raw CSV); Stage 2 scripts tested on the real Tariffs.xlsx (counts in §9 confirmed).
- In progress: check how ToU households were chosen (evidence says opt-in).
- Not started: running Stage 1 on real data; Stages 4–9.
- Trackers: shared task tracker (owners per §9) and a project guideline document exist on claude.ai.

---

## 11. Report outline (3–4 pages)
| Section | Pages | Content |
|---|---|---|
| 1 Question & decision | 0.4 | Question, manager, consequences of error, T and rule |
| 2 Data & EDA | 0.6 | Source/licence, cleaning table with counts, price-schedule figure, 2012 load-curve figure, exclusions, 63 usable High events |
| 3 Distribution | 0.5 | Mechanism → lognormal/gamma, fit table, one Q-Q, where it breaks, simulation table & power |
| 4 Estimates | 0.5 | Δ (kW, %), CI, MW at scale, coverage, correct CI wording |
| 5 Tests | 0.6 | H1/H2 with effect sizes; sensitivity table |
| 6 Model | 0.5 | Coefficients in kW, CV vs baseline, diagnostics |
| 7 Ethics | 0.3 | Licence; pseudonymous IDs (no direct identifiers, none removed); all exclusions with before/after; all tests logged |
| 8 Conclusion | 0.3 | Decision vs T (figure), who it applies to, when signals work best, what would change it |

Appendices: cleaning log, extra EDA figures, all Q-Q plots, full sensitivity table, diagnostics, test log, glossary, worked example.

**Worked example** (illustrative): ToU A 0.30 vs 0.36 → −0.06; ToU B 0.25 vs 0.27 → −0.02; Std C 0.42 vs 0.40 → +0.02; Std D 0.31 vs 0.30 → +0.01. ToU mean −0.04, Std mean +0.015 → Δ = −0.055 kWh/hh = 0.11 kW reduction; ×50,000 = 5.5 MW.

---

## 12. Q&A preparation
- **CI meaning:** method captures the truth in 95% of repeated studies; not a probability for this interval.
- **Why Welch:** unequal spreads; Mann–Whitney and bootstrap agree.
- **Why Std group:** removes the busy-day effect.
- **Volunteers:** opt-in → applies to likely sign-ups; groups similar in 2012 (8.1 vs 8.4 kWh/day).
- **No multiplicity correction:** separate questions, both reported.
- **No placebo test:** analysis kept within 2013.
- **Why 0.043 kW:** £2.14/yr ÷ £50/kW/yr, fixed before results, with a range.
- **What the lognormal is for:** simulation of false positives, coverage and power; the tests don't assume it.
- **63 events too few?** 5 parameters, ~13 events each; LOMO CV; baseline; a guide, not a forecast.
- **Why 6 events dropped:** fewer than 3 nearby normal comparison days.
- **Why ±21 not ±7:** ±7 loses 16 High events.

---

## 13. Sources
- London Datastore dataset: https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d
- Schofield (2015), Imperial College PhD thesis: https://spiral.imperial.ac.uk/handle/10044/1/25575
- Bhattacharya et al., arXiv:1605.08078: https://ar5iv.labs.arxiv.org/html/1605.08078
- DECC (2014) smart-meter IA: https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/276656/smart_meter_roll_out_for_the_domestic_and_small_and_medium_and_non_domestic_sectors.pdf
- BEIS (2016) smart-meter CBA: https://assets.publishing.service.gov.uk/media/5a7f59f9ed915d74e6229eef/OFFSEN_2016_smart_meters_cost-benefit-update_Part_I_FINAL_VERSION.PDF
- Sustainability First (2012) Paper 4: https://sustainabilityfirst.org.uk/wp-content/uploads/2012/06/Sustainability-First-GB-Electricity-Demand-Paper-4-What-demand-side-services-can-provide-value-to-the-electricity-sector-June-2012.pdf
- EnAppSys, Capacity Market T-4 2026/27: https://www.enappsys.com/t-4-capacity-market-auction-for-the-delivery-year-2026-27-has-cleared-at-an-all-time-high-price-of-63-kw-year/

## Changes log
(none recorded in the supplied file)

11 November 2026: this continuation restores original High-and-Low scope after the
High-only handoff, records Nyo's inherited implementation details, clarifies signed
effects versus reductions and conditional percentage intervals, and records the absent
historical Git evidence. See the appended changes in docs/decisions.md and PROVENANCE.md.
No original fixed rule above was edited.

11 November 2026: repaired first-valid-duplicate handling and pre-deduplication raw
row counting for future raw rebuilds. Supplied matrices remain unchanged; original
CSV verification is unavailable. See the later implementation-repair entry in decisions.
