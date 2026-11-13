# Do Price Signals Cut Household Demand? (Team Megamind)

Modern Applied Statistics for Data Science, Dr. Sein Minn, AIT.
Team: Saniah Kayenat Chowdhury, Sabrina Afrin, Ahmad Jawid Fedayi, Arpan Ojha, Lin Htet Aung and Nyo Lae Hnin.

**Question.** When a household on a dynamic tariff gets a High-price signal, how much less electricity does it use during those hours than a similar household on a flat tariff?

**Decision.** A utility product manager has to decide whether to offer the tariff to all residential customers. The rule is to offer it only if the reduction is at least **T = 0.043 kW per household**.

This folder is the combined team project: every stage's code, results, figures and write-up in one repository.

---

## Main result

| | Result |
|---|---|
| **H1, High events** (main) | ToU households used **0.029 kW less** per household (95% CI 0.026 to 0.033 kW; 6.2% of normal use). One-sided Welch p = 2.0 × 10⁻⁴⁷, Mann–Whitney p = 1.0 × 10⁻⁶⁸, Cohen's d = −0.64. |
| **Decision against T = 0.043 kW** | The whole interval is below T, so **do not offer** the tariff. All four sensitivity runs (A–D) give 0.028–0.030 kW and the same decision. |
| **Method check** (Stage 4 simulation) | All 4 scenarios pass: 5.9% false positives, 94.7% coverage, 100% power, and both stress tests pass. |
| **When signals work best** (Stage 6) | Winter events get about 0.015 kW more cut per household (p = 0.003). Evening start, length and a Low period just before add little. The model beats the baseline only slightly in cross-validation (RMSE 0.0200 vs 0.0203 kW). |
| **H2, Low events** (for information) | ToU households used 0.033 kW **more** during Low events (95% CI 0.029 to 0.037 kW). Per `decisions.md` §8, H2 has no threshold; see the open question on scope below. |

Every number comes from `results/results.json`.

---

## Who did what

| Stage | Owner | Code | Write-up |
|---|---|---|---|
| 0 Decisions, threshold T, rules | Sabrina | — (rules are coded in `src/config.py`) | `docs/decisions.md` |
| 1 & 3 Data pipeline: matrix, event and household scores | Saniah | `src/03_matrix.py`, `04_event_scores.py`, `05_household_scores.py`, `pipeline_lib.py` | `README_P1.md` |
| 2 Events and matched days | Ahmad Jawid (Javed) | `src/01_events.py`, `02_matched_days.py`, `stage2_events_matched_days.ipynb` | `README_P1.md` §2 |
| 4 Distribution fit and simulation | Nyo | `src/06_distribution.py`, `07_simulation.py`, `tests/test_stage4.py` | `README_P4.md` |
| 5a Estimates, intervals, coverage, decision | Lin | `src/08_estimates.py`, `inference.py` | `reports/REPORT_SECTIONS.md`, `reports/LIN_RESULTS.md` |
| 5b Hypothesis tests and sensitivity table (official H1) | Arpan | `src/09_tests.py` | `README_P5.md`, `docs/stage5_arpan/` |
| 6 Regression: which events get bigger cuts (official) | Ahmad Jawid | `src/10_model.py`, `tests/test_10_model.py` | `README_P6.md` |
| Report text, run-all, gate | Lin | `src/11_writeup.py`, `src/check_gate.py`, `run_all.py` | `reports/` |
| Exploration (EDA) | team | outputs in `eda/` | `eda/summary.txt` |

**Supporting scripts by Lin.** `src/09b_tests_high_low.py` runs the tests for High and Low events. `src/10b_model_supporting.py` is a second fit of the same regression. Their numbers match the owners' scripts: Arpan's H1 results are identical to full precision, and the regression coefficients are equal. Their outputs carry `_high_low` or `_supporting` in the file name, so no file is overwritten.

---

## How to run

1. Install Python 3.12 and the pinned packages:
   ```bash
   python3.12 -m venv env
   source env/bin/activate            # Windows: env\Scripts\activate
   python -m pip install -r requirements-lock.txt
   ```
2. Put the data in place. It is not in Git because it is large.
   - `data/raw/Tariffs.xlsx` is already included.
   - `data/interim/H2013.npy` (390 MB) is not included. Copy it from Saniah's `Data_pipeline` zip, at `stage1_3_saniah/data/interim/H2013.npy`.
3. Run everything with one command:
   ```bash
   python run_all.py              # several minutes; use --workers 1 on a slow laptop
   python -m pytest -q            # all tests
   ```

`run_all.py` stops at the first error. It runs these steps in order:

1. results gate check
2. Stage 2 events
3. Stage 3 scores
4. Lin's estimates
5. Arpan's tests, then Lin's High+Low tests
6. Ahmad Jawid's model, then Lin's supporting model
7. write-up

Stage 4 is not rerun each time, because the 4,000-trial simulation takes about an hour. Its committed results are checked by the gate instead. To rebuild it:

```bash
python src/06_distribution.py
python src/07_simulation.py
```

All random steps use **seed 2013**. Results are in kWh per half-hour; × 2 = kW per household.

To check that a clean copy reproduces the outputs exactly, run `python scripts/verify_reproduction.py`.

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
