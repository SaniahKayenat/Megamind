# Data card

## Source and licence

| | |
|---|---|
| Dataset | *SmartMeter Energy Consumption Data in London Households*, [London Datastore](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d) |
| Publisher | UK Power Networks, Low Carbon London trial (analysis: Schofield 2015, Imperial College London) |
| Licence | **CC BY 4.0.** Free to reuse with credit. Credit: "Contains data from UK Power Networks' Low Carbon London project, London Datastore, CC BY 4.0." |
| Period used | 2013 for all analysis. 2012 only to describe the groups before the tariff and to define high night-use homes. |

## What each raw file holds

| File | Contents |
|---|---|
| `low-carbon-london-data-168-files.zip` | 168 CSVs, about 1 million rows each (about 10 GB in total). Four columns: `LCLid` (household code, e.g. `MAC000145`), `stdorToU` (`Std` = flat tariff, `ToU` = dynamic tariff), `DateTime` (half-hour start, fixed GMT), `KWH/hh (per half hour)` (text; `Null` = missing) |
| `Tariffs.xlsx` | The 2013 price for every half-hour: High (67.20p/kWh), Low (3.99p) or Normal (11.76p). The flat tariff is 14.23p. 17,520 half-hours: 788 High, 1,660 Low, 15,072 Normal |

Large files are not in Git. `Tariffs.xlsx` is in `data/raw/`. The 2013 matrix `data/interim/H2013.npy` is built by `src/03_matrix.py` from the CSVs (Saniah's copy can be used instead).

## Personal data

- **Identifiers:** households are identified only by the publisher's pseudonymous code (`LCLid`). The data has no names, addresses or postcodes.
- **Nothing removed:** no direct identifiers were removed because none were present.
- **Nothing added:** no data was joined to the households, and nothing about them was inferred.
- **Protected attributes:** the dataset has none (no age, gender, ethnicity or income). The only household attribute is the tariff group.
- **Re-identification:** do not attempt it.

## Cleaning steps and counts

| Step | Count | Source |
|---|---|---|
| Rows read, 2013 | 93,087,837 (EDA chunk count); 93,024,229 after within-chunk de-duplication | `eda/summary.txt`, `results.json` → `p1_matrix` |
| Rows read, 2012 | 60,410,060 (EDA); 60,368,495 after de-duplication | same |
| `Null` kWh, treated as missing, never zero | 12 in 2013; 5,548 in 2012 | `p1_matrix` |
| Duplicate (household, time) rows | 105,173, all with identical kWh. First valid reading kept | `results/duplicates_check.csv` |
| Valid 2013 readings kept | 93,024,217 | `p1_matrix` |
| Households | 5,566 (1,123 ToU, 4,443 Std); 0 with mixed labels | `p1_matrix` |
| Dropped: no 2013 data | 38 (6 ToU, 32 Std) | `results/exclusions_main.csv` |
| High events in 2013 | 69 | `results/events.csv` |
| Dropped: High events with fewer than 3 matched days (±14) | 6 (7 Jan, 29 Sep, 8, 15, 21 and 28 Dec), leaving **63 usable** | `p1_events` |
| Low events in 2013 | 92; 15 dropped, 77 usable | `p1_events` |
| Normal days (all 48 half-hours Normal) | 212 (144 weekday, 68 weekend) | `results/normal_days.csv` |
| Households in main High analysis | **1,114 ToU, 4,396 Std** | `results/exclusions_main.csv` |
| Dropped: no valid High event score | 6 (all Std) | same |
| Dropped: fewer than 5 valid High events | 12 (3 ToU, 9 Std) | same |
| Outliers removed | None. Zeros and large readings are real readings | `docs/decisions.md` §3 |

Sensitivity runs A–D have their own before/after tables in `results/exclusions_{A,B,C,D}.csv`. Run C also drops 553 high night-use homes (top 10% of 2012 night share, cut-off 0.209).

## Known limitations

1. **Opt-in households.** Tariff households chose to join; they were not randomly assigned (Schofield 2015, pp. 65–67). Results apply to households likely to sign up, not to all customers.
2. **Uneven 2012 coverage.** Meters were installed during 2012. Std households reporting rose from 494 in January to 4,421 in December 2012, and ToU households from 87 upwards. The 2012 group comparison rests on later months (`eda/coverage_by_month.csv`).
3. **Fixed GMT clock.** 99.7% of households have 48 readings on the clock-change days, so meters and tariff file both use GMT all year. Times in results are GMT; summer local time is one hour later.
4. **0.001 kWh steps.** Readings are recorded in 0.001 kWh steps, so very small readings are discrete.
5. **Zeros.** 1.18% of ToU and 1.27% of Std 2013 readings are exactly 0. They are concentrated in a few homes, and the fitted distributions cannot produce them (`README_P4.md`).
6. **Six High events without enough comparison days.** These are mainly in December, and none can be scored. Window ±21 (run A) keeps all but 2.
7. **Missing readings and drop-out.** Households report less as the year goes on (Std: 4,404 in January 2013, 4,087 in December). Run D keeps only households with ≥300 days of 2013 data.
8. **Shared event shocks.** All households share the same events and matched days. Resampling households does not capture that dependence (`docs/STATISTICS_EXPLAINED.md`).
