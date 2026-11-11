# How every program fits together

Read this with `docs/STATISTICS_EXPLAINED.md`. Programs use paths from config and
stop on invalid inputs. The original ZIPs are unchanged. Version history records
integration edits, and the dated decisions explain analysis choices.

| Program | Reads | Does, and why | Writes |
|---|---|---|---|
| `config.py` | No data | Centralises paths, coverage rules, seeds and thresholds so scripts agree | Constants imported by other programs |
| `pipeline_lib.py` | Household CSV chunks or score tables | Cleans readings; defines the one event score; validates group inputs; saves numbers and appends tests | Reusable functions, `results.json`, `test_log.csv` |
| `check_gate.py` | Git checkpoint, distribution fits, simulation trials | Confirms committed calibration evidence passes the planned checks before continuation effects are calculated | Gate audit and its result dictionary |
| `01_events.py` | `Tariffs.xlsx` | Finds uninterrupted non-Normal price runs and all-Normal days, with the original event identifiers | `events.csv`, `normal_days.csv` |
| `02_matched_days.py` | Events and normal days | Finds same-type comparison dates within 21 days, requiring every date touched to be Normal | Matched shifts and counts |
| `03_matrix.py` | Raw household CSVs | Creates a household-by-time matrix and records cleaning/coverage facts | 2012/2013 matrices, index and cleaning summary |
| `04_event_scores.py` | 2013 matrix, index, events and shifts | Applies the shared scoring function at both matching windows for High and Low | Compressed household-event score tables |
| `05_household_scores.py` | Event scores, index, event attributes | Gives each eligible household one score, counts exclusions, and aggregates event effects | Main and A–D household/exclusion/event tables |
| `06_distribution.py` | Matrix and Normal dates | Fits lognormal and gamma models to 500 nonzero observations from each of 200 eligible sampled homes | Fit table, Q-Q plots, model summaries |
| `07_simulation.py` | Fits, calendar, group membership and missingness only | Simulates known High-event effects and applies the real scoring/test method | Four scenarios of 1,000 trials each |
| `import_test_log.py` | Supplied fit and simulation tables | Records inherited tests without inventing original run times | Appended test-log rows labelled as imports |
| `inference.py` | Arrays of household scores | Defines within-group bootstrap, unit conversion, threshold decisions, Welch/MW and Cohen's d in one place | Values returned to callers |
| `08_estimates.py` | Main household scores | Computes both effects, 10,000-draw intervals, High decisions and 1,000 nested coverage trials per tariff | Estimates, bootstrap arrays, coverage trials, decision figure |
| `09_tests.py` | Main and A–D scores, bootstrap arrays | Shows assumptions and runs every planned comparison without selecting significant outcomes | Assumption figures, sensitivity table, test log |
| `10_model.py` | High event effects | Fits the planned HC3 model, checks overlap/influence, and validates predictions on unseen months | Coefficients, CV predictions, diagnostics |
| `11_writeup.py` | Saved result dictionary and exclusion counts | Generates Lin's writing and speaker script from saved results rather than hand-entered numbers | Start guide, report sections, speaking notes, handoff |
| `run_all.py` | Available prepared inputs or raw CSVs | Runs dependencies in order and stops on the first failure | All Lin outputs and supporting analyses |
| `scripts/verify_reproduction.py` | Committed project, external prepared inputs, clean Python environment | Clones locally, reruns the prepared analysis and compares exact output hashes | Reproduction receipt and readable report |
| `run_p1.py` | Raw inputs or existing matrices | Original Saniah convenience runner for Stages 1/3 | Pipeline outputs |
| `stage3_report.py` | Pipeline tables | Original counts-only High handoff summary, retained for provenance | Original stage summary |
| `tests/hand_check.py` | Original raw CSVs | Checks a score independently of the matrix | Console comparison; requires absent raw data |
| `tests/test_score_event.py` | Tiny invented arrays | Checks missingness, coverage and matched-day rules against hand answers | Test results |
| `tests/test_stage4.py` | Tiny simulated data | Checks compact storage equivalence and bootstrap-KS calibration | Test results |
| `tests/test_inference.py` | Tiny invented household samples | Checks signs, units, interval reversal, boundary decisions, reproducible resampling and one-sided direction | Test results |
| `tests/test_matrix_insert.py` | Tiny invented meter records | Checks first-valid duplicates and Null duplicates within and across chunks | Test results |
| `tests/test_supplied_hand_check.py` | Supplied reading export | Independently checks its arithmetic against the rebuilt event table, allowing float32 rounding | Test results |

## Each action in the prepared run

1. Check inputs. Missing files must stop the run, rather than produce partial results.
2. Check the gate. The inherited simulation and fixed decisions are in a local checkpoint.
3. Rebuild the price calendar and comparison dates from the workbook.
4. Score the supplied matrix twice: ±14 for the main analysis and ±21 for sensitivity A.
5. Aggregate main and A–D tables, retaining every specified exclusion count.
6. Import historical tests if there is no log yet, making the provenance limitation explicit.
7. Estimate changes and intervals, then evaluate the predetermined High threshold.
8. Validate interval behaviour through the additional empirical resampling exercise.
9. Run hypothesis tests and sensitivity comparisons; append every test.
10. Fit the prespecified event model and compare it with the held-out-month baseline.
11. Generate report text and speaker notes from `results.json`.

No program sends a message, publishes results or uploads household data. Git commits
are local review checkpoints. Large matrices and raw readings stay out of Git.
