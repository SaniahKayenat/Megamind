"""
run_p1.py - run the whole P1 data pipeline in order.

    python src/run_p1.py [--raw data/raw] [--households profile_out/households.csv] [--force]

Skips the slow matrix step if data/interim/H2013.npy already exists (use --force to rebuild).
Needs results/events.csv and results/matched_days.csv from Stage 2 (01_events.py, 02_matched_days.py).
"""
import argparse
import subprocess
import sys
from pathlib import Path

from config import EVENTS, H2013, MATCHED

HERE = Path(__file__).resolve().parent


def run(*args):
    cmd = [sys.executable, str(HERE / args[0]), *args[1:]]
    print("\n==>", " ".join(cmd[1:]), flush=True)
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=None)
    ap.add_argument("--households", default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if a.force or not H2013.exists():
        extra = []
        if a.raw:
            extra += ["--raw", a.raw]
        if a.households:
            extra += ["--households", a.households]
        run("03_matrix.py", *extra)
    else:
        print("matrix exists, skipping 03_matrix.py (use --force to rebuild)")

    for f in (EVENTS, MATCHED):
        if not f.exists():
            sys.exit(f"Missing {f}. Run Stage 2 first: python src/01_events.py && python src/02_matched_days.py")

    run("04_event_scores.py", "--window", "14")
    run("04_event_scores.py", "--window", "21")
    for v in ["main", "A", "B", "C", "D"]:
        run("05_household_scores.py", "--variant", v)


if __name__ == "__main__":
    main()
