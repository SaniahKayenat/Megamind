"""
03_matrix.py - turn the raw readings into two household x half-hour matrices.

    python src/03_matrix.py [--raw data/raw] [--households profile_out/households.csv]

Outputs
    data/interim/H2013.npy          float32, households x 17,520 (NaN = no reading)
    data/interim/H2012.npy          float32, households x 17,568 (2012 is a leap year)
    results/households_index.csv    one row per household, in matrix row order:
                                    LCLid, group, readings/days per year, 2012 night share, high_night flag
    results/duplicates_check.csv    duplicate (household, time) rows: how many, how many identical
    results.json                    p1.* summary numbers

Rules (see config.py / docs/decisions.md)
    - Duplicate (household, time) rows: the FIRST valid reading is kept.
    - Null kWh = missing (never zero).
    - Column = half-hours since 1 Jan 00:00 on a fixed clock (no daylight-saving shift).

Run time: one pass over all raw files, roughly 20-40 minutes. Needs ~800 MB of disk;
the matrices are written straight to disk (memory-mapped), so RAM use stays modest.
"""
import argparse
import sys

import numpy as np
import pandas as pd

from config import (H2012, H2013, HOUSEHOLDS, INTERIM, NIGHT_MIN_DAYS_2012, NIGHT_SLOTS,
                    NIGHT_TOP_SHARE, RAW_DIR, RESULTS, SLOTS_2012, SLOTS_2013, START_2012, START_2013)
from pipeline_lib import clean_chunk, raw_files, save_result, slot_of, insert_readings

CHUNK = 2_000_000


def household_list(files, households_csv):
    """Sorted household IDs with their group. Uses the EDA's households.csv if given (fast)."""
    if households_csv:
        h = pd.read_csv(households_csv)
        h = h.rename(columns={"grp": "group"})[["LCLid", "group"]]
        return h.sort_values("LCLid").reset_index(drop=True)
    print("Listing households (one quick pass reading two columns)...")
    seen = {}
    for f in files:
        for c in pd.read_csv(f, usecols=lambda c: c.strip() in ("LCLid", "stdorToU"), dtype=str, chunksize=CHUNK):
            c.columns = [x.strip() for x in c.columns]
            for hid, g in c.drop_duplicates().itertuples(index=False):
                seen.setdefault(hid.strip(), set()).add(g.strip())
    rows = [(h, sorted(g)[0] if len(g) == 1 else "MIXED") for h, g in seen.items()]
    return pd.DataFrame(rows, columns=["LCLid", "group"]).sort_values("LCLid").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAW_DIR), help="folder with the household CSVs")
    ap.add_argument("--households", default=None,
                    help="households.csv from profile_households.py (optional; saves one pass)")
    args = ap.parse_args()

    INTERIM.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    files = raw_files(args.raw)
    print(f"{len(files)} readings files")

    hh = household_list(files, args.households)
    row_of = pd.Series(np.arange(len(hh)), index=hh.LCLid)
    n = len(hh)
    print(f"{n} households")

    mats = {
        2012: (np.lib.format.open_memmap(H2012, mode="w+", dtype=np.float32, shape=(n, SLOTS_2012)), START_2012),
        2013: (np.lib.format.open_memmap(H2013, mode="w+", dtype=np.float32, shape=(n, SLOTS_2013)), START_2013),
    }
    for M, _ in mats.values():
        M[:] = np.nan
    # A Null observation still counts as an encountered household/time. Keep this
    # separate from NaN in the retained matrices to count cross-chunk duplicates.
    seen_slots = {year: np.zeros(M.shape, dtype=bool) for year, (M, _) in mats.items()}

    stats = dict(rows_2012=0, rows_2013=0, null_2012=0, null_2013=0, unknown_household_rows=0,
                 dup_rows=0, dup_identical=0)
    labels = {}

    for f in files:
        print("reading", f, flush=True)
        for raw in pd.read_csv(f, chunksize=CHUNK, dtype=str):
            c = clean_chunk(raw)
            c = c[(c.dt >= START_2012) & (c.dt < "2014-01-01")]
            if c.empty:
                continue
            for hid, g in c.groupby("LCLid").grp.unique().items():
                labels.setdefault(hid, set()).update(g)

            c = c.assign(row=c.LCLid.map(row_of))
            stats["unknown_household_rows"] += int(c.row.isna().sum())
            c = c[c.row.notna()]

            for year, (M, start) in mats.items():
                d = c[c.dt.dt.year == year]
                stats[f"rows_{year}"] += len(d)
                stats[f"null_{year}"] += int(d.kwh.isna().sum())
                if d.empty:
                    continue
                rows = d.row.to_numpy(np.int64)
                cols = slot_of(d.dt, start)
                vals = d.kwh.to_numpy(np.float32)
                duplicates, identical = insert_readings(M, seen_slots[year], rows, cols, vals)
                stats["dup_rows"] += duplicates
                stats["dup_identical"] += identical
    for M, _ in mats.values():
        M.flush()

    # ---------- per-household facts, in blocks to limit memory ----------
    H12, H13 = mats[2012][0], mats[2013][0]
    out = []
    for a in range(0, n, 500):
        b = min(a + 500, n)
        x13 = np.asarray(H13[a:b])
        x12 = np.asarray(H12[a:b])
        d13 = ~np.isnan(x13).reshape(b - a, 365, 48).all(axis=2)
        d12 = ~np.isnan(x12).reshape(b - a, 366, 48).all(axis=2)
        x12d = x12.reshape(b - a, 366, 48)
        out.append(pd.DataFrame({
            "readings_2013": (~np.isnan(x13)).sum(1),
            "days_2013": d13.sum(1),
            "readings_2012": (~np.isnan(x12)).sum(1),
            "days_2012": d12.sum(1),
            "kwh_2012": np.nansum(x12, axis=1),
            "kwh_night_2012": np.nansum(x12d[:, :, list(NIGHT_SLOTS)], axis=(1, 2)),
        }))
    facts = pd.concat(out, ignore_index=True)
    hh = pd.concat([hh, facts], axis=1)
    hh["row"] = np.arange(n)
    hh["mixed_label"] = hh.LCLid.map(lambda h: len(labels.get(h, set())) > 1)

    ok = (hh.days_2012 >= NIGHT_MIN_DAYS_2012) & (hh.kwh_2012 > 0)
    hh["night_share_2012"] = np.where(ok, hh.kwh_night_2012 / hh.kwh_2012.where(ok), np.nan)
    cut = hh.loc[ok, "night_share_2012"].quantile(1 - NIGHT_TOP_SHARE)
    hh["high_night"] = hh.night_share_2012 >= cut
    hh.to_csv(HOUSEHOLDS, index=False)

    # ---------- duplicates and summary ----------
    pd.DataFrame([{"duplicate_rows": stats["dup_rows"], "identical_kwh": stats["dup_identical"],
                   "different_kwh": stats["dup_rows"] - stats["dup_identical"]}]).to_csv(
        RESULTS / "duplicates_check.csv", index=False)

    cells_2013 = int(hh.readings_2013.sum())
    summary = {
        "households": n,
        "households_by_group": hh.group.value_counts().to_dict(),
        "households_mixed_label": int(hh.mixed_label.sum()),
        "rows_2013": stats["rows_2013"], "null_kwh_2013": stats["null_2013"],
        "rows_2012": stats["rows_2012"], "null_kwh_2012": stats["null_2012"],
        "readings_kept_2013": cells_2013,
        "duplicate_rows": stats["dup_rows"], "duplicate_rows_identical": stats["dup_identical"],
        "unknown_household_rows": stats["unknown_household_rows"],
        "night_share_cutoff_top10": float(cut),
        "high_night_households": int(hh.high_night.sum()),
        "households_no_2013_data": hh[hh.days_2013 == 0].group.value_counts().to_dict(),
        "households_300plus_days_2013": hh[hh.days_2013 >= 300].group.value_counts().to_dict(),
    }
    save_result("p1_matrix", summary)
    for k, v in summary.items():
        print(f"  {k}: {v}")
    if stats["unknown_household_rows"]:
        print("WARNING: some rows belong to households missing from --households; rerun without it.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
