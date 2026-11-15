# Megamind — Do Price Signals Cut Household Demand?

**Modern Applied Statistics for Data Science | Asian Institute of Technology | November 2026**

Team Megamind analyses electricity consumption from the Low Carbon London smart-meter dataset to study household responses to dynamic electricity prices. The repository combines data preparation, event matching, statistical analysis, simulation, regression, and reproducibility checks into one pipeline.

## 1. Project Structure

```text
Megamind/
│
├── run_all.py                  # Main pipeline
├── requirements.txt
├── requirements-lock.txt      # Pinned dependencies
├── requirements-dev.txt       # Testing dependencies
├── README.md
├── DATA_CARD.md               # Dataset documentation
│
├── src/                       # Analysis scripts
│   ├── config.py              # Configuration and paths
│   ├── pipeline_lib.py        # Shared functions
│   ├── check_gate.py          # Results gate
│   ├── 01_events.py           # Identify price events
│   ├── 02_matched_days.py     # Match normal days
│   ├── 03_matrix.py           # Build data matrices
│   ├── 04_event_scores.py     # Event-level scoring
│   ├── 05_household_scores.py # Household-level scoring
│   ├── 06_distribution.py     # Distribution fitting
│   ├── 07_simulation.py       # Simulation study
│   ├── 08_estimates.py        # Effect estimation
│   ├── 09_tests.py            # Hypothesis tests
│   ├── 09b_tests_high_low.py  # Supporting tests
│   ├── 10_model.py            # Regression analysis
│   ├── 10b_model_supporting.py
│   └── 11_writeup.py          # Generate written outputs
│
├── data/
│   ├── raw/                   # Tariffs.xlsx and raw CSVs
│   └── interim/               # Prepared matrices
│
├── results/                   # Numerical results and tables
├── figures/                   # Generated figures
├── eda/                       # Exploratory data analysis
├── tests/                     # Automated tests
├── scripts/                   # Reproducibility utilities
├── docs/                      # Decisions
```

## 2. Requirements

- Python 3.12 (tested with Python 3.12.14)
- Git
- Dependencies listed in `requirements-lock.txt`
- Prepared electricity-consumption matrix or original raw CSVs

The project uses `portalocker` for cross-platform file locking.

## 3. Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/SaniahKayenat/Megamind.git
cd Megamind
```

Keep the Git history (`.git` folder), as it is used by the project's results-gate checks.

### Step 2 — Create a virtual environment

**Windows (Command Prompt)**

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
python -m pip install -r requirements-lock.txt
python -m pip install -r requirements-dev.txt
```

The dependency files should include `portalocker` and `pytest`.

## 4. Data Preparation

Large datasets and intermediate matrices are stored separately from the GitHub repository.

### Option A — Prepared matrix (recommended)

Place prepared matrix in:

```text
data/interim/H2013.npy
```

The H2013.npy file can be found at https://drive.google.com/file/d/13Z8SewfE4tz8j12j4mrMGSpzQ9a19T57/view?usp=sharing
Make sure the tariff schedule exists at:

```text
data/raw/Tariffs.xlsx
```

### Option B — Original raw data

Download the [Low Carbon London smart-meter dataset](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d).

Extract the 168 household CSV files into:

```text
data/raw/
```

Keep `Tariffs.xlsx` in the same folder.

## 5. Running the Project

Run the following commands from the repository root (`Megamind`).

### Run using the prepared matrix

```bash
python run_all.py
```

This executes the integrated analysis using `H2013.npy`.

### Run from the original CSV files

```bash
python run_all.py --from-raw
```

This rebuilds the matrices before executing the remaining analysis.

### Specify the number of workers

```bash
python run_all.py --workers 2
```

The default number of workers is 2.

### Pipeline execution order

`run_all.py` executes the following steps:

1. Verify the results gate.
2. Identify price events and matched normal days.
3. Build matrices when `--from-raw` is specified.
4. Calculate event scores for 14-day and 21-day windows.
5. Calculate household scores for the main analysis and sensitivity runs A–D.
6. Estimate effects and confidence intervals.
7. Perform hypothesis tests and supporting analyses.
8. Run regression models.
9. Generate reports and EDA figures.

The pipeline stops automatically if a step fails.

## 5. Testing and Reproducibility

### Run automated tests

```bash
python -m pytest -q
```

Random procedures use seed **2013** for reproducibility.

## 6. Output Files

| Location                         | Description                          |
| -------------------------------- | ------------------------------------ |
| `results/results.json`           | Main numerical results               |
| `results/test_log.csv`           | Statistical test records             |
| `results/household_scores_*.csv` | Household-level scores               |
| `results/event_effects_*.csv`    | Event-level effects                  |
| `results/sensitivity_table.csv`  | Sensitivity analysis                 |
| `results/simulation_trials.csv`  | Simulation trials                    |
| `results/regression_*.csv`       | Regression outputs                   |
| `figures/`                       | Statistical plots and figures        |
| `reports/START_HERE.md`          | Guide to generated reporting outputs |
| `RESULTS.md`                     | Detailed results and interpretation  |
| `docs/decisions.md`              | Study decisions and analysis rules   |
| `docs/PROVENANCE.md`             | Source and reproducibility records   |

## 7. Data Credits

**Dataset:** UK Power Networks, _SmartMeter Energy Consumption Data in London Households_, London Datastore (CC BY 4.0).
