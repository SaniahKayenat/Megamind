# Statistics explained for Lin

## What each household's score means

First compare a household's mean use during one price event with its mean use at the
same clock slots on nearby all-Normal days of the same weekday/weekend type. A negative
score means lower use. Missing readings are not zero. A matched day must cover at least
80% of the event's present slots; the event must cover at least 80% of its slots and have
at least three counted matched days. A household must have five valid events.

Average valid event scores to obtain one score per household. Households receive equal
weight regardless of their number of valid events. Compare the mean ToU score with the
mean Std score. The Std comparison attempts to subtract demand changes that happened
on the event day even without a tariff signal. This depends on comparability of the
groups' counterfactual changes. Opt-in allocation limits causal interpretation.

## Effect, reduction and units

Delta is ToU minus Std in kWh per half-hour. Signed change in power is twice Delta.
For High events a positive reduction is minus twice Delta. If Delta's interval is [a,b],
the reduction interval is [-2b,-2a]. Reversing the endpoints is essential.

Multiply kW per home by 50,000 and divide by 1,000 to obtain MW at that scale. This is a
linear scenario for similar sign-ups during the studied hours, not a forecast that all
customers will respond identically or that every High hour coincides with a system peak.

The signed percentage is 100 times Delta divided by mean matched-day use of ToU homes.
The planned interval scales Delta's interval by that fixed observed denominator. It
does not include the denominator's sampling uncertainty. Reduction percent reverses
the sign. Low-event increases retain their positive signed direction.

## Why bootstrap households

Repeated readings and events within one household depend on one another. Resampling
households preserves their already-aggregated information without pretending that
half-hours are independent. Each bootstrap draw samples the original number of ToU
households and the original number of Std households separately, with replacement.
Take their mean difference, repeat 10,000 times, and use the 2.5th and 97.5th percentiles.

The interval is two-sided even though the hypothesis tests are one-sided. A one-sided
5% p-value can disagree with whether a two-sided 95% interval excludes zero without a
coding error. The correct required wording is: "If we repeated this study many times,
95% of intervals built this way would contain the true effect."

The bootstrap still assumes household-level independence. Common event shocks or shared
matched dates can induce cross-household dependence that this bootstrap does not model.
The Std comparison may reduce shared demand shifts but cannot prove independence.

## What the coverage exercise tells us

Center each group's observed scores at zero and add the observed Delta to the ToU group.
These empirical populations now have a known target difference. Generate 1,000 new
studies of the real group sizes. In each, build a percentile interval using 2,000 inner
resamples. Coverage is the fraction containing that known target. The prespecified
check is 93.6%–96.4%, reflecting about 1.4 percentage points of Monte Carlo error.

This checks the procedure under an empirical model based on these households. It does
not reveal the unknown true effect, prove a causal design, or validate transfer to
different households. A failed check stays in the report; seeds are never tuned.

## Tests and effect sizes

Welch tests a difference of means while allowing unequal group variances. H1 passes ToU
first with `less`, and H2 with `greater`. Mann-Whitney checks rank distributions. It
does not automatically test medians or the same mean difference as Welch. Cohen's d is
Delta divided by the pooled household-score SD. Its sign describes direction, while kW
describes practical magnitude. Both planned questions are reported, without a
multiple-testing adjustment as the blueprint specifies. Sensitivity runs are robustness
checks, not independent discoveries.

Q-Q plots describe tail behaviour. A skewed individual-score distribution does not by
itself invalidate a large-sample mean comparison, but the central limit theorem is an
approximation, not a guarantee. Neither a histogram nor a normality test proves independence.

## Economic decision and regression

Apply the threshold to the positive High-event reduction interval. Offer if its lower
endpoint reaches the threshold, do not offer if its upper endpoint is below it, otherwise
recommend a bigger pilot. Repeat at all three fixed cost/value thresholds. The threshold
is an assumption-based break-even rule from the project, not a newly estimated fact.

The separate regression has one row per usable High event and predicts its signed group
effect from evening, hours, winter and Low-before. HC3 permits unequal residual spreads.
It does not correct temporal correlation. Check VIF, Cook's distance and date-ordered
Durbin-Watson. Cross-validation holds out a whole month. Its baseline is the training
mean, not the full-data mean, which would leak held-out information. If prediction does
not improve over the baseline, report that outcome even if individual coefficients
have small p-values.
