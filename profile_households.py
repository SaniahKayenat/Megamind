"""
profile_households.py
Criterion 2 profiling for the Low Carbon London smart-meter data.

Reads the household readings in chunks (works on the single ~10 GB CSV or on the
folder of 168 split CSVs), and writes small summary tables and figures to an output
folder. Nothing large is held in memory.

Usage:
    python profile_households.py <csv file OR folder of csv files> [output folder]

Outputs (in the output folder, default ./profile_out):
    summary.txt                 key numbers for section 2b of the proposal
    households.csv              one row per household: group, readings and days per year
    coverage_by_month.csv       households with data each month, by group
    kwh_hist_2013.csv           histogram of 2013 half-hourly kWh by group (log bins) + zeros
    profile_2012.csv            average kWh in each of the 48 half-hours, by group, 2012
    dst_check.csv               readings per household on clock-change days 2013
    fig_coverage.png, fig_kwh_hist.png, fig_profile_2012.png, fig_daily_kwh_2012.png
"""
import sys
import glob
import os
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHUNK = 2_000_000
BINS = np.logspace(-3, np.log10(10), 61)  # 0.001 to 10 kWh per half-hour
DST_DAYS = ["2013-03-30", "2013-03-31", "2013-10-26", "2013-10-27"]


def files_from(path):
    if os.path.isdir(path):
        fs = sorted(glob.glob(os.path.join(path, "*.csv")))
        if not fs:
            sys.exit(f"No CSV files found in {path}")
        return fs
    return [path]


def clean(chunk):
    chunk.columns = [c.strip() for c in chunk.columns]
    chunk = chunk.rename(columns={"KWH/hh (per half hour)": "kwh", "stdorToU": "grp"})
    chunk["kwh"] = pd.to_numeric(chunk["kwh"].astype(str).str.strip(), errors="coerce")
    # DateTime looks like '2012-10-12 00:30:00.0000000'; keep the first 19 characters
    chunk["dt"] = pd.to_datetime(chunk["DateTime"].astype(str).str[:19], format="%Y-%m-%d %H:%M:%S")
    chunk["grp"] = chunk["grp"].astype(str).str.strip()
    return chunk[["LCLid", "grp", "dt", "kwh"]]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "profile_out"
    os.makedirs(out, exist_ok=True)

    labels = defaultdict(set)                       # LCLid -> set of group labels
    rows = defaultdict(int)                         # (year) -> total rows
    nulls = defaultdict(int)                        # (year) -> null kWh rows
    dups = 0                                        # duplicate (LCLid, dt) inside a chunk
    month_hh = defaultdict(set)                     # (grp, 'YYYY-MM') -> set of LCLid
    hh_year = defaultdict(lambda: [0, set()])       # (LCLid, year) -> [valid readings, set of dates]
    hh_kwh2012 = defaultdict(float)                 # LCLid -> total kWh 2012
    hist = defaultdict(lambda: np.zeros(len(BINS) - 1, dtype=np.int64))
    zeros = defaultdict(int)
    valid2013 = defaultdict(int)
    prof_sum = defaultdict(float)                   # (grp, slot) -> kWh sum 2012
    prof_n = defaultdict(int)
    dst = defaultdict(int)                          # (LCLid, date) -> readings

    files = files_from(src)
    need = {"LCLid", "stdorToU", "DateTime", "KWH/hh (per half hour)"}
    print(f"{len(files)} CSV files found")
    for f in files:
        mb = os.path.getsize(f) / 1e6
        cols = {c.strip() for c in pd.read_csv(f, nrows=0).columns}
        if not need <= cols:
            print(f"  SKIPPING {os.path.basename(f)}: columns {sorted(cols)} are not the readings format")
            continue
        if mb > 2000:
            print(f"  WARNING {os.path.basename(f)} is {mb:,.0f} MB - if this is the full combined file "
                  f"AND the 168 split files are also here, every reading is counted twice. "
                  f"Keep only one of the two in the folder.")
    for f in files:
        cols = {c.strip() for c in pd.read_csv(f, nrows=0).columns}
        if not need <= cols:
            continue
        print("reading", os.path.basename(f), flush=True)
        for raw in pd.read_csv(f, chunksize=CHUNK, dtype=str):
            c = clean(raw)
            c = c[(c.dt >= "2012-01-01") & (c.dt < "2014-01-01")]
            if c.empty:
                continue
            c["year"] = c.dt.dt.year
            for k, v in c.groupby("year").size().items():
                rows[k] += v
            for k, v in c[c.kwh.isna()].groupby("year").size().items():
                nulls[k] += v
            dups += int(c.duplicated(["LCLid", "dt"]).sum())
            for hid, g in c.groupby("LCLid").grp.unique().items():
                labels[hid].update(g)

            v = c.dropna(subset=["kwh"]).drop_duplicates(["LCLid", "dt"])
            v = v.assign(ym=v.dt.dt.strftime("%Y-%m"), date=v.dt.dt.date)
            for (grp, ym), ids in v.groupby(["grp", "ym"]).LCLid.unique().items():
                month_hh[(grp, ym)].update(ids)
            for (hid, yr), g in v.groupby(["LCLid", "year"]):
                rec = hh_year[(hid, yr)]
                rec[0] += len(g)
                rec[1].update(g.date.unique())

            v12 = v[v.year == 2012]
            for hid, s in v12.groupby("LCLid").kwh.sum().items():
                hh_kwh2012[hid] += s
            slot = v12.dt.dt.hour * 2 + v12.dt.dt.minute // 30
            for (grp, sl), s in v12.groupby([v12.grp, slot]).kwh.agg(["sum", "size"]).iterrows():
                prof_sum[(grp, sl)] += s["sum"]
                prof_n[(grp, sl)] += s["size"]

            v13 = v[v.year == 2013]
            for grp, g in v13.groupby("grp"):
                x = g.kwh.to_numpy()
                zeros[grp] += int((x == 0).sum())
                valid2013[grp] += len(x)
                hist[grp] += np.histogram(x[x > 0], bins=BINS)[0]
            # clock check counts every reading row, including null kWh
            a = c.drop_duplicates(["LCLid", "dt"])
            d = a[a.dt.dt.strftime("%Y-%m-%d").isin(DST_DAYS)]
            for (hid, day), n in d.groupby(["LCLid", d.dt.dt.strftime("%Y-%m-%d")]).size().items():
                dst[(hid, day)] += n

    # ---------- household table ----------
    mixed = {h: s for h, s in labels.items() if len(s) > 1}
    grp_of = {h: (sorted(s)[0] if len(s) == 1 else "MIXED") for h, s in labels.items()}
    hh = []
    for h, g in grp_of.items():
        r12 = hh_year.get((h, 2012), [0, set()])
        r13 = hh_year.get((h, 2013), [0, set()])
        days12 = len(r12[1])
        hh.append(dict(LCLid=h, grp=g, readings_2012=r12[0], days_2012=days12,
                       readings_2013=r13[0], days_2013=len(r13[1]),
                       daily_kwh_2012=(hh_kwh2012[h] / r12[0] * 48) if r12[0] else np.nan))
    hh = pd.DataFrame(hh)
    hh.to_csv(os.path.join(out, "households.csv"), index=False)

    cov = pd.DataFrame([dict(grp=g, month=m, households=len(s)) for (g, m), s in month_hh.items()])
    cov = cov.sort_values(["grp", "month"])
    cov.to_csv(os.path.join(out, "coverage_by_month.csv"), index=False)

    hrows = []
    for grp, counts in hist.items():
        for lo, hi, n in zip(BINS[:-1], BINS[1:], counts):
            hrows.append(dict(grp=grp, bin_low=lo, bin_high=hi, count=int(n)))
    pd.DataFrame(hrows).to_csv(os.path.join(out, "kwh_hist_2013.csv"), index=False)

    prof = pd.DataFrame([dict(grp=g, slot=s, mean_kwh=prof_sum[(g, s)] / prof_n[(g, s)])
                         for (g, s) in prof_sum])
    prof = prof.sort_values(["grp", "slot"])
    prof.to_csv(os.path.join(out, "profile_2012.csv"), index=False)

    dstdf = pd.DataFrame([dict(LCLid=h, date=d, readings=n) for (h, d), n in dst.items()])
    dstdf.to_csv(os.path.join(out, "dst_check.csv"), index=False)

    # ---------- summary ----------
    L = []
    L.append("=== Rows (2012-2013) ===")
    for y in sorted(rows):
        L.append(f"{y}: {rows[y]:,} rows, {nulls[y]:,} null kWh ({nulls[y] / rows[y]:.2%})")
    L.append(f"Duplicate (LCLid, DateTime) rows found within chunks: {dups:,}")
    L.append("")
    L.append("=== Households ===")
    L.append(f"Households with mixed Std/ToU labels: {len(mixed)}")
    for g, d in hh.groupby("grp"):
        L.append(f"{g}: {len(d):,} households | "
                 f"any 2013 data {(d.days_2013 > 0).sum():,} | "
                 f">=180 days in 2013 {(d.days_2013 >= 180).sum():,} | "
                 f">=300 days in 2013 {(d.days_2013 >= 300).sum():,} | "
                 f">=60 days in 2012 {(d.days_2012 >= 60).sum():,}")
    L.append("")
    L.append("=== 2013 half-hourly kWh ===")
    for g in sorted(valid2013):
        L.append(f"{g}: {valid2013[g]:,} valid readings, zeros {zeros[g]:,} ({zeros[g] / valid2013[g]:.2%})")
    L.append("")
    L.append("=== 2012 daily kWh per household (households with >=60 days in 2012) ===")
    for g, d in hh[hh.days_2012 >= 60].groupby("grp"):
        q = d.daily_kwh_2012.quantile([0.25, 0.5, 0.75])
        L.append(f"{g}: n={len(d):,}, mean {d.daily_kwh_2012.mean():.2f}, "
                 f"median {q[0.5]:.2f} (IQR {q[0.25]:.2f}-{q[0.75]:.2f}) kWh/day")
    L.append("")
    L.append("=== Clock check (readings per household-day; 48 = fixed clock, 46/50 = local time) ===")
    if len(dstdf):
        for d, g in dstdf.groupby("date"):
            L.append(f"{d}: " + ", ".join(f"{k} readings: {v} households"
                                         for k, v in g.readings.value_counts().sort_index().items()))
    text = "\n".join(L)
    print("\n" + text)
    with open(os.path.join(out, "summary.txt"), "w") as fh:
        fh.write(text + "\n")

    # ---------- figures ----------
    colors = {"ToU": "#2a6fdb", "Std": "#8a8a8a"}

    fig, ax = plt.subplots(figsize=(9, 4))
    for g, d in cov.groupby("grp"):
        ax.plot(pd.to_datetime(d.month), d.households, marker="o", ms=3, label=g, color=colors.get(g))
    ax.axvline(pd.Timestamp("2013-01-01"), color="k", lw=0.8, ls="--")
    ax.text(pd.Timestamp("2013-01-08"), ax.get_ylim()[1] * 0.95, "tariff starts", fontsize=8, va="top")
    ax.set_ylabel("Households with data")
    ax.set_title("Households with readings each month")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_coverage.png"), dpi=130)

    fig, ax = plt.subplots(figsize=(9, 4))
    mids = np.sqrt(BINS[:-1] * BINS[1:])
    for g, counts in hist.items():
        ax.plot(mids, counts / counts.sum(), label=f"{g} (zeros: {zeros[g] / valid2013[g]:.1%})",
                color=colors.get(g))
    ax.set_xscale("log")
    ax.set_xlabel("kWh per half-hour (log scale)")
    ax.set_ylabel("Share of non-zero readings")
    ax.set_title("Distribution of half-hourly use, 2013")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_kwh_hist.png"), dpi=130)

    fig, ax = plt.subplots(figsize=(9, 4))
    for g, d in prof.groupby("grp"):
        ax.plot(d.slot / 2, d.mean_kwh, label=g, color=colors.get(g))
    ax.set_xticks(range(0, 25, 3))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 3)])
    ax.set_ylabel("Mean kWh per half-hour")
    ax.set_title("Average daily load curve before the tariff (2012)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_profile_2012.png"), dpi=130)

    fig, ax = plt.subplots(figsize=(9, 4))
    sub = hh[(hh.days_2012 >= 60) & hh.grp.isin(["ToU", "Std"])]
    data = [sub[sub.grp == g].daily_kwh_2012.dropna() for g in ["ToU", "Std"]]
    ax.boxplot(data, showfliers=True)
    ax.set_xticks([1, 2], ["ToU", "Std"])
    ax.set_yscale("log")
    ax.set_ylabel("Average daily kWh in 2012 (log scale)")
    ax.set_title("Household daily use before the tariff")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_daily_kwh_2012.png"), dpi=130)

    print(f"\nWrote outputs to {out}/")


if __name__ == "__main__":
    main()