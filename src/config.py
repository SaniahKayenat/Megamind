"""
config.py - paths and analysis rules shared by every script.

The rules below must match docs/decisions.md. Change them there first,
commit, and only then change them here.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ---------- paths ----------
RAW_DIR = ROOT / "data" / "raw"                 # the 168 household CSVs go here (not committed)
TARIFFS = RAW_DIR / "Tariffs.xlsx"
INTERIM = ROOT / "data" / "interim"             # large generated files (not committed)
RESULTS = ROOT / "results"                      # small tables + results.json (committed)

H2013 = INTERIM / "H2013.npy"                   # households x 17,520 half-hours of 2013
H2012 = INTERIM / "H2012.npy"                   # households x 17,568 half-hours of 2012 (leap year)
HOUSEHOLDS = RESULTS / "households_index.csv"   # row order of the matrices + household facts
EVENTS = RESULTS / "events.csv"                 # from Stage 2 (src/01_events.py)
MATCHED = RESULTS / "matched_days.csv"          # from Stage 2 (src/02_matched_days.py)
RESULTS_JSON = RESULTS / "results.json"

# ---------- time ----------
START_2012 = "2012-01-01 00:00:00"
START_2013 = "2013-01-01 00:00:00"
SLOTS_2012 = 366 * 48
SLOTS_2013 = 365 * 48

# ---------- analysis rules (must match docs/decisions.md) ----------
COVER_MIN = 0.80          # share of an event's half-hours that must have readings
DAY_COVER_MIN = 0.80      # a matched day counts if it has >= 80% of the half-hours present on the event day
MIN_MATCHED_DAYS = 3      # matched days needed for a valid event score
MIN_EVENTS = 5            # valid events needed for a household score
MATCH_WINDOW_MAIN = 14    # +/- days
MATCH_WINDOW_ALT = 21     # sensitivity run A (changed from 7, decisions.md section 9)
NIGHT_SLOTS = range(0, 12)          # 00:00-06:00
NIGHT_MIN_DAYS_2012 = 60            # days of 2012 data needed to compute night share
NIGHT_TOP_SHARE = 0.10              # top 10% night share = "high night-use" (sensitivity run C)
MIN_DAYS_2013 = 300                 # sensitivity run D
SEED = 2013

# ---------- scope ----------
TARIFFS_USED = ["High", "Low"]  # restore the original blueprint scope; see dated decisions

# Reporting paths and fixed inference settings. A signed effect differs from a reduction.
FIGURES = ROOT / "figures"
REPORTS = ROOT / "reports"
TEST_LOG = RESULTS / "test_log.csv"
BOOTSTRAP_DRAWS = 10_000
COVERAGE_TRIALS = 1_000
COVERAGE_BOOTSTRAP_DRAWS = 2_000
THRESHOLDS_KW = {"central": 0.043, "low": 0.017, "high": 0.179}
PRE_ANALYSIS_COMMIT = "7341120911a7358d1cf055e20cee50ce3b945928"
