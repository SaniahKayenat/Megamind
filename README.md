# Household EDA: Low Carbon London smart-meter data

`profile_households.py` does the exploratory data analysis for our project on dynamic electricity pricing. It reads the half-hourly smart-meter readings, which are too large to open at once (about 10 GB, 167 million rows), in chunks. It saves small summary tables and figures that the proposal and report use.

## Data

| Item       | Details                                                                                                                                                                       |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Dataset    | [SmartMeter Energy Consumption Data in London Households](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d), London Datastore |
| Publisher  | UK Power Networks (Low Carbon London trial)                                                                                                                                   |
| Licence    | CC BY 4.0: free to reuse with credit                                                                                                                                          |
| Files used | `low-carbon-london-data-168-files.zip`: 168 CSVs of about 1 million rows each                                                                                                 |
| Columns    | `LCLid` (household ID), `stdorToU` (Std or ToU), `DateTime`, `KWH/hh (per half hour)`                                                                                         |

The raw data is **not** in this repository. Download and unzip it yourself, and put all the CSVs in one folder.

> **Important:** use either the 168 split files **or** the single combined CSV, never both in the same folder. Otherwise every reading is counted twice. The script warns you if it finds a very large file (over 2 GB) next to the split files, and it skips any CSV that does not have the four columns above.

## Requirements

Tested with Python 3.13 and:

```
pandas==3.0.5
numpy==2.5.3
matplotlib==3.11.2
```

Install them with:

```
pip install pandas==3.0.5 numpy==2.5.3 matplotlib==3.11.2
```

Other recent versions of these libraries should also work.

## How to run

```
python profile_households.py <data folder> <output folder>
```

Example:

```
python profile_households.py "D:/LCL/data" "D:/LCL/eda_results"
```

- `<data folder>` is the folder with the CSVs. You can also give a single CSV file.
- `<output folder>` is where results are saved. It is created if it doesn't exist. If you leave it out, the script uses `profile_out`.
- Put quotes around paths that contain spaces.

The script prints each file name as it reads it. A full run takes roughly 20–40 minutes, depending on your computer. It does not use random numbers, so every run gives the same output.

## What it does

The script only looks at readings from **2012** (before the tariff) and **2013** (the tariff year). For each chunk of data it:

1. Cleans the data: strips spaces from column names, turns the kWh text into numbers (`Null` becomes missing), and reads the timestamps.
2. Counts rows, missing kWh values and duplicate household + time rows.
3. Checks that each household has only one group label (Std or ToU).
4. Records which days and months each household has readings for.
5. Adds up 2012 use for each household, and for each of the 48 half-hours of the day, by group.
6. Builds a histogram of 2013 half-hourly kWh by group and counts zero readings.
7. Counts readings on the 2013 daylight-saving days (see below).

Duplicates and missing values are left out of all sums and averages.

## Outputs

| File                     | What it contains                                                                                                  | Used for                               |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| `summary.txt`            | Key numbers: rows, missing values, duplicates, households per group, coverage, zeros, 2012 daily use, clock check | Data preparation table (section 2)     |
| `households.csv`         | One row per household: group, readings and days in 2012 and 2013, average daily kWh in 2012                       | Sample sizes; group comparison         |
| `coverage_by_month.csv`  | Households with data each month, by group                                                                         | Sample over time                       |
| `profile_2012.csv`       | Average kWh in each half-hour of the day in 2012, by group                                                        | 2012 load-curve chart                  |
| `kwh_hist_2013.csv`      | Histogram of 2013 half-hourly kWh (log-spaced bins), by group                                                     | Distribution of readings (criterion 3) |
| `dst_check.csv`          | Readings per household on the daylight-saving days                                                                | Clock check                            |
| `fig_coverage.png`       | Households reporting each month, ToU vs Std                                                                       | Appendix                               |
| `fig_kwh_hist.png`       | Distribution of half-hourly use in 2013 (log scale)                                                               | Appendix                               |
| `fig_profile_2012.png`   | Average daily load curve in 2012, ToU vs Std                                                                      | Main text                              |
| `fig_daily_kwh_2012.png` | Household daily use in 2012, ToU vs Std (box plot)                                                                | Appendix                               |

## The clock check

The UK moves its clocks forward an hour in spring (31 March 2013) and back in autumn (27 October 2013). A meter that followed the change would record 46 half-hours on the first day and 50 on the second, instead of the usual 48.

The script counts readings per household on those days. In our run, 99.7% of households had the normal 48. So the meters use a fixed clock (GMT) all year, as does the tariff file, and readings match prices by timestamp without adjustment. Times in our results are therefore GMT. In summer, local time is one hour later.

## Results of our run

| Measure                        | ToU   | Std   |
| ------------------------------ | ----- | ----- |
| Households                     | 1,123 | 4,443 |
| With any 2013 data             | 1,117 | 4,411 |
| With ≥300 days of 2013 data    | 1,047 | 4,140 |
| Median daily use in 2012 (kWh) | 8.14  | 8.43  |
| Zero readings in 2013          | 1.18% | 1.27% |

Other figures: 60,410,060 rows in 2012 and 93,087,837 in 2013; 5,548 missing kWh values in 2012 and 12 in 2013; 105,173 duplicate rows (0.07%); no household changes group.
