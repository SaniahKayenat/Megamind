"""
05_household_scores.py - one score per household for High events,
plus the event-level table the regression (Stage 6) uses.

    python src/05_household_scores.py --variant main
    python src/05_household_scores.py --variant A    # matched days within +/-21  (needs 04 --window 21)
    python src/05_household_scores.py --variant B    # without the off-grid event days
    python src/05_household_scores.py --variant C    # without high night-use homes
    python src/05_household_scores.py --variant D    # only households with >= 300 days of 2013 data

Outputs (for each variant)
    results/household_scores_{variant}.csv   LCLid, group, tariff, n_events, score, normal_use, event_use
                                             (score in kWh per half-hour; normal_use = mean matched_mean,
                                              used by Stage 5 for "% of normal use")
    results/exclusions_{variant}.csv         households kept and dropped, by group, tariff and reason
    results/event_effects_{variant}.csv      one row per event: ToU mean, Std mean, effect, counts
"""
import argparse

import pandas as pd

from config import EVENTS, HOUSEHOLDS, MIN_DAYS_2013, MIN_EVENTS, RESULTS, TARIFFS_USED
from pipeline_lib import save_result

VARIANTS = {
    "main": dict(window=14, drop_off_grid=False, drop_high_night=False, min_days=None),
    "A": dict(window=21, drop_off_grid=False, drop_high_night=False, min_days=None),
    "B": dict(window=14, drop_off_grid=True, drop_high_night=False, min_days=None),
    "C": dict(window=14, drop_off_grid=False, drop_high_night=True, min_days=None),
    "D": dict(window=14, drop_off_grid=False, drop_high_night=False, min_days=MIN_DAYS_2013),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="main", choices=VARIANTS)
    args = ap.parse_args()
    v = VARIANTS[args.variant]

    hh = pd.read_csv(HOUSEHOLDS)
    ev = pd.read_csv(EVENTS)
    ev = ev[ev.tariff.isin(TARIFFS_USED)]          # High events only
    sc = pd.read_csv(RESULTS / f"event_scores_w{v['window']}.csv.gz")

    # ---------- filters for this variant ----------
    keep_hh = pd.Series(True, index=hh.index)
    reason = pd.Series("", index=hh.index)
    no_data = hh.days_2013 == 0
    reason[no_data] = "no 2013 data"
    keep_hh &= ~no_data
    if v["drop_high_night"]:
        m = hh.high_night.fillna(False).astype(bool) & keep_hh
        reason[m] = "high night-use home"
        keep_hh &= ~m
    if v["min_days"]:
        m = (hh.days_2013 < v["min_days"]) & keep_hh
        reason[m] = f"fewer than {v['min_days']} days of 2013 data"
        keep_hh &= ~m
    hh["filter_reason"] = reason

    ev_keep = ev if not v["drop_off_grid"] else ev[~ev.off_grid.astype(bool)]
    sc = sc[sc.valid & sc.event_id.isin(ev_keep.event_id) & sc.LCLid.isin(hh.LCLid[keep_hh])]

    # ---------- household scores ----------
    g = (sc.groupby(["LCLid", "group", "tariff"])
           .agg(n_events=("score", "size"), score=("score", "mean"),
                normal_use=("matched_mean", "mean"), event_use=("event_mean", "mean"))
           .reset_index())
    enough = g.n_events >= MIN_EVENTS
    scores = g[enough]
    scores.to_csv(RESULTS / f"household_scores_{args.variant}.csv", index=False, float_format="%.6g")

    # ---------- exclusion table ----------
    rows = []
    for tariff in sorted(ev.tariff.unique()):
        for group, d in hh.groupby("group"):
            got = g[(g.tariff == tariff) & (g.group == group)]
            row = {"tariff": tariff, "group": group, "households": len(d)}
            for r in d.filter_reason[d.filter_reason != ""].unique():
                row[f"dropped: {r}"] = int((d.filter_reason == r).sum())
            passed = d[d.filter_reason == ""]
            row["dropped: no valid events"] = int((~passed.LCLid.isin(got.LCLid)).sum())
            row[f"dropped: fewer than {MIN_EVENTS} valid events"] = int((got.n_events < MIN_EVENTS).sum())
            row["kept"] = int((got.n_events >= MIN_EVENTS).sum())
            rows.append(row)
    excl = pd.DataFrame(rows).fillna(0)
    excl.to_csv(RESULTS / f"exclusions_{args.variant}.csv", index=False)

    # ---------- event-level effects (for the Stage 6 regression) ----------
    sc_kept = sc.merge(scores[["LCLid", "tariff"]], on=["LCLid", "tariff"])   # same households as the tests
    e = (sc_kept.groupby(["event_id", "group"]).score.agg(["mean", "size"]).unstack("group"))
    e.columns = [f"{a}_{b}" for a, b in e.columns]
    e = e.rename(columns={"mean_ToU": "tou_mean", "mean_Std": "std_mean", "size_ToU": "n_tou", "size_Std": "n_std"})
    e["effect"] = e.tou_mean - e.std_mean
    e = ev_keep.merge(e.reset_index(), on="event_id", how="left")
    e.to_csv(RESULTS / f"event_effects_{args.variant}.csv", index=False, float_format="%.6g")

    summary = {f"{t}_{grp}": int(n) for (t, grp), n in scores.groupby(["tariff", "group"]).size().items()}
    save_result(f"p1_household_scores_{args.variant}", summary)
    print(f"variant {args.variant}: households with a score -> {summary}")
    print(excl.to_string(index=False))


if __name__ == "__main__":
    main()
