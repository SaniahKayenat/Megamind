# Stage 5: Hypothesis tests (Arpan)

H1 only (High-price events), following guideline section 13. Everything in this folder is
Arpan's Stage 5 work and its outputs.

## Result in one paragraph

During High events, tariff (ToU) households used 0.0293 kW less per household than flat-rate
(Std) households (95% CI 0.0256 to 0.0332 kW; 6.2% of normal use). One-sided Welch t = -14.99,
df = 1,372, p = 2.0e-47; Mann-Whitney p = 1.0e-68 (a ToU home scores lower than a Std home in
67% of pairs); Cohen's d = -0.64 (medium). SDs 0.0309 vs 0.0205 (ratio 1.50) justify Welch.
Household scores are heavy-tailed, but the bootstrap distribution of the difference is
bell-shaped (skew -0.08). All four sensitivity runs give 0.028-0.030 kW, every interval is
below T = 0.043 kW, and Welch, Mann-Whitney and the bootstrap interval agree in every run:
decision "do not offer" in all five. Run C removes 10.7% of Std homes but only 6.7% of ToU homes.

## What's here

| Path | What it is |
|---|---|
| `src/09_tests.py` | The script: assumption checks, H1 tests, sensitivity table, agreement check, logging |
| `figures/qq_household_scores_high.png` | Q-Q plots of ToU and Std household scores |
| `figures/bootstrap_hist_high.png` | Histogram of Lin's 10,000 bootstrap differences with a normal curve |
| `results/sensitivity_table.csv` | One row per run (main, A-D), every number at full precision |
| `results/results.json` | Keys `p5_assumptions_high`, `p5_h1_main`, `p5_sensitivity_table`, `p5_agreement_check` |
| `results/test_log.csv` | The 10 logged tests (Welch and Mann-Whitney for each run), person "Arpan" |
| `results/tests_summary.txt` | Plain-text summary |
| `docs/Stage 5 Hypothesis Tests - Arpan's Part Explained.pdf` | Full explanation: what, how, why, results, meaning, verification, limitations, Q&A |
| `docs/report_section5_and_slide8.md` | Draft text for report section 5 and the slide 8 script, ready to paste |

## For the team

- **Merge, don't overwrite:** add the four `p5_*` keys to the team `results.json` and the 10 rows
  to the team `test_log.csv`.
- **Inputs:** the script reads Lin's repo (`Lin_Project`): `src/config.py`, `pipeline_lib.py`,
  `inference.py` (for `group_scores`, `log_test`, `save_result`, `boot_diff`, `decision`) and
  `results/household_scores_{main,A,B,C,D}.csv` and `results/boot_high.npy`. It never changes them.
- **Scope:** Lin's repo also contains a supporting `09_tests.py` (11 Nov) that tested Low events
  (H2) as well. Its H1 numbers are identical to these. This version is High-only, as agreed on 10 Nov.
- **Verification:** numbers match Lin's supporting run exactly, and an independent re-coding of
  every formula (without the shared code) matches to 13 digits.

## How to run

Python 3.11+ with `Lin_Project/requirements-lock.txt` installed. From this folder:

```
python src/09_tests.py --lin "<path to Lin_Project>" --no-log   # check, nothing logged
python src/09_tests.py --lin "<path to Lin_Project>"            # logged run
```

Without `--lin` it looks for `Lin_Project` next to this folder or inside a
`3_Integrated_Repo_Lin/` folder beside it. Takes a few seconds; outputs go into this folder only.

## Run history

12 Nov 2026: one `--no-log` check run, then the final logged run (the 10 rows in the log).
A second `--no-log` run after a folder move gave byte-identical results. The independent
re-computation was verification only, not a new analysis.
