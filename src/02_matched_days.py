"""Stage 2b (Javed): matched normal days for every event.

Reads  results/events.csv, results/normal_days.csv   (from 01_events.py)
Writes results/matched_days.csv   event_id, shift_days   (one row per matched day, |k| <= 21)
       results/matched_counts.csv event_id, tariff, start, n_matched_14, n_matched_21

A shift of k days (k != 0) is a matched day if the shifted window (slots + 48k) stays inside 2013,
every date it touches is an all-Normal day, and the shifted start date has the event's day type.
Rules: docs/decisions.md §5. Same code as stage2_events_matched_days.ipynb.
Run from the repository root:  python src/02_matched_days.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
try:  # shared paths, if config.py defines them
    from config import RESULTS
except ImportError:
    RESULTS = ROOT / "results"
RESULTS = Path(RESULTS)

N_SLOTS = 365 * 48
MAX_SHIFT = 21
MIN_MATCHED = 3
BANK_HOLIDAYS_2013 = {pd.Timestamp(d).date() for d in [
    "2013-01-01", "2013-03-29", "2013-04-01", "2013-05-06",
    "2013-05-27", "2013-08-26", "2013-12-25", "2013-12-26"]}


def day_type(d):
    d = pd.Timestamp(d)
    return "weekend" if d.dayofweek >= 5 or d.date() in BANK_HOLIDAYS_2013 else "weekday"


def build_matched_days(events, is_normal_day, day_type_of_day, max_shift=MAX_SHIFT):
    rows = []
    for e in events.itertuples(index=False):
        for k in range(-max_shift, max_shift + 1):
            if k == 0:
                continue
            first = e.first_slot + 48 * k
            last = first + e.n_slots - 1
            if first < 0 or last >= N_SLOTS:
                continue
            d_first, d_last = first // 48, last // 48
            if not is_normal_day[d_first:d_last + 1].all():
                continue
            if day_type_of_day[d_first] != e.day_type:
                continue
            rows.append((e.event_id, k))
    return pd.DataFrame(rows, columns=["event_id", "shift_days"])


def count_matched(events, matched, window):
    m = matched[matched["shift_days"].abs() <= window]
    return events["event_id"].map(m.groupby("event_id").size()).fillna(0).astype(int)


def main():
    events = pd.read_csv(RESULTS / "events.csv", parse_dates=["start", "end"])
    normal = pd.read_csv(RESULTS / "normal_days.csv", parse_dates=["date"])
    dates = pd.date_range("2013-01-01", periods=365, freq="D")
    is_normal_day = dates.isin(normal["date"])
    day_type_of_day = np.array([day_type(d) for d in dates])

    matched = build_matched_days(events, is_normal_day, day_type_of_day)
    matched.to_csv(RESULTS / "matched_days.csv", index=False)

    counts = events[["event_id", "tariff", "start"]].copy()
    counts["n_matched_14"] = count_matched(events, matched, 14)
    counts["n_matched_21"] = count_matched(events, matched, 21)
    counts.to_csv(RESULTS / "matched_counts.csv", index=False)

    high, low = counts.tariff == "High", counts.tariff == "Low"
    n7 = count_matched(events, matched, 7)
    usable = high & (counts.n_matched_14 >= MIN_MATCHED)
    print("High < 3 matched (±14):",
          counts.loc[high & (counts.n_matched_14 < MIN_MATCHED), "start"].dt.strftime("%Y-%m-%d").tolist(),
          "(expect 01-07, 09-29, 12-08, 12-15, 12-21, 12-28)")
    print(f"Low < 3 matched (±14): {(low & (counts.n_matched_14 < MIN_MATCHED)).sum()} (expect 15)")
    print(f"High usable (±14): {usable.sum()} (expect 63); "
          f"median matched days {counts.loc[usable, 'n_matched_14'].median():g} (expect 9)")
    print(f"< 3 matched (±21): High {(high & (counts.n_matched_21 < MIN_MATCHED)).sum()} (expect 2), "
          f"Low {(low & (counts.n_matched_21 < MIN_MATCHED)).sum()} (expect 5)")
    print(f"High < 3 matched (±7, proposal): {(high & (n7 < MIN_MATCHED)).sum()} (expect 16)")
    print("Wrote", RESULTS / "matched_days.csv", "and", RESULTS / "matched_counts.csv")


if __name__ == "__main__":
    main()
