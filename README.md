# Do Price Signals Cut Household Demand?

**Team Megamind.** Modern Applied Statistics for Data Science, Dr. Sein Minn, Asian Institute of Technology (AIT), November 2026.

| Member | Stages |
|---|---|
| Sabrina Afrin | 0 (decisions), 7 (reproducibility) |
| Saniah Kayenat Chowdhury | 1 (data pipeline and EDA), 3 (scores) |
| Ahmad Jawid Fedayi (Javed) | 2 (events and matched days), 6 (regression) |
| Nyo Lae Hnin | 4 (distribution model and simulation) |
| Lin Htet Aung | 5a (estimates and decision), write-up, fresh-clone test |
| Arpan Ojha | 5b (hypothesis tests and sensitivity) |

---

## 1. Summary

| | |
|---|---|
| **Question** | When a household on a dynamic tariff gets a High-price signal, how much less electricity does it use during those hours than a similar household on a flat tariff? |
| **Decision-maker** | A utility product manager deciding whether to offer the dynamic tariff to all residential customers |
| **Decision rule** | Offer it only if the reduction is at least **T = 0.043 kW per household**: the break-even point where the tariff pays for itself |
| **Answer** | Tariff households cut **0.029 kW** per household during High events (95% CI 0.026 to 0.033 kW; 6.2% of normal use). The whole interval is below T, so the decision is **do not offer** |

*Interval wording used throughout: if we repeated this study many times, 95% of intervals built this way would contain the true effect.*

---

## 2. Background and data

**Trial.** In 2013, UK Power Networks' Low Carbon London trial put about 1,100 London households on a **dynamic time-of-use (ToU) tariff**. These households were sent the prices in advance. Electricity could be:

| Price | p/kWh |
|---|---|
| High | 67.20 |
| Low | 3.99 |
| Normal | 11.76 |

About 4,400 other households stayed on a **flat (Std) tariff** at 14.23p/kWh. Every household's smart meter recorded use every half-hour.

**Data.** *SmartMeter Energy Consumption Data in London Households*, from the London Datastore (CC BY 4.0):

- **Readings:** 168 CSV files (about 10 GB) of half-hourly readings for 5,566 households, 2011–2014.
- **Tariff schedule:** `Tariffs.xlsx`, the price for every half-hour of 2013 (69 High and 92 Low events).
- **Personal data:** households are identified only by a pseudonymous code. The data has no names, addresses or demographics.

**Important limitation.** Households **chose** to join the tariff group; they were not randomly assigned (confirmed in Schofield 2015, pp. 65–67). The results therefore apply to *households likely to sign up*, not to all customers.

Full details: [`DATA_CARD.md`](DATA_CARD.md).

---

## 3. Method in brief

For every household and every High event, we compare the household's use **during the event** with its use at **the same clock times on nearby normal days** ("matched days"). This gives an **event score**. Averaging a household's event scores gives its **household score**. We then compare the average household score of the ToU group with that of the Std group.

```
Raw readings ──► Stage 1: clean, build matrix (households × half-hours)
Tariff file  ──► Stage 2: find events and matched normal days
                         │
                         ▼
                 Stage 3: event scores ──► household scores
                         │
          ┌──────────────┼──────────────────┐
          ▼              ▼                  ▼
  Stage 4: check     Stage 5: estimate,   Stage 6: which events
  the method by      test, decide         get bigger cuts
  simulation         against T            (regression)
                         │
                         ▼
          Stage 7: one-command reproducibility
```

All rules were written down in [`docs/decisions.md`](docs/decisions.md) (Stage 0) before the results were computed.

---

## 4. Stages: who did what and what came out

### Stage 0: Decisions (Sabrina)
- **What was done:** fixed every rule in advance in `docs/decisions.md`:
  - the question, the threshold T and its sources;
  - data cleaning rules, event and matched-day rules, the scoring rules;
  - the hypotheses H1 and H2, the tests and intervals;
  - the four sensitivity runs, the regression model and the seeds.
- **T:** the yearly cost of the tariff per household (£2.14 for an in-home display) ÷ the yearly value of 1 kW less peak demand (£50). That gives T = 0.043 kW. A low case (0.017 kW) and a high case (0.179 kW) are also reported.
- **Schofield check:** confirmed that households opted in.
- **Changes after 9 November** are logged with dates at the bottom of `decisions.md`.
- **More detail:** [`README_P0_P7.md`](README_P0_P7.md).

### Stage 1: Data pipeline and EDA (Saniah)
- **What was done:** read the 168 CSVs and built the 2013 matrix (`H2013.npy`, 5,566 households × 17,520 half-hours).
- **Cleaning:**
  - 105,173 duplicate rows, all with identical values; the first was kept.
  - 12 `Null` readings, treated as missing and never as zero.
  - 38 households with no 2013 data, dropped.
  - No outliers removed.
- **EDA:**
  - In 2012, before the tariff, the groups had similar daily use (median 8.14 vs 8.43 kWh) and the same daily pattern.
  - ToU homes used 19% less at night. This is why sensitivity run C exists.
  - Meters use a fixed GMT clock.
- **Code:** `src/03_matrix.py`, `src/pipeline_lib.py`, `eda/profile_households.py`, `eda/make_figures.py`.
- **More detail:** [`README_P1.md`](README_P1.md), [`eda/README_EDA.md`](eda/README_EDA.md).

### Stage 2: Events and matched days (Ahmad Jawid)
- **What was done:**
  - found the 69 High events in 2013;
  - found the 212 "normal" days (all 48 half-hours at the Normal price);
  - for each event, found the matched days within ±14 days with the same day type (weekday or weekend).
- **Result:** 6 events have fewer than 3 matched days and are dropped, which leaves **63 usable High events**. The median event has 9 matched days.
- **Code:** `src/01_events.py`, `src/02_matched_days.py`, `stage2_events_matched_days.ipynb`.

### Stage 3: Scores (Saniah)
- **Event score:** mean kWh per half-hour during the event − mean at the same half-hours on the matched days.
- **Validity rules:**
  - A score counts only if at least 80% of the event's half-hours have readings and at least 3 matched days count.
  - A household needs at least 5 valid events.
- **Result:** **1,114 ToU and 4,396 Std households** in the main analysis. Exclusion tables are in `results/exclusions_*.csv`.
- **Code:** `src/04_event_scores.py`, `src/05_household_scores.py`.

### Stage 4: Distribution model and simulation (Nyo)
- **Distribution fit:** for 200 random households, lognormal and gamma models were fitted to half-hourly use and compared with three checks: AIC, a parametric-bootstrap KS test and Q-Q plots.
  - **The lognormal is better** for 86% of households.
  - Neither model fits exactly. The misfit is at the low end (a standby "floor"), in the top tail and in the zeros.
- **Simulation:** 1,000 simulated studies per scenario, where the true effect is known. Each used the real scoring code and the real test.
  - False positives: 5.9% (pass range 3.6–6.4%).
  - Interval coverage: 94.7% (pass range 93.6–96.4%).
  - Power at T: 100%.
  - Both stress tests (extra zeros and a heavy tail) pass.
- **Meaning:** the method can be trusted.
- **Code:** `src/06_distribution.py`, `src/07_simulation.py`, `tests/test_stage4.py`.
- **More detail:** [`README_P4.md`](README_P4.md).

### Stage 5a: Estimates and decision (Lin)
- **Effect:**
  - reduction 0.029 kW per household (95% CI 0.026–0.033);
  - 6.2% of normal use;
  - 1.46 MW less peak demand for 50,000 sign-ups.
- **Decision:** do not offer (central T), offer (low T), do not offer (high T).
- **Interval check:** resampling the real scores gives 94.2% coverage.
- **Also:** Lin restored the Low-event analysis (H2).
- **Code:** `src/08_estimates.py`, `src/inference.py`.
- **More detail:** [`reports/LIN_RESULTS.md`](reports/LIN_RESULTS.md).

### Stage 5b: Hypothesis tests and sensitivity (Arpan)
- **H1 tests:** during High events, ToU households use less than Std households.
  - One-sided Welch t-test: p = 2.0 × 10⁻⁴⁷.
  - Mann–Whitney check: p = 1.0 × 10⁻⁶⁸.
  - Cohen's d = −0.64.
  - All three methods agree.
- **Sensitivity runs:** A (±21 days), B (without off-grid events), C (without high night-use homes) and D (only households with ≥300 days) all give 0.028–0.030 kW and the same decision.
- **Code:** `src/09_tests.py`.
- **More detail:** [`README_P5.md`](README_P5.md).

### Stage 6: Regression (Ahmad Jawid)
- **What was done:** explained the effect of each of the 63 events by its features: evening start, length, winter, and a Low period just before.
- **Result:**
  - Only **winter** has a clear link: 0.015 kW more cut per household (p = 0.003).
  - The model beats a simple average only slightly in leave-one-month-out cross-validation (RMSE 0.0200 vs 0.0203 kW). It is a rough guide, not a forecast.
- **Code:** `src/10_model.py`, `tests/test_10_model.py`.
- **More detail:** [`README_P6.md`](README_P6.md).

### Stage 7: Reproducibility (Sabrina, with Lin's fresh-clone test)
- **What was done:**
  - one command (`run_all.py`);
  - pinned package versions;
  - all seeds fixed at 2013;
  - a data card;
  - this README.
- **Fresh-copy check:** every number reproduced to within rounding error (relative difference below 10⁻¹³).
- **More detail:** [`README_P0_P7.md`](README_P0_P7.md).

### Stages 8–9: Report and presentation (everyone)
- Each member writes the report section and slides for their own stage.
- Ready-to-use text is in each stage README and in `reports/`.

---

## 5. Key results

| Result | Value |
|---|---|
| **High-event reduction (H1)** | **0.029 kW** per household, 95% CI 0.026–0.033 (6.2% of normal use) |
| Welch / Mann–Whitney p-values | 2.0 × 10⁻⁴⁷ / 1.0 × 10⁻⁶⁸ |
| **Decision at T = 0.043 kW** | **Do not offer**: the reduction is real but too small to pay for the tariff |
| Decision at low T (0.017) / high T (0.179) | Offer / do not offer |
| Sensitivity runs A–D | 0.028–0.030 kW; same decision |
| Method check (simulation) | All 4 scenarios pass |
| When signals work best | Winter events: +0.015 kW cut |
| Low events (H2, for information) | ToU households use **0.033 kW more** when electricity is cheap (95% CI 0.029–0.037) |

The full explanation with figures is in **[`RESULTS.md`](RESULTS.md)**. Every number comes from `results/results.json`.

---

## 6. Limitations

1. **Opt-in households.** Results apply to households likely to sign up, not to all customers.
2. **Shared events.** All households share the same events and matched days, so intervals may be somewhat too narrow. The regression's Durbin–Watson of 1.27 points the same way.
3. **Simulated power is optimistic.** Simulated households do not vary their response from event to event, so real power is probably lower.
4. **Average over the event, not the network peak.** The reduction is an average over each event's hours, not the network's peak moment.
5. **T rests on published cost figures.** It is not based on costs measured in the trial, which is why three cases are reported.
6. **Order of rules and results.** Git history cannot prove that the rules came before the results (`docs/decisions.md`, Changes, 13 Nov).

---

## 7. How to run

**Requirements.** Python 3.12 (tested with 3.12.14). Exact package versions are in `requirements-lock.txt`.

```bash
# 1. Install
python3.12 -m venv env
source env/bin/activate            # Windows: env\Scripts\activate
python -m pip install -r requirements-lock.txt
```

**2. Data.** Large files are not in Git.
- `data/raw/Tariffs.xlsx` is included.
- Put the 2013 matrix at `data/interim/H2013.npy` (390 MB, from Saniah's pipeline zip). Alternatively, unzip the 168 London Datastore CSVs into `data/raw/` and use `--from-raw`.

```bash
# 3. Run everything (stops at the first error)
python run_all.py                  # a few minutes with H2013.npy
python run_all.py --from-raw       # rebuilds the matrix from the CSVs (up to 2-3 hours)

# 4. Automated tests
python -m pytest -q

# 5. Check that outputs match the committed ones exactly
python scripts/verify_reproduction.py
```

`run_all.py` runs, in order:

1. results gate check
2. events and matched days
3. matrix (`--from-raw` only)
4. scores
5. estimates
6. tests
7. regression
8. write-up
9. EDA figures

**Rebuilt separately because they are slow:**

```bash
python src/06_distribution.py                 # Stage 4 fit, ~1 minute
python src/07_simulation.py                   # Stage 4 simulation, ~1 hour
python eda/profile_households.py data/raw eda # EDA tables from the 10 GB of CSVs, 20-40 minutes
```

### Random seeds

Every random step uses **seed 2013**.

| Random step | Script |
|---|---|
| 200-household sample, 500-reading draw, KS simulations | `src/06_distribution.py` (`default_rng(2013)`) |
| Simulation study, 4 × 1,000 trials | `src/07_simulation.py` (`SeedSequence(2013)`, one child seed per trial) |
| Bootstrap intervals, 10,000 resamples | `src/08_estimates.py`, `src/inference.py`, `src/09_tests.py` |
| Resampling coverage check | `src/08_estimates.py` (`SeedSequence(2013)`) |
| Leave-one-month-out cross-validation | `src/10_model.py` (no random step) |

---

## 8. Outputs

| Output | Where |
|---|---|
| Every reported number | `results/results.json`, written by code with `save_result()` |
| Every test ever run, including exploratory ones (append-only) | `results/test_log.csv`, written with `log_test()` |
| Tables | `results/*.csv` |
| Figures | `figures/` (see below) |

### Which script makes which figure

| Figure | Script |
|---|---|
| `figures/eda/fig1_high_by_hour.png`, `fig2_load_curve_2012.png`, `figB1_coverage.png`, `figB2_kwh_distribution.png`, `figB3_daily_kwh_2012.png` | `eda/make_figures.py` |
| `figures/stage2_matched_days.png` | `stage2_events_matched_days.ipynb` |
| `figures/qq_p10.png`, `qq_p50.png`, `qq_p90.png`, `qq_worst.png` | `src/06_distribution.py` |
| `figures/decision.png`, `decision.svg` | `src/08_estimates.py` |
| `figures/qq_household_scores_high.png`, `bootstrap_hist_high.png` | `src/09_tests.py` |
| `figures/assumptions_high.png`, `assumptions_low.png` | `src/09b_tests_high_low.py` |
| `figures/reg_resid_vs_fitted.png`, `reg_qq_residuals.png`, `reg_cooks_distance.png` | `src/10_model.py` |
| `figures/model_diagnostics_supporting.png` | `src/10b_model_supporting.py` |

**Supporting scripts by Lin.** `src/09b_tests_high_low.py` tests High and Low events. `src/10b_model_supporting.py` is a second fit of the regression. Their numbers match the official Stage 5b and Stage 6 scripts. Their output files carry `_high_low` or `_supporting` in the name.

---

## 9. Folder map

| Folder or file | Contents |
|---|---|
| `src/` | all analysis scripts, numbered in run order |
| `tests/` | automated checks |
| `results/` | tables, `results.json`, `test_log.csv` |
| `figures/` | all figures |
| `eda/` | EDA scripts and summary tables |
| `docs/` | `decisions.md`, statistics and program guides, provenance, Arpan's Stage 5 notes, course documents (`docs/course/`) |
| `reports/` | report sections, speaker notes, reproducibility record |
| `slides/` | slide content |
| `submissions/` | earlier copies of `results.json`, kept for provenance |
| `data/` | `raw/` (`Tariffs.xlsx`; CSVs go here) and `interim/` (`H2013.npy`); not in Git |
| `README_P0_P7.md`, `README_P1.md`, `README_P4.md`, `README_P5.md`, `README_P6.md` | each stage owner's detailed README |
| `RESULTS.md` | all results explained, stage by stage |
| `DATA_CARD.md` | data source, licence, cleaning counts, limitations |

---

## 10. Status and open items

1. **Scope.** Stages 3, 5b and 6 focus on High events (H1). Lin's work also covers Low events (H2), as `decisions.md` §7 planned. The team should confirm in `decisions.md` whether the report includes H2.
2. **Final fresh-clone test.** Lin should clone from GitHub, run `run_all.py` with the pinned packages (including statsmodels for Stage 6), and confirm with `verify_reproduction.py`.
3. **GitHub.** Push the `team-integrated` branch to [SaniahKayenat/Megamind](https://github.com/SaniahKayenat/Megamind). Keep the hidden `.git` folder, because the results gate needs it.

---

## 11. Credits and sources

- **Data:** UK Power Networks, *SmartMeter Energy Consumption Data in London Households*, [London Datastore](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d), CC BY 4.0.
- **Trial analysis:** Schofield, J. (2015). PhD thesis, Imperial College London, <https://spiral.imperial.ac.uk/handle/10044/1/25575>.
- **Threshold sources:** DECC (2014), BEIS (2016), Sustainability First (2012) and EnAppSys (GB Capacity Market T-4 auction for 2026/27). Full links are in [`docs/decisions.md`](docs/decisions.md).
