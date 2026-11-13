# Do Price Signals Cut Household Demand? — Lin's completed work

This project estimates electricity-demand changes during 2013 Low Carbon London price
events. Lin's estimates, uncertainty, threshold decision, report sections and presentation
material are complete, with supporting tests, sensitivity comparisons and event modelling.

Start with [reports/START_HERE.md](reports/START_HERE.md). Read
[docs/PROGRAM_GUIDE.md](docs/PROGRAM_GUIDE.md) for every program's inputs, actions and
outputs, and [docs/STATISTICS_EXPLAINED.md](docs/STATISTICS_EXPLAINED.md) for the reasoning.
Original submissions remain untouched in the parent folder.

## Run the prepared-input analysis

Tested with Python **3.12.14**. The six principal package versions are pinned in
`requirements.txt`; `requirements-lock.txt` also records the tested transitive versions.
Use the lock file when reproducing this environment exactly.

```bash
python3.12 -m venv env
source env/bin/activate
python -m pip install -r requirements-lock.txt
python run_all.py
```

Place the supplied `H2013.npy` under `data/interim/` and `Tariffs.xlsx` under
`data/raw/` first. They already exist in this working folder. The matrix came from
Saniah's ZIP and the workbook from Javed's. They are deliberately excluded from Git.
The prepared route rebuilds calendar, scores, estimates, coverage checks, tests,
sensitivity comparisons, model and writing. It reuses **committed Nyo Stage 4 evidence**.
Allow several minutes, mainly for scoring and the nested coverage exercise. The runner
stops at the first error. Use `--workers 1` to reduce CPU use.

## What this run does not claim

The original 168 household CSVs, earlier EDA scripts and historical Git evidence were not
supplied. Prepared-input reproduction is therefore not a fresh raw-download reproduction
of the entire team's project. Nyo's submitted 4,000 trials are audited, not silently
regenerated on every run. See [docs/PROVENANCE.md](docs/PROVENANCE.md).

With original household CSVs added to `data/raw/`, `python run_all.py --from-raw` rebuilds
the matrices first. It still uses the frozen calibration. The continuation repairs
two inherited matrix-writer issues: a Null preceding a valid duplicate now retains
the valid reading, and raw row counters now precede deduplication. Synthetic tests
exercise these edge cases. All supplied duplicates were reported identical, but that
assertion has not been independently rechecked from raw files here. Do not describe
the raw mode as verified until original CSVs are available and its checks are completed.

Nyo's optional standalone reconstruction commands are:

```bash
python src/06_distribution.py
python src/07_simulation.py --workers 2
```

These are expensive and can differ under newer library versions from the submitted
rounded tables. Use a separate checkout. If results change, preserve both runs, log
the change and establish a new committed calibration checkpoint before real inference.
The gate intentionally rejects changed calibration evidence in this continuation.

## Reproducibility and review

`reports/REPRODUCIBILITY.md` records the actual clean-environment, fresh-local-clone
check and its limits. `results/test_log.csv` is append-only. Imported tests identify
their import time explicitly; original execution times are unknown. Rerun timestamps
and commit identifiers are not numerical reproducibility targets. The target is exact
`results/results.json` equality, with bootstrap/coverage files checked separately.

Before sharing with the team, fetch or clone this repository's `lin-complete` branch
rather than copying scripts alone: `check_gate.py` needs the pre-analysis Git object.
No changes were pushed to the team's remote. Have another teammate review the branch.

## Tests and individual steps

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python src/08_estimates.py
python src/09_tests.py
python src/10_model.py
python src/11_writeup.py
```

The original `tests/hand_check.py` requires raw household CSVs. Its supplied reading
export is separately checked without claiming a new raw extraction.

## Seeds and units

Every random root is **2013**: household sampling, reading sampling, KS bootstrap,
simulation, inference bootstrap and empirical coverage. Independent SeedSequence child
streams make parallel coverage/simulation trials reproducible regardless of scheduling.
Cross-validation has no random step. Bootstrap batching is fixed for exact reproduction.

Files store kWh per half-hour. Signed change in kW is `2*Delta`; positive High reduction
is `-2*Delta`. `mw_50k_high` is a signed change; `reduction_high_mw_50k` is the positive
High reduction. The report uses unambiguous structured `estimates.High` values. Keep
effect and reduction interval endpoints distinct. GMT is fixed throughout the data.

## Output map

- `results/results.json`: source of reported numbers, including full-precision findings.
- `results/estimates.csv`, `coverage_trials.csv`, `sensitivity_table.csv`: reviewable tables.
- `results/boot_high.npy`, `boot_low.npy`: all main bootstrap differences for Arpan.
- `figures/decision.png` and `.svg`: High reduction against the economic thresholds.
- `figures/assumptions_*.png`: group Q-Q and bootstrap distributions.
- `figures/model_diagnostics.png`: residuals, Q-Q and Cook's distance.
- `reports/REPORT_SECTIONS.md`: Lin's estimates section and joint conclusion draft.
- `reports/SPEAKER_NOTES.md`: Lin's three slide contributions and Q&A.
- `reports/LIN_RESULTS.md`: detailed interpretation and all sensitivity results.

The EDA scripts listed in the blueprint were not supplied. Their earlier outputs and
claims are inherited context, not independently reconstructed findings in this handoff.

## Data credit

UK Power Networks, *SmartMeter Energy Consumption Data in London Households*, London
Datastore, CC BY 4.0 according to the supplied project specification. See `DATA_CARD.md`.
