# Data pipeline (Stages 1 and 3): Saniah

**Status: done (10 Nov 2026).** All checks passed. The results are in `results/` and are ready for the next steps.

**Scope: High-price events only.** Low events are not part of the project.

---

## 1. What this step does, in one paragraph

We want to know whether households on the dynamic tariff (ToU) cut their electricity use when they get a High-price signal, compared with households on the flat tariff (Std). This step turns 93 million raw meter readings into **one number per household**: on average, how much more or less electricity the household used during High-price events than it normally uses at those same hours. A negative number means it used less than usual. Every later step (tests, simulation, regression, sensitivity runs, data card) starts from these numbers.

## 2. How it fits with Javed's work (Stage 2)

Javed found the 69 High-price events in 2013, the 212 normal days (days with no price signal at all) and, for each event, its **matched days**: normal days of the same type (weekday or weekend) within ±21 days.

- **I measured what each household did** at those times, using his matched days as the comparison.

Javed's files used here: `results/events.csv` and `results/matched_days.csv`.

## 3. What I did, step by step

### Step 1: Put all readings into one table (`03_matrix.py`)

The raw data is 168 CSV files with one reading per row. I put every 2013 reading into one large table, the **matrix**:

- one row per household (5,566);
- one column per half-hour of 2013 (17,520).

A second matrix for 2012 is used only to describe households, not to measure the effect.

Rules used while filling it:

- **"Null" readings are missing, not zero.** There were 12 in 2013 and 5,548 in 2012.
- **Duplicates: keep the first copy.** 105,173 rows repeated a household and time. All of them had exactly the same kWh value, so this choice changes nothing.
- **No outliers removed.** A very high reading is still a real reading.
- **Fixed GMT clock.** No daylight-saving shift, so every day has 48 half-hours.

The same pass also recorded, for each household:

- how many days of 2013 data it has;
- its **2012 night share**: the part of its electricity used between 00:00 and 06:00.

The top 10% of households by night share (more than 20.9% of their use at night) are flagged as **high night-use homes**. These are usually homes with timers or storage heaters.

Result: 93,024,217 readings kept for 2013. 1,123 ToU and 4,443 Std households. No household changed tariff group.

### Step 2: Score every household on every High event (`04_event_scores.py`)

For each household and each High event:

1. **Event use:** the household's average kWh per half-hour during the event.
2. **Normal use:** its average kWh per half-hour at **the same half-hours** on the event's matched days.
3. **Score = event use − normal use.**

Example: an event runs 17:00–20:00 on a Tuesday. We compare the household's use from 17:00 to 20:00 that Tuesday with its use from 17:00 to 20:00 on nearby normal weekdays. If it used 0.30 kWh per half-hour during the event and 0.34 normally, its score is −0.04.

**When a score counts (is "valid"):**

- At least 80% of the event's half-hours must have readings.
- At least 3 matched days must be usable. A matched day is usable for a household if it has readings for at least 80% of the same half-hours.
- If a half-hour is missing on the event day, it is also left out on the matched days, so both sides always cover the same hours.

**How many matched days were used:**

|                                          | Main run (±14 days)         | Run A (±21 days)         |
| ---------------------------------------- | --------------------------- | ------------------------ |
| High events with at least 3 matched days | 63 of 69                    | 67 of 69                 |
| Matched days per usable event            | min 3, **median 9**, max 15 | min 3, median 13, max 22 |

A household with gaps in its data may use fewer days than the event has. The exact number for each household and event is in the `n_days` column of `event_scores_w14.csv.gz`.

**6 events drop out.** On 7 Jan, 29 Sep, and 8, 15, 21 and 28 Dec there are fewer than 3 normal days within 14 days (almost every day around them had a price signal), so nobody can be scored on them. **63 events remain.**

Of the 384,054 household-event pairs, **87.5% gave a valid score.** Most of the rest belong to the 6 dropped events. About 4% had too many missing readings during the event. Every one of the 63 events has a valid score for at least 1,040 ToU and 4,055 Std households.

### Step 3: One score per household (`05_household_scores.py`)

A household's score is **the average of its valid event scores**, if it has at least 5.

**Why one number per household?** Readings from the same household are not independent: a household that uses a lot at 17:00 also uses a lot at 17:30. If we treated every reading as separate evidence, we would be far too confident. The households are what was sampled, so the test uses one value per household.

|                                | ToU             | Std             |
| ------------------------------ | --------------- | --------------- |
| Households in the data         | 1,123           | 4,443           |
| Dropped: no 2013 data          | 6               | 32              |
| Dropped: no valid High events  | 0               | 6               |
| Dropped: only 1–4 valid events | 3               | 9               |
| **Kept (main analysis)**       | **1,114 (99%)** | **4,396 (99%)** |

The median household in both groups has a valid score on **all 63 events**. The fewest any kept household has is 5 (Std) and 7 (ToU). So each household score is an average over many events, not just a few.

### Step 4: The same thing for the four sensitivity runs

In the main run we made some choices that were reasonable but could have gone another way. Each sensitivity run changes **one** choice and makes the household scores again. If the final answer stays about the same in every run, it doesn't depend on that choice. If it changes, we say so in the report. All five runs are reported, whatever they show.

| Run      | What changes                                                                        | The worry it checks                                                                                                           | ToU   | Std   | Events |
| -------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ----- | ----- | ------ |
| **Main** | the rules above                                                                     | (this is the answer)                                                                                                          | 1,114 | 4,396 | 63     |
| A        | matched days within ±21 instead of ±14                                              | Did the 14-day window drive the result? A wider window keeps more events but compares with days further away in the season.   | 1,114 | 4,398 | 67     |
| B        | the 3 odd-timed event days removed (29 Jan, 9 Feb, 21 Mar; events H014, H020, H044) | Did a few unusual days drive the result?                                                                                      | 1,114 | 4,396 | 60     |
| C        | high night-use homes removed                                                        | The Std group has more of these homes (10.7% vs 6.7% of ToU), and their pattern is very different. Is that behind the result? | 1,039 | 3,921 | 63     |
| D        | only households with at least 300 days of 2013 data                                 | Could households that left the study part-way bias the result?                                                                | 1,047 | 4,140 | 63     |

Run B keeps the same households as the main run (removing 3 events didn't push anyone below 5), but its scores are slightly different.

### Step 5: Checks

- **Unit tests** (`tests/test_score_event.py`): 5 small cases with answers worked out by hand. All pass.
- **Hand check** (`tests/hand_check.py`): one ToU household's score on event H026, recomputed directly from the raw CSV without the matrix. It **matched the pipeline to 6 decimal places.**
- **Counts:** households, readings, Nulls and households with 300+ days all agree with the EDA.

## 4. The results gate

Nothing in this step compares ToU scores with Std scores: no group averages and no differences. That is deliberate. Nobody looks at the effect until `decisions.md`, the threshold T and the simulation are committed, so the result can't influence our choices. `stage3_summary.txt` shows counts only.

## 5. Next steps: who does what, with which files

All scores are in **kWh per half-hour**. To convert a score to a reduction in kW, multiply by 2 and flip the sign (a reduction is a negative score). The threshold is **T = 0.043 kW**.

### Nyo: distribution model and simulation (do this before Lin looks at the effect)

- **Use:** `results/households_index.csv` (pick 200 households with `days_2013 >= 300`, seed 2013); `results/normal_days.csv`; `data/interim/H2013.npy` (rebuild it with `run_p1.py` if you don't have it); `src/pipeline_lib.py`.
- **Do:**
  1. Fit lognormal and gamma models to the non-zero normal-day readings of the 200 households, and compare them with AIC, a KS test and Q-Q plots.
  2. Simulate households with **no real effect** from the better model.
  3. Score the simulated households with `pipeline_lib.score_event()`, the exact function used on the real data, and run the same test as Lin.
  4. Check the false-positive rate is 3.6–6.4% and the interval coverage is 93.6–96.4%, then estimate power.
- **Output:** the simulation results, committed **before** anyone looks at the real ToU vs Std difference.

### Lin: main tests and the decision (after Nyo's simulation is committed)

- **Use:** `results/household_scores_main.csv`, one row per household. Columns: `LCLid`, `group` (ToU or Std), `tariff` (always High), `n_events`, `score`, `normal_use`, `event_use`.
- **Do:**
  1. One-sided Welch t-test, H1: the mean ToU score is lower than the mean Std score (α = 0.05). Mann–Whitney as a check.
  2. 95% bootstrap interval for the difference, resampling households within each group, 10,000 resamples, seed 2013.
  3. Cohen's d.
  4. The difference as % of normal use, using `normal_use`.
  5. Compare with T = 0.043 kW and apply the decision rule:
     - **offer the tariff** if the lower end of the interval is at least 0.043 kW;
     - **don't offer it** if the upper end is below 0.043 kW;
     - otherwise **inconclusive**: recommend a bigger pilot.
- **Output:** numbers into `results.json` (`save_result`), each test into `test_log.csv` (`log_test`).

### Javed: regression (which kinds of events get bigger reductions)

- **Use:** `results/event_effects_main.csv`, one row per High event (63 with an effect; the 6 dropped events have empty values). Columns include `tou_mean`, `std_mean`, `effect` (ToU minus Std), `n_tou`, `n_std`, `evening`, `hours`, `winter`, `low_before`, `month`.
- **Do:** fit `effect ~ evening + hours + winter + low_before` with OLS and HC3 standard errors. Run leave-one-month-out cross-validation against a mean-only baseline. Check Cook's distance and Durbin–Watson.
- **Output:** the coefficient table and the cross-validation result.

### Arpan: sensitivity runs (after Lin's main test)

- **Use:** `results/household_scores_A.csv`, `_B.csv`, `_C.csv`, `_D.csv` (same columns as Lin's file), and `results/exclusions_A.csv` to `_D.csv` for the household counts.
- **Do:** run Lin's exact test and bootstrap on each file. Report all five runs (main + A–D) in one table: reduction in kW, 95% interval, number of households.
- **Note for run C:** it removes 10.7% of Std homes but only 6.7% of ToU homes. Say this when reporting it.

### Sabrina: data card

- **Use:** `results/stage3_summary.txt` (all the counts), `results/exclusions_main.csv` (who was dropped and why), `results/duplicates_check.csv` (105,173 duplicates, all identical) and `results/households_index.csv` (days of data per household).
- **Do:** describe the data, the cleaning rules and the drop-outs, using the numbers in sections 3 and 4 above.

## 6. How to run it again

Put Javed's Stage 2 files (`events.csv`, `matched_days.csv`, `normal_days.csv`, `matched_counts.csv`, `results.json`) in `results/`. Then:

```
python tests/test_score_event.py
python src/run_p1.py --raw "<folder with the 168 CSVs>" --households "<EDA folder>/households.csv"
python tests/hand_check.py --raw "<folder with the 168 CSVs>"
python src/stage3_report.py
```

The matrix step takes 20–40 minutes and needs about 800 MB of disk. It is skipped if `data/interim/H2013.npy` already exists (add `--force` to rebuild). The scoring steps take a few minutes.

## 7. Files

| File                         | What it does                                                                |
| ---------------------------- | --------------------------------------------------------------------------- |
| `src/config.py`              | Paths and rules (must match `docs/decisions.md`). `TARIFFS_USED = ["High"]` |
| `src/pipeline_lib.py`        | Shared functions. `score_event()` is the one definition of a score          |
| `src/03_matrix.py`           | Raw CSVs → matrices, `households_index.csv`, `duplicates_check.csv`         |
| `src/04_event_scores.py`     | Matrix + events → `event_scores_w14.csv.gz` and `_w21`                      |
| `src/05_household_scores.py` | Event scores → `household_scores_*`, `exclusions_*`, `event_effects_*`      |
| `src/run_p1.py`              | Runs 03, 04 and 05 in order                                                 |
| `src/stage3_report.py`       | Counts-only summary → `results/stage3_summary.txt`                          |
| `tests/test_score_event.py`  | Five hand-checkable tests of the scoring rules                              |
| `tests/hand_check.py`        | One score recomputed from the raw CSV                                       |

**Outputs** (all in `results/`): `households_index.csv`, `duplicates_check.csv`, `event_scores_w14.csv.gz`, `event_scores_w21.csv.gz`, `household_scores_{main,A,B,C,D}.csv`, `exclusions_{main,A,B,C,D}.csv`, `event_effects_{main,A,B,C,D}.csv`, `stage3_summary.txt`, `results.json` (`p1_*` keys).
