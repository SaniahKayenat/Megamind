"""Stage 2a (Javed): price events and normal days from Tariffs.xlsx.

Reads  data/raw/Tariffs.xlsx
Writes results/events.csv, results/normal_days.csv

Rules: docs/decisions.md §4–5. Same code as stage2_events_matched_days.ipynb.
Run from the repository root:  python src/01_events.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
try:  # shared paths, if config.py defines them
    from config import RAW, RESULTS
except ImportError:
    RAW, RESULTS = ROOT / "data" / "raw", ROOT / "results"
TARIFF_FILE = Path(RAW) / "Tariffs.xlsx"
RESULTS = Path(RESULTS)

YEAR_START = pd.Timestamp("2013-01-01 00:00:00")
N_SLOTS = 365 * 48
BANK_HOLIDAYS_2013 = {pd.Timestamp(d).date() for d in [
    "2013-01-01", "2013-03-29", "2013-04-01", "2013-05-06",
    "2013-05-27", "2013-08-26", "2013-12-25", "2013-12-26"]}
GRID_HOURS = {23, 2, 5, 8, 11, 14, 17, 20}
EVENING_START_HOURS = {17, 20}
WINTER_MONTHS = {10, 11, 12, 1, 2, 3}


def day_type(d):
    d = pd.Timestamp(d)
    return "weekend" if d.dayofweek >= 5 or d.date() in BANK_HOLIDAYS_2013 else "weekday"


def load_tariffs(path):
    t = pd.read_excel(path, sheet_name=0)
    t.columns = [str(c).strip() for c in t.columns]
    t = t.rename(columns={t.columns[0]: "time", t.columns[1]: "price"})
    t["time"] = pd.to_datetime(t["time"])
    t["price"] = t["price"].astype(str).str.strip()
    t = t.sort_values("time").reset_index(drop=True)
    t["slot"] = ((t["time"] - YEAR_START) / pd.Timedelta(minutes=30)).round().astype(int)
    assert len(t) == N_SLOTS, f"expected {N_SLOTS} half-hours, found {len(t)}"
    assert (t["slot"].to_numpy() == np.arange(N_SLOTS)).all(), "gaps or repeats in the timestamps"
    assert set(t["price"]) == {"High", "Low", "Normal"}, f"unexpected prices: {set(t['price'])}"
    return t


def build_events(tariffs):
    price = tariffs["price"].to_numpy()
    new_run = np.r_[True, price[1:] != price[:-1]]
    run_starts = np.flatnonzero(new_run)
    run_lengths = np.diff(np.r_[run_starts, len(price)])
    rows = [(price[s], int(s), int(n)) for s, n in zip(run_starts, run_lengths) if price[s] != "Normal"]
    ev = pd.DataFrame(rows, columns=["tariff", "first_slot", "n_slots"])

    ev["event_id"] = [("H" if p == "High" else "L") + f"{i:03d}" for i, p in enumerate(ev["tariff"])]
    ev["start"] = YEAR_START + pd.to_timedelta(ev["first_slot"] * 30, unit="min")
    ev["end"] = ev["start"] + pd.to_timedelta(ev["n_slots"] * 30, unit="min")
    ev["hours"] = ev["n_slots"] / 2
    ev["day_type"] = ev["start"].map(day_type)

    def on_grid(ts):
        return (ts.dt.minute == 0) & ts.dt.hour.isin(GRID_HOURS)

    ev["off_grid"] = ~(on_grid(ev["start"]) & on_grid(ev["end"]))
    ev["low_before"] = [int(s > 0 and price[s - 1] == "Low") for s in ev["first_slot"]]
    ev["evening"] = ((ev["start"].dt.minute == 0) & ev["start"].dt.hour.isin(EVENING_START_HOURS)).astype(int)
    ev["month"] = ev["start"].dt.month
    ev["winter"] = ev["month"].isin(WINTER_MONTHS).astype(int)
    return ev[["event_id", "tariff", "start", "first_slot", "n_slots", "end", "hours",
               "day_type", "off_grid", "low_before", "evening", "month", "winter"]]


def build_normal_days(tariffs):
    price = tariffs["price"].to_numpy()
    dates = pd.date_range("2013-01-01", periods=365, freq="D")
    is_normal = (price.reshape(365, 48) == "Normal").all(axis=1)
    types = np.array([day_type(d) for d in dates])
    return pd.DataFrame({"date": dates[is_normal].strftime("%Y-%m-%d"), "day_type": types[is_normal]})


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    tariffs = load_tariffs(TARIFF_FILE)
    events = build_events(tariffs)
    normal_days = build_normal_days(tariffs)
    events.to_csv(RESULTS / "events.csv", index=False)
    normal_days.to_csv(RESULTS / "normal_days.csv", index=False)

    high = events[events.tariff == "High"]
    print(f"Events: High {len(high)} (expect 69), Low {(events.tariff == 'Low').sum()} (expect 92)")
    print("High lengths (h: count):", {float(k): int(v) for k, v in high.hours.value_counts().sort_index().items()},
          "(expect 3: 26, 4: 1, 6: 34, 12: 7, 24: 1)")
    print("Off-grid dates:", sorted(set(events.loc[events.off_grid, "start"].dt.strftime("%Y-%m-%d"))),
          "(expect 2013-01-29, 2013-02-09, 2013-03-21)")
    print(f"Normal days: {len(normal_days)} (expect 212)")
    print("Wrote", RESULTS / "events.csv", "and", RESULTS / "normal_days.csv")


if __name__ == "__main__":
    main()
