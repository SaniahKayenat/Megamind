# Lin's sections for the team report

## 4. Estimates and uncertainty

The main High analysis retained 1,114 ToU and 4,396 Std households
across 63 usable events. The ToU-minus-Std difference
was -0.01463 kWh per half-hour. This corresponds to a demand reduction
of **0.029 kW per household** (95% percentile bootstrap CI
**0.026 to 0.033 kW**), or 6.2% of matched-day
ToU use. At 50,000 similar households this scales to
1.46 MW (CI 1.28 to 1.66 MW).

For Low events, 1,114 ToU and 4,395 Std households across
77 usable events gave a signed change of
0.033 kW per household (95% CI 0.029 to 0.037 kW), or
8.7% of normal use. These intervals use 10,000
within-group household resamples, seed 2013. If we repeated this study many times, 95% of intervals built this way would contain the true effect.

In 1,000 empirical resampling trials per tariff, interval coverage was
94.2% for High and 94.6% for Low, with roughly
±1.4 percentage points of simulation
error. The checks are conditional on the observed household distributions. Percentage
intervals fix the observed normal-use denominator as specified in advance.

## 8. Conclusion (with Sabrina)

The central decision rule does not support offering the tariff on these assumptions. The High reduction interval is 0.026 to 0.033 kW
against the central break-even threshold of 0.043 kW.
The corresponding decisions at the low (0.017 kW) and high
(0.179 kW) thresholds are **offer** and
**do not offer**. Figure `decision.png` shows the estimated reduction and its
interval alongside these economic assumptions.

The result describes opt-in households and average response during the studied High
hours. It does not establish the benefit for every residential customer or the exact
system-peak capacity saving. Shared shocks, household independence and comparability
of counterfactual group changes remain assumptions. The event model concludes:
**timing/length predict response better than the mean baseline**, with only a 1.4%
reduction in held-out-month RMSE. This is a small predictive improvement.
A further pilot should test recruitment beyond volunteers and
measure coincident network-peak savings and actual operating costs before a broad rollout.
