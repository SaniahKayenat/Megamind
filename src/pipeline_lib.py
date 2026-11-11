"""
pipeline_lib.py - functions shared by the P1 scripts and reused by others.

score_event() is the single definition of an event score. the Stage 4 simulation
study must call this same function so that the simulation tests the exact
method used on the real data.
"""
import json
import os
import warnings
import csv
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import (COVER_MIN, DAY_COVER_MIN, MIN_MATCHED_DAYS, RESULTS_JSON,
                    RESULTS, ROOT, TEST_LOG)


# ---------------------------------------------------------------- reading raw data
KWH_COL = "KWH/hh (per half hour)"
NEED_COLS = {"LCLid", "stdorToU", "DateTime", KWH_COL}


def raw_files(path):
    """Household CSVs in a folder (or a single CSV). Skips files without the four columns."""
    path = str(path)
    files = [path] if os.path.isfile(path) else sorted(
        os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(".csv"))
    good = []
    for f in files:
        cols = {c.strip() for c in pd.read_csv(f, nrows=0).columns}
        if NEED_COLS <= cols:
            good.append(f)
        else:
            print(f"  skipping {os.path.basename(f)} (not a readings file)")
    if not good:
        raise SystemExit(f"No readings files found in {path}")
    return good


def clean_chunk(raw):
    """Strip column names, kWh text -> number (Null -> NaN), parse timestamps."""
    raw.columns = [c.strip() for c in raw.columns]
    out = pd.DataFrame({
        "LCLid": raw["LCLid"].astype(str).str.strip(),
        "grp": raw["stdorToU"].astype(str).str.strip(),
        # DateTime looks like '2013-01-01 00:30:00.0000000'
        "dt": pd.to_datetime(raw["DateTime"].astype(str).str[:19], format="%Y-%m-%d %H:%M:%S"),
        "kwh": pd.to_numeric(raw[KWH_COL].astype(str).str.strip(), errors="coerce"),
    })
    return out


def slot_of(dt, start):
    """Half-hour index from `start` (fixed clock: readings and tariff ignore daylight saving)."""
    return ((dt - pd.Timestamp(start)) // pd.Timedelta(minutes=30)).to_numpy(np.int64)


# ---------------------------------------------------------------- the event score
def score_event(H, slots, shifts, cover_min=COVER_MIN, day_cover_min=DAY_COVER_MIN,
                min_days=MIN_MATCHED_DAYS):
    """
    Score every household (row of H) on one event.

    H       households x half-hours array (NaN = no reading)
    slots   the event's half-hour columns in H
    shifts  matched-day shifts in days (e.g. [-14, -7, 3]); column s + 48*k is
            the same clock time k days away

    For each household:
      event_mean   = mean use over the event half-hours that have readings
      matched_mean = mean use over the SAME half-hours on the matched days
                     (a half-hour missing on the event day is dropped on the matched days too;
                      a matched day counts only if it has >= day_cover_min of those half-hours)
      score        = event_mean - matched_mean   (negative = used less than usual)
      valid        = cover >= cover_min and at least min_days usable matched days
    Missing readings are never treated as zero: they are left out of sums AND counts.
    """
    S = np.asarray(slots, dtype=np.int64)
    n = H.shape[0]
    ev = np.asarray(H[:, S], dtype=np.float64)
    present = ~np.isnan(ev)
    n_present = present.sum(axis=1)
    cover = n_present / len(S)

    out = {"cover": cover, "n_days": np.zeros(n, dtype=np.int64)}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)   # all-NaN rows -> NaN, by design
        out["event_mean"] = np.nanmean(ev, axis=1)
        if len(shifts) == 0:
            out["matched_mean"] = np.full(n, np.nan)
        else:
            M = np.stack([np.asarray(H[:, S + 48 * int(k)], dtype=np.float64) for k in shifts], axis=1)
            M = np.where(present[:, None, :], M, np.nan)                 # same half-hours on both sides
            day_n = (~np.isnan(M)).sum(axis=2)                            # households x days
            day_ok = (n_present[:, None] > 0) & (day_n >= day_cover_min * n_present[:, None])
            M = np.where(day_ok[:, :, None], M, np.nan)
            out["matched_mean"] = np.nanmean(M.reshape(n, -1), axis=1)
            out["n_days"] = day_ok.sum(axis=1)
    out["score"] = out["event_mean"] - out["matched_mean"]
    out["valid"] = (cover >= cover_min) & (out["n_days"] >= min_days) & np.isfinite(out["score"])
    return out


def event_slots(first_slot, n_slots):
    return np.arange(int(first_slot), int(first_slot) + int(n_slots))


# ---------------------------------------------------------------- results.json
def save_result(key, value):
    """Add or replace one entry in results/results.json (every reported number goes here)."""
    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if RESULTS_JSON.exists():
        data = json.loads(RESULTS_JSON.read_text())
    data[key] = value
    # Replace atomically: an interrupted write cannot truncate the shared dictionary.
    # Scripts run sequentially, so a later stage cannot overwrite a concurrent writer.
    temp = RESULTS_JSON.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True, default=_jsonable,
                               allow_nan=False) + "\n")
    temp.replace(RESULTS_JSON)


def _jsonable(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.bool_):
        return bool(x)
    raise TypeError(type(x))


def group_scores(variant="main", tariff="High"):
    """Read identical, validated household inputs for Lin and Arpan.

    Every household has equal weight. An event-rich household is not counted as
    multiple independent observations. Fail on corrupt inputs rather than dropping
    problematic rows silently. The percentage denominator follows the fixed plan.
    """
    if variant not in {"main", "A", "B", "C", "D"} or tariff not in {"High", "Low"}:
        raise ValueError("Unknown variant or tariff")
    d = pd.read_csv(RESULTS / f"household_scores_{variant}.csv")
    d = d[d.tariff == tariff]
    if d.empty or d.LCLid.duplicated().any() or set(d.group) != {"ToU", "Std"}:
        raise ValueError(f"Invalid household table: {variant}/{tariff}")
    if not np.isfinite(d[["score", "normal_use"]].to_numpy()).all():
        raise ValueError("Non-finite household input; fix upstream, never replace with zero")
    tou = d.loc[d.group == "ToU", "score"].to_numpy(dtype=float)
    std = d.loc[d.group == "Std", "score"].to_numpy(dtype=float)
    normal = float(d.loc[d.group == "ToU", "normal_use"].mean())
    if min(len(tou), len(std)) < 2 or normal <= 0:
        raise ValueError("Need two households per group and positive normal use")
    return tou, std, normal


def log_test(person, hypothesis, run, test, statistic, p_value, effect, note=""):
    """Append every test, including reruns. UTC time records execution, not data time.

    The commit identifies the code baseline; notes flag inherited tests and local
    modifications. Log files intentionally differ across reruns, unlike results.json.
    """
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unavailable"
    fields = ["timestamp", "git_commit", "person", "hypothesis", "run", "test",
              "statistic", "p_value", "effect", "note"]
    TEST_LOG.parent.mkdir(parents=True, exist_ok=True)
    exists = TEST_LOG.exists() and TEST_LOG.stat().st_size > 0
    with TEST_LOG.open("a", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(dict(zip(fields, [datetime.now(timezone.utc).isoformat(), commit,
            person, hypothesis, run, test, statistic, p_value, effect, note])))
