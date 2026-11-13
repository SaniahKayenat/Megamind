# Report section 5 and slide 8 (Arpan)

## Report section 5: Tests (about 0.6 page)

We tested H1, stated before any result: during High events, the mean ToU household score is
below the mean Std score (one-sided Welch t-test, α = 0.05, with a one-sided Mann–Whitney test as
a check). Each test uses one score per household (1,114 ToU, 4,396 Std), because readings within a
home are not independent. Household scores are heavy-tailed (Figure: Q-Q plots), but the bootstrap
distribution of the difference is bell-shaped (skew −0.08), so the comparison of means is reliable.
ToU scores vary 1.5 times as much as Std scores, which is why we use Welch rather than Student's t.

Tariff households used 0.0293 kW less per household during High events (95% interval 0.0256 to
0.0332 kW; 6.2% of normal use). The Welch test rejects "no reduction" (t = −14.99, df = 1,372,
p < 10⁻⁴⁰), and Mann–Whitney agrees (p < 10⁻⁶⁰; a ToU home scores lower than a Std home in 67% of
pairs). Cohen's d is −0.64, a medium effect.

The four pre-stated sensitivity runs give reductions of 0.028 to 0.030 kW (Table). In every run
Welch, Mann–Whitney and the bootstrap interval point the same way, and every interval lies below
the break-even threshold of 0.043 kW. Run C removes 10.7% of Std but 6.7% of ToU homes, yet its
estimate is almost unchanged. The reduction is real and robust, but too small to clear break-even.
All tests are listed in the test log (Appendix).

**Table: sensitivity runs**

| Run | ToU / Std | Reduction, kW (95% CI) | Welch p | Mann–Whitney p | Cohen's d | Decision |
|---|---|---|---|---|---|---|
| Main (±14 days) | 1,114 / 4,396 | 0.0293 (0.0256 to 0.0332) | 2.0 × 10⁻⁴⁷ | 1.0 × 10⁻⁶⁸ | −0.64 | Do not offer |
| A (±21 days) | 1,114 / 4,398 | 0.0283 (0.0246 to 0.0321) | 2.0 × 10⁻⁴⁶ | 2.3 × 10⁻⁶⁷ | −0.62 | Do not offer |
| B (no off-grid days) | 1,114 / 4,396 | 0.0289 (0.0252 to 0.0328) | 5.4 × 10⁻⁴⁷ | 2.3 × 10⁻⁶⁵ | −0.62 | Do not offer |
| C (no high night-use homes) | 1,039 / 3,921 | 0.0295 (0.0255 to 0.0336) | 2.7 × 10⁻⁴⁴ | 4.6 × 10⁻⁶⁵ | −0.64 | Do not offer |
| D (≥300 days of data) | 1,047 / 4,140 | 0.0287 (0.0250 to 0.0324) | 8.0 × 10⁻⁴⁸ | 1.4 × 10⁻⁶⁷ | −0.69 | Do not offer |

Interval wording: if we repeated this study many times, 95% of intervals built this way would
contain the true effect.

## Slide 8 (1.5 minutes)

**Title:** A real cut, every way we test it, but too small to pay off

**On the slide:** the sensitivity table above (or each run's reduction as a dot with whiskers and a
vertical line at T = 0.043 kW), plus one line: "Welch t = −15.0, p < 10⁻⁴⁰ · d = −0.64 · SD ratio 1.5".

**Script:**

> Lin showed the size of the cut. My job was to test whether it's real, check the test's
> assumptions, and see if it survives other choices.
>
> We stated one hypothesis before seeing any result: during High prices, tariff households use
> less than flat-rate households. We test it on one score per household, 1,114 against 4,396,
> because readings inside one home aren't independent.
>
> The scores have heavy tails, but the bootstrap distribution of the difference is a clean bell
> curve, so the mean comparison holds. The tariff group is 1.5 times as variable, so we use
> Welch's test, which doesn't assume equal spreads.
>
> Welch gives t of minus 15: p is far below any threshold. The rank-based Mann–Whitney check
> agrees. Cohen's d is 0.64, a medium effect.
>
> Then we changed each questionable choice: a wider matching window, dropping odd event days,
> dropping heavy night users, and keeping only full-year homes. Every run gives 28 to 30 watts,
> every test agrees, and every interval stays below the 43-watt break-even.
>
> So the response is real and robust, but it's not big enough to pay for itself.
