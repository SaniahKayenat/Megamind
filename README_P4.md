# Stage 4: Distribution model and simulation (Nyo)

**Status: done (10 Nov 2026).** All four simulation scenarios pass. Nothing here compares ToU with Std on real data, so the results gate is still closed. Once this is committed, Lin and Arpan can start Stage 5.

## How to run

The scripts need the Stage 1–3 files: `data/interim/H2013.npy`, `results/households_index.csv`, `results/normal_days.csv`, `results/events.csv`, `results/matched_days.csv` and `results/household_scores_main.csv`. Only the `LCLid` and `group` columns of the last file are read.

```
python tests/test_stage4.py          # 2 checks, ~15 s
python src/06_distribution.py        # Part A, ~1 min
python src/07_simulation.py          # Part B, 4,000 trials, ~1 h on 2 cores (faster with more)
python src/07_simulation.py --summarise-only   # redo the summary from simulation_trials.csv
```

All random steps use seed 2013. The simulation gives each trial its own seed from `SeedSequence(2013)`, so the results are identical whatever the number of cores.

## Files

| File | What it is |
|---|---|
| `src/06_distribution.py` | Part A: sample, fits, AIC, bootstrap KS, Q-Q plots, where the fit breaks |
| `src/07_simulation.py` | Part B: the four scenarios, using `pipeline_lib.score_event()` unchanged |
| `tests/test_stage4.py` | (1) the simulation's compact matrix gives exactly the same scores as the real 2013 layout; (2) the bootstrap KS test rejects 4.5% of truly lognormal samples (it should be about 5%) |
| `results/dist_sample.csv` | the 200 households |
| `results/dist_fits.csv` | one row per household: lognormal μ and σ, gamma shape and scale, AIC, KS distance and p-value for each model, zero share, daily use, and quantile ratios |
| `results/dist_where_it_breaks.txt` | every Part A number used below |
| `figures/qq_p10.png`, `qq_p50.png`, `qq_p90.png`, `qq_worst.png` | Q-Q plots, lognormal and gamma side by side |
| `results/simulation_trials.csv` | 4,000 rows, one per trial |
| `results/simulation_summary.txt` | the scenario table |
| `results/results.json` | keys `p4_distribution`, `p4_fit_breaks`, `p4_simulation` |

## Decisions to add to `docs/decisions.md` (Sabrina)

1. **A household with no non-zero readings is replaced.** MAC003627 was drawn, but its meter records only zeros, so neither model can be fitted. It was replaced by a further draw from the remaining eligible households with the same random number generator: MAC004517. The replacement is recorded in `dist_sample.csv` and `results.json`.
2. **Typo in the guideline's `ks_boot` code.** In the guideline, the `hits +=` line sits outside the loop. It belongs inside the loop, as in our code. `tests/test_stage4.py` confirms the corrected version is calibrated.
3. **The simulation uses the real missing-reading pattern.** Each simulated household has the same missing half-hours as a real kept household, so the 80% coverage, matched-day and 5-event rules act on the simulated data exactly as they do on the real data. Only the pattern of which readings are missing is used, never the values.
4. **The simulation uses a compact matrix.** The simulated matrix holds the event day and its matched days next to each other, 48 columns apart, so `score_event()` is called with shifts 1…m. The function itself is not changed, and test 1 shows the scores are identical.
5. **Stress test details.** The top 5% of households by expected use are multiplied by 3 before the effect is applied. Their expected use is scaled to match, so the true reduction is still δ.

---

## Text for the report

### Distribution model (criterion 3)

**Why these two models.**

- *Lognormal:* half-hourly use is a product of many positive factors (whether someone is home × which appliances are on × for how long), and the logarithm of a product is a sum, which tends toward a normal distribution.
- *Gamma:* use is also a sum of several appliance loads, and sums of positive, skewed pieces tend toward a gamma distribution.

**What we fitted.** For each of 200 randomly chosen households (seed 2013, from the 5,187 with at least 300 days of 2013 data; 32 ToU and 168 Std), we took 500 random non-zero readings from the 212 all-Normal days. We fitted both models by maximum likelihood with location fixed at 0.

**Results.**

- **AIC:** the lognormal has the lower AIC for **86%** of households, with a median AIC difference of **−80** in its favour.
- **KS test:** a parametric-bootstrap KS test with 199 refits per test rejects both models for almost every household at the 5% level. Only **3.5%** of households are not rejected for the lognormal and **1.0%** for the gamma.
- **Size of the misfit:** the median KS distance is 0.097 for the lognormal and 0.122 for the gamma.

So the lognormal is clearly the better of the two, but it is not exact. With 500 readings per household, the test detects even a small misfit.

**Where the fit breaks.** The Q-Q plots (Figure X) show three places:

- **Bottom:** the smallest readings sit on a floor (fridges, routers, standby use). In the median household, the observed 1st percentile is **1.40×** the lognormal's, and 83% of households show this. The gamma is much worse here (2.83×).
- **Middle and top:** many homes have two regimes, background use and appliances on. This shows as a step in the Q-Q plot. In 36% of households, the observed 99th percentile is more than 20% above the lognormal's. All 18 high night-use homes in the sample (storage heaters or timers) are rejected.
- **Zeros:** zeros make up **0.72%** of normal-day readings. They are concentrated in a few homes: the median household has none, 4% of households have more than 5%, and one has 44%.

The 0.001 kWh recording steps turned out to matter little: in the median household, none of the 500 readings is at or below 0.01 kWh.

**Why this is acceptable.** The tests use household averages over many events, not raw readings. By the central limit theorem, these averages are close to normal whatever shape the raw readings have. The lognormal's job here is only to drive the simulator. The stress test below adds zeros and a heavy tail to check that the method still works when the model is wrong.

### Simulation study (criterion 4)

**Setup.** We simulated 1,000 trials per scenario. Each trial:

- has the real numbers of households (1,114 ToU, 4,396 Std), each with the real household's pattern of missing readings;
- covers the real 63 usable High events and their matched days;
- gives each household (μ, σ) from the 200 fitted pairs, plus a shared day effect (σ_day = 0.276);
- is scored with the same `score_event()` function, Welch test (one-sided, α = 0.05) and bootstrap interval (2,000 resamples) as the real analysis.

| Scenario | True effect (kWh/half-hour) | Rejected H1 | 95% interval contains the truth | Pass? |
|---|---|---|---|---|
| Null | 0 | **5.9%** (false positives) | 94.9% | yes (3.6–6.4%) |
| At threshold T | −0.0215 | **100%** (power) | **94.7%** | yes (93.6–96.4%) |
| Stress, null (1.2% zeros, top 5% of homes ×3) | 0 | **6.1%** (false positives) | 93.3% | yes (3.6–6.4%) |
| Stress, threshold | −0.0215 | 99.8% | **94.6%** | yes (93.6–96.4%) |

The estimates are unbiased in every scenario: the mean estimate is within 0.00004 kWh of the truth.

**Power sentence.** With our sample sizes, a true reduction of 0.043 kW per household was detected in **100%** of simulated studies (99.8% under the stress test). With no effect, the estimate's spread implies the smallest reduction detectable with 80% power is about **0.004 kW** (0.009 kW under the stress test).

**Caveat.** The simulated households vary only by their fitted (μ, σ), random day effects and half-hour noise. Real households also vary in their response from event to event, so real scores will probably be noisier and the real interval wider. This makes the power figure an upper bound. Lin's resampling coverage check on the real scores (Stage 5, step 5) covers this gap.
