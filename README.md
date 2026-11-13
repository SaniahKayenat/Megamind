# Do Price Signals Cut Household Demand? (Team Megamind)

Modern Applied Statistics for Data Science, Dr. Sein Minn, AIT.
Team: Saniah Kayenat Chowdhury, Sabrina Afrin, Ahmad Jawid Fedayi, Arpan Ojha, Lin Htet Aung and Nyo Lae Hnin.

**Question.** When a household on a dynamic tariff gets a High-price signal, how much less electricity does it use during those hours than a similar household on a flat tariff?

**Decision.** A utility product manager has to decide whether to offer the tariff to all residential customers. The rule is to offer it only if the reduction is at least **T = 0.043 kW per household**.

**Answer in one line.** Tariff households cut **0.029 kW** per household during High events (95% CI 0.026 to 0.033). That is below T, so the decision is **do not offer**.

This folder is the combined team project: every stage's code, results, figures and write-up in one repository.

## Read in this order

| Part | What it covers | Where |
|---|---|---|
| **1. Before you run** | What the project is, who did each stage, what you need, installation | this file, Part 1 |
| **2. Run** | One command, what it runs, run time, seeds | this file, Part 2 |
| **3. After the run** | What every result means, stage by stage, with figures | **[RESULTS.md](RESULTS.md)** |

---

# Part 1: Before you run

## Who did each stage

| Stage | Owner | Code | Write-up |
|---|---|---|---|
| 0 Decisions, threshold T, rules | Sabrina | — (rules are coded in `src/config.py`) | `docs/decisions.md`, `README_P0_P7.md` |
| 1 & 3 Data pipeline: matrix, event and household scores | Saniah | `src/03_matrix.py`, `04_event_scores.py`, `05_household_scores.py`, `pipeline_lib.py` | `README_P1.md` |
| 2 Events and matched days | Ahmad Jawid (Javed) | `src/01_events.py`, `02_matched_days.py`, `stage2_events_matched_days.ipynb` | `README_P1.md` §2 |
| 4 Distribution fit and simulation | Nyo | `src/06_distribution.py`, `07_simulation.py`, `tests/test_stage4.py` | `README_P4.md` |
| 5a Estimates, intervals, coverage, decision | Lin | `src/08_estimates.py`, `inference.py` | `reports/REPORT_SECTIONS.md`, `reports/LIN_RESULTS.md` |
| 5b Hypothesis tests and sensitivity table (official H1) | Arpan | `src/09_tests.py` | `README_P5.md`, `docs/stage5_arpan/` |
| 6 Regression: which events get bigger cuts (official) | Ahmad Jawid | `src/10_model.py`, `tests/test_10_model.py` | `README_P6.md` |
| 7 Reproducibility: run-all, requirements, seeds, data card, README | Sabrina (Lin: fresh-clone test) | `run_all.py`, `requirements*.txt` | `README_P0_P7.md`, `DATA_CARD.md`, this README |
| Report text, gate | Lin | `src/11_writeup.py`, `src/check_gate.py` | `reports/` |
| Exploration (EDA) | Saniah | `eda/profile_households.py`, `eda/make_figures.py` | `eda/README_EDA.md` |

**Supporting scripts by Lin.** `src/09b_tests_high_low.py` runs the tests for High and Low events. `src/10b_model_supporting.py` is a second fit of the same regression. Their numbers match the owners' scripts: Arpan's H1 results are identical to full precision, and the regression coefficients are equal. Their outputs carry `_high_low` or `_supporting` in the file name, so no file is overwritten.

## What you need

**Python 3.12** (tested with 3.12.14). Package versions are pinned in `requirements.txt` (the six main packages) and `requirements-lock.txt` (every package, for an exact copy).

1. **Install Python and the packages:**
   ```bash
   python3.12 -m venv env
   source env/bin/activate            # Windows: env\Scripts\activate
   python -m pip install -r requirements-lock.txt
   ```
2. **Put the data in place.** Large files are not in Git.
   - `data/raw/Tariffs.xlsx` is already included.
   - The 2013 matrix `data/interim/H2013.npy` (390 MB) can come from either of two places:
     - copy Saniah's file into `data/interim/`; or
     - download `low-carbon-london-data-168-files.zip` from the [London Datastore](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d), unzip the 168 CSVs into `data/raw/`, and use `--from-raw` below.

---

# Part 2: Run the project

From the `Megamind` folder, run everything with one command:

```bash
python run_all.py              # with H2013.npy: a few minutes (measured: under 2 minutes on 2 cores)
python run_all.py --from-raw   # from the 168 CSVs: also builds the matrix (the guideline allows up to 2-3 hours)
python -m pytest -q            # all automated tests
```

`run_all.py` stops at the first error. It runs these steps in order:

1. results gate check
2. events and matched days
3. matrix (`--from-raw` only)
4. event and household scores
5. estimates
6. tests
7. regression
8. write-up
9. EDA figures

**Stage 4 is not rerun each time.** The simulation takes about an hour, so `run_all.py` reuses its committed results and the gate checks them. To rebuild it:

```bash
python src/06_distribution.py      # about 1 minute
python src/07_simulation.py        # about 1 hour on 2 cores
```

**EDA.** `eda/make_figures.py` runs inside `run_all.py`. The slow first EDA step reads the 10 GB of CSVs, so it is run separately, once:

```bash
python eda/profile_households.py data/raw eda
```

It takes 20-40 minutes. See `eda/README_EDA.md`.

To check that a fresh copy reproduces the outputs exactly, run `python scripts/verify_reproduction.py`.

## Random seeds

Every random step uses **seed 2013**. Steps that run trials in parallel give each trial its own child seed from `SeedSequence(2013)`, so the results are the same whatever the number of cores.

| Random step | Script | Seed |
|---|---|---|
| 200-household sample | `src/06_distribution.py` | `default_rng(2013)` |
| 500-reading draw per household | `src/06_distribution.py` | same generator |
| KS goodness-of-fit simulations (199 per household and model) | `src/06_distribution.py` | same generator |
| Simulation study (4 × 1,000 trials) | `src/07_simulation.py` | `SeedSequence(2013)` |
| Bootstrap intervals (10,000 resamples) | `src/08_estimates.py`, `src/inference.py`, `src/09_tests.py` | `default_rng(2013)` |
| Resampling coverage check (1,000 trials × 2,000 resamples) | `src/08_estimates.py` | `SeedSequence(2013)` |
| Leave-one-month-out cross-validation | `src/10_model.py` | none (no random step) |

---

# Part 3: After the run

The run writes four kinds of output:

| Output | Where | What it is |
|---|---|---|
| Numbers | `results/results.json` | Every number in the report, written by code with `save_result()`. Nobody types a number by hand |
| Tables | `results/*.csv` | Estimates, sensitivity table, regression tables, simulation trials, exclusions |
| Test record | `results/test_log.csv` | Every test ever run, including failed and exploratory ones. Append-only |
| Figures | `figures/` | See the table below |

**[RESULTS.md](RESULTS.md) explains every result, stage by stage.** Each stage owner's README (`README_P0_P7.md`, `README_P1.md`, `README_P4.md`, `README_P5.md`, `README_P6.md`) has the full detail.

## Which script makes which figure

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

---

## Folder map

| Folder | What is in it |
|---|---|
| `src/` | every script, numbered in run order |
| `tests/` | automated checks (Stages 3, 4, 5 and 6) |
| `results/` | all tables, `results.json` (every reported number) and `test_log.csv` (every test ever run, append-only) |
| `figures/` | all figures for the report and appendix |
| `docs/` | `decisions.md` (the rules, fixed before scoring, with dated changes at the bottom), statistics and program guides, provenance, and course documents in `docs/course/` |
| `reports/` | report sections, speaker notes and presentation text (Lin), reproducibility record |
| `eda/` | exploration outputs |
| `slides/` | Lin's slide content |
| `submissions/` | earlier copies of `results.json` kept for provenance |
| `DATA_CARD.md`, `BLUEPRINT.md` | data card and project blueprint |

---

## Open items for the team

1. **Decide the scope.** Saniah, Arpan and Ahmad Jawid worked on High events only (H1). Lin restored High and Low (H1 and H2), as in `decisions.md` §7. Both sets of results are here. Agree which one the report uses and add a dated line to `docs/decisions.md`.
2. **Rerun once in the pinned environment.** The two regression scripts need statsmodels, which wasn't available when the project was combined. Their outputs are the owners' submitted runs. Run `python run_all.py`, then `python scripts/verify_reproduction.py`, and commit the result. The `results.json` hash in `docs/expected_output_hashes.json` is the combined file and has not yet been confirmed by a fresh full run.
3. **Push to GitHub** (`SaniahKayenat/Megamind`). The local branch is `team-integrated`. Keep the hidden `.git` folder: the results gate checks an earlier commit.
4. **Raw-data check.** The original 168 household CSVs were not in any submission. With them in `data/raw/`, `python run_all.py --from-raw` rebuilds the matrix from scratch.
5. **Report and slides.** Each stage README has ready-to-use text, and `reports/` holds Lin's sections.

## Data credit

UK Power Networks, *SmartMeter Energy Consumption Data in London Households*, London Datastore, CC BY 4.0. See `DATA_CARD.md`.
