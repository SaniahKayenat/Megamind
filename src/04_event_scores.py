"""
04_event_scores.py - score every household on each High and Low event.

    python src/04_event_scores.py --window 14     # main analysis
    python src/04_event_scores.py --window 21     # sensitivity run A

Inputs
    data/interim/H2013.npy, results/households_index.csv     (03_matrix.py)
    results/events.csv          from Stage 2 (01_events.py); needs columns: event_id, tariff, first_slot, n_slots
    results/matched_days.csv    from Stage 2 (01_events.py); needs columns: event_id, shift_days
                                (built for +/-21 days; each run keeps |shift_days| <= its window)

Output
    results/event_scores_w{window}.csv.gz   one row per household x event:
        LCLid, group, event_id, tariff, event_mean, matched_mean, score, cover, n_days, valid
"""
import argparse

import numpy as np
import pandas as pd

from config import EVENTS, H2013, HOUSEHOLDS, MATCHED, RESULTS, TARIFFS_USED
from pipeline_lib import event_slots, save_result, score_event
from check_gate import require_gate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=14, help="matched days within +/- this many days")
    ap.add_argument("--mmap", action="store_true", help="read the matrix from disk instead of loading it (low RAM)")
    args = ap.parse_args()
    require_gate()  # the continuation's decisions and inherited calibration are committed

    hh = pd.read_csv(HOUSEHOLDS).sort_values("row")
    H = np.load(H2013, mmap_mode="r" if args.mmap else None)
    assert H.shape[0] == len(hh), "matrix and households_index.csv disagree; rerun 03_matrix.py"

    ev = pd.read_csv(EVENTS)
    ev = ev[ev.tariff.isin(TARIFFS_USED)]
    md = pd.read_csv(MATCHED)
    md = md[md.shift_days.abs() <= args.window]
    shifts = md.groupby("event_id").shift_days.apply(list).to_dict()

    parts, few_days = [], []
    for e in ev.itertuples(index=False):
        S = event_slots(e.first_slot, e.n_slots)
        ks = shifts.get(e.event_id, [])
        lo, hi = S.min() + 48 * min(ks, default=0), S.max() + 48 * max(ks, default=0)
        assert lo >= 0 and hi < H.shape[1], f"event {e.event_id}: a matched day falls outside 2013"
        if len(ks) < 3:
            few_days.append(e.event_id)
        r = score_event(H, S, ks)
        parts.append(pd.DataFrame({
            "LCLid": hh.LCLid.to_numpy(), "group": hh.group.to_numpy(),
            "event_id": e.event_id, "tariff": e.tariff,
            "event_mean": r["event_mean"], "matched_mean": r["matched_mean"], "score": r["score"],
            "cover": r["cover"], "n_days": r["n_days"], "valid": r["valid"],
        }))
    out = pd.concat(parts, ignore_index=True)
    path = RESULTS / f"event_scores_w{args.window}.csv.gz"
    out.to_csv(path, index=False, float_format="%.17g",
               compression={"method": "gzip", "mtime": 0})

    summary = {
        "events_scored": int(len(ev)),
        "events_with_fewer_than_3_matched_days": few_days,
        "valid_scores": int(out.valid.sum()),
        "valid_share": float(out.valid.mean()),
    }
    save_result(f"p1_event_scores_w{args.window}", summary)
    print(f"wrote {path}")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
