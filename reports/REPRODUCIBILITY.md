# Reproducibility check

**Status: passed.** A fresh local clone at commit `bcc72c225efa4d626ad24235a2bd0ec1b72ce5bb` ran
`python run_all.py` in a separate clean environment with the pinned packages.
The virtual environment did not inherit system packages. The supplied prepared matrix
and tariff workbook were copied as external inputs, with frozen Stage 4 calibration
already committed. This tests Lin's complete prepared-input route.

| Output | Comparison |
|---|---|
| `results/results.json` | Exact match |
| `results/boot_high.npy` | Exact match |
| `results/boot_low.npy` | Exact match |
| `results/coverage_trials.csv` | Exact match |
| `results/sensitivity_table.csv` | Exact match |
| `results/estimates.csv` | Exact match |
| `results/regression_coefficients.csv` | Exact match |
| `results/regression_cv_predictions.csv` | Exact match |
| `figures/decision.png` | Exact match |
| `figures/assumptions_high.png` | Exact match |
| `figures/assumptions_low.png` | Exact match |
| `figures/model_diagnostics.png` | Exact match |

The result dictionary comparison is byte-for-byte, stronger than checking rounded
report values. Main bootstrap draws and all empirical coverage-trial records are also
checked exactly. Tests are append-only, so execution timestamps and commit labels are
not expected to match. SVG metadata timestamps are not a numerical target.

This does **not** establish a fresh raw-download reproduction of the full team project:
original household CSVs and EDA scripts were not supplied, Nyo's original 4,000 trials
were audited rather than regenerated, and historical preregistration cannot be proved.
The original independent raw-CSV hand check needs those files. The supplied reading
export's arithmetic and raw-writer edge cases have separate automated tests.

Machine-readable evidence: `results/reproducibility.json`. The clone is retained under
`tmp/` for inspection and is excluded from Git. No remote repository was changed.
