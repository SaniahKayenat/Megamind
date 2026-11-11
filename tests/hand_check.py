"""
hand_check.py - recompute ONE household's score on ONE event straight from the raw CSVs,
without the matrix or score_event(), and compare it with the pipeline (Stage 3 check).

    python tests/hand_check.py                       # picks a ToU household and High event H026
    python tests/hand_check.py --household MAC000123 --event H058

It also writes results/hand_check_readings.csv with every half-hour it used, so the
same calculation can be repeated in a spreadsheet: mean(event rows) - mean(matched rows).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import RAW_DIR, RESULTS  # noqa: E402
from pipeline_lib import KWH_COL, raw_files  # noqa: E402


def find_household(files, hid):
    """Raw files are sorted by household, so stop once the household has been seen and passed."""
    parts, seen = [], False
    for f in files:
        ids = pd.read_csv(f, usecols=lambda c: c.strip() == "LCLid", dtype=str).iloc[:, 0].str.strip()
        hit = ids == hid
        if hit.any():
            seen = True
            d = pd.read_csv(f, dtype=str)
            d.columns = [c.strip() for c in d.columns]
            parts.append(d[d.LCLid.str.strip() == hid])
        elif seen:
            break
    if not parts:
        sys.exit(f"{hid} not found in the raw files")
    d = pd.concat(parts)
    d["t"] = pd.to_datetime(d.DateTime.str[:19])
    d["kwh"] = pd.to_numeric(d[KWH_COL].str.strip(), errors="coerce")
    d = d.dropna(subset=["kwh"]).drop_duplicates("t", keep="first")   # same rules: Null = missing, keep first
    return d.set_index("t").kwh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAW_DIR))
    ap.add_argument("--household", default=None)
    ap.add_argument("--event", default="H026")
    ap.add_argument("--window", type=int, default=14)
    a = ap.parse_args()

    ev = pd.read_csv(RESULTS / "events.csv", parse_dates=["start"]).set_index("event_id")
    md = pd.read_csv(RESULTS / "matched_days.csv")
    sc = pd.read_csv(RESULTS / f"event_scores_w{a.window}.csv.gz")
    if a.household is None:
        cand = sc[(sc.event_id == a.event) & (sc.group == "ToU") & sc.valid].sort_values("LCLid")
        if cand.empty:
            sys.exit(f"No valid ToU score for {a.event}; pass --event and --household")
        a.household = cand.LCLid.iloc[0]
    row = sc[(sc.event_id == a.event) & (sc.LCLid == a.household)].iloc[0]
    e = ev.loc[a.event]

    r = find_household(raw_files(a.raw), a.household)
    times = pd.date_range(e.start, periods=int(e.n_slots), freq="30min")
    event_vals = r.reindex(times)
    present = event_vals.notna().to_numpy()

    rows = [{"role": "event", "shift_days": 0, "time": t, "kwh": v} for t, v in event_vals.items()]
    kept_days = 0
    for k in md[(md.event_id == a.event) & (md.shift_days.abs() <= a.window)].shift_days:
        mt = times + pd.Timedelta(days=int(k))
        mv = r.reindex(mt).to_numpy()
        mv = np.where(present, mv, np.nan)                       # same half-hours on both sides
        if np.isfinite(mv).sum() >= 0.8 * present.sum():         # day counts with >= 80% of them
            kept_days += 1
            rows += [{"role": "matched", "shift_days": int(k), "time": t, "kwh": v} for t, v in zip(mt, mv)]
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "hand_check_readings.csv", index=False)

    manual = out[out.role == "event"].kwh.mean() - out[out.role == "matched"].kwh.mean()
    print(f"household {a.household}, event {a.event} ({e.start:%Y-%m-%d %H:%M}, {e.hours:g} h), window ±{a.window}")
    print(f"  event half-hours with readings: {int(present.sum())} of {len(present)}; matched days used: {kept_days}")
    print(f"  by hand (raw CSV): {manual:.6f} kWh per half-hour")
    print(f"  pipeline:          {row.score:.6f} kWh per half-hour  (valid={row.valid})")
    ok = np.isclose(manual, row.score, atol=1e-6)
    print("  MATCH" if ok else "  MISMATCH - tell the team before going further")
    print(f"  readings written to {RESULTS / 'hand_check_readings.csv'}")


if __name__ == "__main__":
    main()
