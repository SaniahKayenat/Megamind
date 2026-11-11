"""
stage3_report.py - one summary of Stages 1 and 3 to share with the team (and to write the data section).

    python src/stage3_report.py        ->  prints it and saves results/stage3_summary.txt

RESULTS GATE: this report deliberately shows only counts, coverage and validity.
It never compares ToU and Std scores (no group means, no differences), because the
effect must not be looked at until decisions.md, T and the simulation are committed.
"""
import json

import pandas as pd

from config import RESULTS

lines = []


def say(x=""):
    print(x)
    lines.append(str(x))


def main():
    res = json.loads((RESULTS / "results.json").read_text())
    hh = pd.read_csv(RESULTS / "households_index.csv")
    ev = pd.read_csv(RESULTS / "events.csv")
    dup = pd.read_csv(RESULTS / "duplicates_check.csv")
    sc = pd.read_csv(RESULTS / "event_scores_w14.csv.gz", usecols=["LCLid", "group", "event_id", "tariff",
                                                                     "cover", "n_days", "valid"])

    say("=== Stage 1: matrix ===")
    for k, v in res["p1_matrix"].items():
        say(f"  {k}: {v}")
    say(f"  duplicates check: {dup.to_dict('records')[0]}")
    say("")
    say("=== Households (from households_index.csv) ===")
    g = hh.groupby("group")
    say(pd.DataFrame({
        "households": g.size(),
        "any_2013_data": g.apply(lambda d: (d.days_2013 > 0).sum()),
        "days_2013_median": g.days_2013.median(),
        ">=300_days_2013": g.apply(lambda d: (d.days_2013 >= 300).sum()),
        "night_share_2012_median": g.night_share_2012.median().round(4),
        "high_night_homes": g.high_night.sum(),
    }).to_string())
    say("")
    say("=== Stage 3: event scores (window ±14) ===")
    s = res["p1_event_scores_w14"]
    say(f"  events scored: {s['events_scored']}; valid share of household x event pairs: {s['valid_share']:.3f}")
    say(f"  events with < 3 matched days: {s['events_with_fewer_than_3_matched_days']}")
    say("")
    say("Why scores are invalid (household x event pairs, ±14):")
    sc["reason"] = "valid"
    sc.loc[~sc.valid, "reason"] = "other (no readings)"
    sc.loc[~sc.valid & (sc.n_days < 3) & (sc.cover >= 0.8), "reason"] = "< 3 matched days"
    sc.loc[~sc.valid & (sc.cover < 0.8), "reason"] = "< 80% event coverage"
    say(sc.groupby(["tariff", "group"]).reason.value_counts().unstack(fill_value=0).to_string())
    say("")
    per_ev = sc[sc.valid].groupby(["event_id", "group"]).size().unstack(fill_value=0)
    per_ev = ev[["event_id", "tariff", "start"]].merge(per_ev.reset_index(), on="event_id", how="left").fillna(0)
    hi = per_ev[per_ev.tariff == "High"]
    say("Valid households per High event (counts only):")
    say(f"  events with any valid score: {(hi[['ToU', 'Std']].sum(axis=1) > 0).sum()} of {len(hi)}")
    say(f"  ToU households per usable event: min {int(hi.loc[hi.ToU > 0, 'ToU'].min())}, "
        f"median {int(hi.loc[hi.ToU > 0, 'ToU'].median())}, max {int(hi.ToU.max())}")
    say(f"  Std households per usable event: min {int(hi.loc[hi.Std > 0, 'Std'].min())}, "
        f"median {int(hi.loc[hi.Std > 0, 'Std'].median())}, max {int(hi.Std.max())}")
    say("")
    say("=== Stage 3: household scores and exclusions ===")
    for v in ["main", "A", "B", "C", "D"]:
        key = f"p1_household_scores_{v}"
        if key in res:
            say(f"  {v}: {res[key]}")
    say("")
    for v in ["main", "A", "B", "C", "D"]:
        p = RESULTS / f"exclusions_{v}.csv"
        if p.exists():
            say(f"exclusions_{v}.csv")
            say(pd.read_csv(p).to_string(index=False))
            say("")
    hs = pd.read_csv(RESULTS / "household_scores_main.csv")
    say("Valid events per household (main), median [min-max]:")
    for (t, grp), d in hs.groupby(["tariff", "group"]):
        say(f"  {t} {grp}: {d.n_events.median():g} [{d.n_events.min()}-{d.n_events.max()}]")

    (RESULTS / "stage3_summary.txt").write_text("\n".join(lines) + "\n")
    print(f"\nsaved {RESULTS / 'stage3_summary.txt'}")


if __name__ == "__main__":
    main()
