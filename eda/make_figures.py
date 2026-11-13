"""
make_figures.py
Draws every figure used in the research proposal (Stat_Proposal.docx).

It does not read the 10 GB raw data. It uses the small tables written by
profile_households.py plus the tariff schedule, so it runs in a few seconds.

Usage:
    python make_figures.py <profile_out folder> <Tariffs.xlsx> [figure folder]

Example:
    python make_figures.py profile_out data/Tariffs.xlsx figures

Inputs (from profile_households.py):
    profile_2012.csv, coverage_by_month.csv, kwh_hist_2013.csv, households.csv

Outputs (default folder: ./figures):
    fig1_high_by_hour.png        Figure 1  - High-price half-hours by hour of day, 2013
    fig2_load_curve_2012.png     Figure 2  - Average daily load curve in 2012, ToU vs Std
    figB1_coverage.png           Figure B1 - Households reporting each month
    figB2_kwh_distribution.png   Figure B2 - Distribution of half-hourly kWh in 2013
    figB3_daily_kwh_2012.png     Figure B3 - Average daily use per household in 2012
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------- style ----------
BLUE = "#2a6fdb"    # ToU households / the highlighted part of a chart
GREY = "#9a9a9a"    # Std households / everything else
INK = "#222222"
MUTED = "#666666"
GRID = "#e6e6e6"
BAND = "#f2f2f2"
DPI = 220

plt.rcParams.update({
    "font.family": "DejaVu Serif", "font.size": 9,
    "axes.edgecolor": "#bbbbbb", "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
})

HOUR_TICKS = range(0, 24, 3)
HOUR_LABELS = [f"{h:02d}:00" for h in HOUR_TICKS]


def style(ax, axis="y"):
    ax.grid(axis=axis, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def save(fig, out, name):
    fig.tight_layout()
    path = os.path.join(out, name)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print("wrote", path)


# ---------- Figure 1: when High prices happened ----------
def fig_high_by_hour(tariffs_path, out):
    t = pd.read_excel(tariffs_path)
    t.columns = ["t", "tariff"]
    t["t"] = pd.to_datetime(t["t"])
    high = t[t.tariff.str.strip() == "High"]
    h = high.t.dt.hour.value_counts().reindex(range(24), fill_value=0)
    evening = h.loc[17:22].sum() / h.sum()          # 17:00-23:00

    fig, ax = plt.subplots(figsize=(6.3, 2.1))
    ax.bar(h.index, h.values, width=0.8,
           color=[BLUE if 17 <= i <= 22 else GREY for i in h.index])
    ax.set_xticks(HOUR_TICKS)
    ax.set_xticklabels(HOUR_LABELS)
    ax.set_ylabel("High half-hours")
    style(ax)
    ax.text(16.4, 52, f"17:00–23:00 holds\n{evening:.0%} of all High half-hours",
            color=INK, fontsize=8.5, ha="right")
    save(fig, out, "fig1_high_by_hour.png")
    return evening


# ---------- Figure 2: 2012 daily load curve ----------
def fig_load_curve(profile_dir, out):
    p = pd.read_csv(os.path.join(profile_dir, "profile_2012.csv"))
    p = p.pivot(index="slot", columns="grp", values="mean_kwh")
    x = p.index / 2
    night = 1 - p.ToU.loc[0:11].sum() / p.Std.loc[0:11].sum()     # 00:00-06:00
    evening = 1 - p.ToU.loc[34:45].sum() / p.Std.loc[34:45].sum()  # 17:00-23:00

    fig, ax = plt.subplots(figsize=(6.3, 2.3))
    ax.axvspan(0, 6, color=BAND, zorder=0)
    ax.axvspan(17, 23, color=BAND, zorder=0)
    ax.plot(x, p.Std, color=GREY, lw=2, label="Std (flat rate)")
    ax.plot(x, p.ToU, color=BLUE, lw=2, label="ToU (dynamic)")
    ax.text(0.2, 0.322, f"00:00–06:00: ToU {night:.0%} lower", fontsize=8, color=MUTED)
    ax.text(17.2, 0.322, f"17:00–23:00: ToU {evening:.0%} lower", fontsize=8, color=MUTED)
    ax.annotate("Std spike at 00:30", xy=(0.5, p.Std.loc[1]), xytext=(2.2, 0.21),
                fontsize=8, color=MUTED, arrowprops=dict(arrowstyle="-", color="#999", lw=0.7))
    ax.set_xlim(0, 23.5)
    ax.set_ylim(0.08, 0.34)
    ax.set_xticks(HOUR_TICKS)
    ax.set_xticklabels(HOUR_LABELS)
    ax.set_ylabel("kWh per half-hour")
    style(ax)
    ax.legend(frameon=False, loc="upper center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, 1.17))
    save(fig, out, "fig2_load_curve_2012.png")
    return night, evening


# ---------- Figure B1: households reporting each month ----------
def fig_coverage(profile_dir, out):
    c = pd.read_csv(os.path.join(profile_dir, "coverage_by_month.csv"))
    c["m"] = pd.to_datetime(c.month)
    fig, ax = plt.subplots(figsize=(6.3, 2.1))
    for g, col in [("Std", GREY), ("ToU", BLUE)]:
        d = c[c.grp == g]
        ax.plot(d.m, d.households, color=col, lw=2, marker="o", ms=3, label=g)
    ax.axvline(pd.Timestamp("2013-01-01"), color="#888", lw=0.8, ls="--")
    ax.text(pd.Timestamp("2013-01-10"), 2600, "tariff year starts",
            fontsize=8, color=MUTED)
    ax.set_ylabel("Households reporting")
    style(ax)
    ax.legend(frameon=False, fontsize=8, loc="center right")
    save(fig, out, "figB1_coverage.png")


# ---------- Figure B2: distribution of half-hourly kWh ----------
def fig_kwh_distribution(profile_dir, out):
    hh = pd.read_csv(os.path.join(profile_dir, "kwh_hist_2013.csv"))
    fig, ax = plt.subplots(figsize=(6.3, 2.1))
    for g, col in [("Std", GREY), ("ToU", BLUE)]:
        d = hh[hh.grp == g]
        mid = np.sqrt(d.bin_low * d.bin_high)   # geometric bin centre (log bins)
        ax.plot(mid, d["count"] / d["count"].sum(), color=col, lw=2, label=g)
    ax.set_xscale("log")
    ax.set_xlabel("kWh per half-hour (log scale)")
    ax.set_ylabel("Share of non-zero readings")
    ax.annotate("gaps: meters record in 0.001 kWh steps", xy=(0.0025, 0.002), xytext=(0.0011, 0.05),
                fontsize=7.5, color=MUTED, arrowprops=dict(arrowstyle="-", color="#999", lw=0.7))
    style(ax)
    ax.legend(frameon=False, fontsize=8)
    save(fig, out, "figB2_kwh_distribution.png")


# ---------- Figure B3: daily use per household, 2012 ----------
def fig_daily_kwh(profile_dir, out):
    h = pd.read_csv(os.path.join(profile_dir, "households.csv"))
    h = h[h.days_2012 >= 60]                     # same rule as summary.txt
    data = [h[h.grp == g].daily_kwh_2012.clip(lower=0.1) for g in ["ToU", "Std"]]
    fig, ax = plt.subplots(figsize=(6.3, 1.9))
    b = ax.boxplot(data, orientation="horizontal", widths=0.5, patch_artist=True,
                   flierprops=dict(marker="o", ms=2, mfc="#bbb", mec="none"),
                   medianprops=dict(color=INK))
    for patch, col in zip(b["boxes"], [BLUE, GREY]):
        patch.set_facecolor(col)
        patch.set_alpha(0.5)
        patch.set_edgecolor(col)
    ax.set_yticks([1, 2], ["ToU", "Std"])
    ax.set_xscale("log")
    ax.set_xlabel("Average daily kWh in 2012 (log scale)")
    style(ax, axis="x")
    save(fig, out, "figB3_daily_kwh_2012.png")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    profile_dir, tariffs = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "figures"
    os.makedirs(out, exist_ok=True)

    evening_share = fig_high_by_hour(tariffs, out)
    night, evening = fig_load_curve(profile_dir, out)
    fig_coverage(profile_dir, out)
    fig_kwh_distribution(profile_dir, out)
    fig_daily_kwh(profile_dir, out)

    print(f"\nNumbers quoted in the proposal:"
          f"\n  share of High half-hours in 17:00-23:00: {evening_share:.1%}"
          f"\n  ToU vs Std in 2012, 00:00-06:00: {night:.1%} lower"
          f"\n  ToU vs Std in 2012, 17:00-23:00: {evening:.1%} lower")


if __name__ == "__main__":
    main()
