# Lin's speaker notes and Q&A

Use these with the three Lin slides, inserted as team slides 7, 10 and 11.
The allocated total is about 2.5 minutes. Rehearse aloud and trim to the team's clock.

## Slide 7: Effect and uncertainty (about 90 seconds)

We compare each household with its usual use at the same clock times on nearby normal
days, then subtract the change seen in flat-tariff households. This gives one score per
household, so repeated half-hour readings do not count as independent observations.

For High events, the estimated reduction is 0.029 kilowatts per
household. The 95% bootstrap interval runs from 0.026 to
0.033 kilowatts. That is 6.2% of the
dynamic-tariff households' normal use. For 50,000 similar homes,
the estimate scales to 1.46 megawatts during these event hours.

The bootstrap resamples whole households within each group. If we repeated this study many times, 95% of intervals built this way would contain the true effect.
Our separate resampling exercise obtained coverage of 94.2% for High
and 94.6% for Low under the observed household distributions.

## Slide 10: Recommendation (about 30 seconds)

Our decision compares the whole reduction interval with a break-even threshold fixed
before this analysis. The central threshold is 0.043
kilowatts per home. The rule gives: do not offer.
Using the lower cost threshold gives offer; the higher threshold gives
do not offer. The recommendation therefore depends on the economic assumptions
as well as the measured reduction.

## Slide 11: Limits and next evidence (about 30 seconds)

These households volunteered for the tariff. Our conclusion applies most directly to
similar households likely to sign up. It does not prove that every customer would
respond the same way. We measured average response during High-price events, rather
than directly measuring avoided network upgrades. A broader pilot should test who
joins, response at the actual network peak and the real costs of running the tariff.

## Q&A

**Why is a reduction positive if Delta is negative?** Delta is ToU minus Std. Multiply
by two to convert half-hour energy to power, then reverse the sign to describe a cut.

**Why do the interval endpoints reverse?** Multiplying by a negative constant reverses
their order. [-a,-b] must be reordered when a was the smaller endpoint.

**Why bootstrap homes?** Repeated readings within a home depend on one another. The
analysis unit is a household, not a reading. Shared shocks across homes remain a limit.

**Does 95% mean a 95% probability for this interval?** Use the repeated-study statement
above. It describes the method's long-run performance, subject to its assumptions.

**What did the extra coverage check prove?** It checked the method under centered
empirical household populations with a known imposed difference. It cannot establish
the unknown true effect or fix the study's observational design.

**Do small p-values justify rollout?** The decision is based on the effect interval
relative to break-even, not on statistical significance alone.

**Why Low events?** They were in the original blueprint as a separately reported
directional question. They have no economic rollout threshold.

**What exactly did you add?** Lin's estimates, intervals, coverage, decision figure,
writing, speaking material and reproduction check, plus missing shared and supporting
tests/model code. The original ZIPs remain unchanged and local history records edits.
