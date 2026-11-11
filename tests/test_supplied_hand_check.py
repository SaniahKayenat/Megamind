"""Independently repeat the supplied reading export's arithmetic.

This does not claim a new extraction from the unavailable original household CSVs.
The inherited hand-check script chose the first valid ToU home on H026 by default.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def test_supplied_reading_export_matches_rebuilt_event_score():
    readings=pd.read_csv(ROOT/"results/hand_check_readings.csv")
    manual=readings.loc[readings.role=="event","kwh"].mean()-readings.loc[readings.role=="matched","kwh"].mean()
    scores=pd.read_csv(ROOT/"results/event_scores_w14.csv.gz")
    selected=scores[(scores.event_id=="H026") & (scores.group=="ToU") & scores.valid].sort_values("LCLid").iloc[0]
    # Raw export has decimal readings; the rebuilt matrix has float32 representations.
    assert np.isclose(manual,selected.score,rtol=0,atol=1e-7)
