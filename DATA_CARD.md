# Data card

Source: UK Power Networks, *SmartMeter Energy Consumption Data in London Households*,
[London Datastore](https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d).
Licence: CC BY 4.0 as recorded in the team's blueprint; credit UK Power Networks.

## What the supplied data contains

Half-hourly household electricity readings, pseudonymous household identifiers and
fixed tariff group labels. No names or addresses are present in the supplied matrices
or analysis tables. The tariff workbook assigns High, Low or Normal to each half-hour
of 2013. Analysis uses 2013; 2012 is used only for descriptive context and the night-use
exclusion definition. Do not commit raw household data or large interim matrices.

The original household CSVs are absent. The supplied 2012/2013 float32 matrices encode
missing readings as NaN, never zero. Zeros and high readings remain observations.
Saniah supplied the row-order index and cleaning summary; Javed supplied the workbook
and matching files. The continuation recalculates scores from the supplied 2013 matrix.

## Cleaning and exclusions

The first valid duplicate is the planned retained reading. All duplicate rows in the
supplied summary are reported identical. Counts are preserved in `results.json` under
`p1_matrix` and `duplicates_check.csv`; they were not independently reconstructed from
absent raw CSVs. The inherited summary's row counters are after within-chunk
deduplication, so label them carefully. The continuation repairs that counter and
first-valid-duplicate handling in the writer, tested synthetically. Original CSVs are
still needed before claiming a raw-data audit or replacing the inherited counts.

The event, matched-day and household exclusion rules are in `docs/decisions.md`.
Each run has a before/after table in `results/exclusions_{main,A,B,C,D}.csv`, by tariff
and group. Counts used in writing are also saved under `reporting_context` in results.json.
High and Low are both restored to the original planned scope. No observations were
removed to improve significance or distribution fit.

## Limitations

Allocation was opt-in. Results describe households likely to sign up, subject to
counterfactual group comparability. Missingness and dropout may affect comparability.
Household resampling does not represent all dependence from shared events or matched
dates. The clock is fixed GMT without daylight-saving adjustments. Meter resolution
is 0.001 kWh. The fitted continuous models omit exact zeros and fit imperfectly.
The tariff-event mean reduction does not directly establish coincident network-peak
savings. Prespecified economic scenarios are assumptions, not trial-measured costs.

Original historical Git ordering cannot be verified from the supplied ZIPs. The local
checkpoint establishes order only for this continuation. No new direct identifiers
were collected, inferred or joined to the data. Do not attempt re-identification.
