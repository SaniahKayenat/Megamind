"""Reproduce the whole Team Megamind project from supplied matrices with one command.

python run_all.py                  # prepared matrices + frozen Stage 4 evidence
python run_all.py --from-raw        # rebuild matrices from 168 household CSVs first

The default deliberately reuses the committed Stage 4 evidence. Rebuilding Nyo's
simulation is a separate, expensive validation, not silently substituted here.
The raw route still uses that frozen calibration; neither route is described as a
new complete Stage 4 rerun. See README and docs/PROVENANCE.md for that boundary.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def run(*parts):
    """Stop on failure: later documents must never use a partially updated analysis."""
    print("Running "+" ".join(parts),flush=True)
    subprocess.run([sys.executable,*parts],cwd=ROOT,check=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-raw",action="store_true")
    ap.add_argument("--workers",type=int,default=2)
    args=ap.parse_args()
    os.environ.setdefault("MPLCONFIGDIR",str(ROOT/"tmp"/"matplotlib"))
    if not (ROOT/"data/raw/Tariffs.xlsx").exists():
        ap.error("Put supplied Tariffs.xlsx in data/raw/ before running.")
    if args.from_raw:
        csvs=list((ROOT/"data/raw").glob("*.csv"))
        if not csvs: ap.error("Raw household CSVs were not supplied. Add them or use prepared mode.")
    elif not (ROOT/"data/interim/H2013.npy").exists():
        ap.error("Prepared mode needs the supplied H2013.npy in data/interim/.")
    run("src/check_gate.py")
    run("src/01_events.py"); run("src/02_matched_days.py")
    if args.from_raw: run("src/03_matrix.py")
    for window in [14,21]: run("src/04_event_scores.py","--window",str(window),"--mmap")
    for variant in ["main","A","B","C","D"]:
        run("src/05_household_scores.py","--variant",variant)
    # Preserve imported tests and append new executions rather than clearing the log.
    if not (ROOT/"results/test_log.csv").exists(): run("src/import_test_log.py")
    run("src/08_estimates.py","--workers",str(args.workers))
    # Stage 5 (Arpan, H1 official) and Lin's supporting High+Low tests
    run("src/09_tests.py"); run("src/09b_tests_high_low.py")
    # Stage 6 (Ahmad Jawid, official model) and Lin's supporting model fit
    run("src/10_model.py"); run("src/10b_model_supporting.py")
    run("src/11_writeup.py")
    # EDA / proposal figures from the committed EDA summary tables (seconds)
    run("eda/make_figures.py","eda","data/raw/Tariffs.xlsx","figures/eda")
    print("Finished. Open reports/START_HERE.md.",flush=True)


if __name__=="__main__": main()
