"""Protect the decisions that can change the scientific conclusion.

These tests use invented small examples, never real effect values. They check units,
threshold equality, household resampling, leftover bootstrap batches and missing data.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from inference import boot_diff, decision, effect_summary, reduction_interval, run_tests


def test_worked_example_and_interval_direction():
    # Blueprint worked example: ToU mean -.04 minus Std mean +.015 = -.055.
    r=effect_summary(np.array([-.06,-.02]),np.array([.02,.01]),.4,[-.08,-.03])
    assert r["effect_kwh"]==pytest.approx(-.055)
    assert r["effect_kw"]==pytest.approx(-.11)
    assert r["reduction_kw"]==pytest.approx(.11)
    assert r["reduction_mw_50k"]==pytest.approx(5.5)
    assert r["pct"]==pytest.approx(-13.75)
    assert r["ci_reduction_kw"]==pytest.approx([.06,.16])


def test_threshold_boundary_rules():
    assert decision([.043,.08])=="offer"
    assert decision([.01,.042999])=="do not offer"
    assert decision([.01,.043])=="inconclusive: bigger pilot"
    assert decision([-.02,.06])=="inconclusive: bigger pilot"
    with pytest.raises(ValueError): decision([.08,.01])


def test_bootstrap_constant_groups_remainder_and_shift():
    ci,b=boot_diff(np.ones(5)*2,np.ones(8)*3,B=257,batch=64)
    assert len(b)==257
    assert np.array_equal(ci,[-1,-1])
    t=np.array([0.,1.,3.]); s=np.array([1.,4.,9.,12.])
    ci,a=boot_diff(t,s,B=257,batch=64)
    shifted,c=boot_diff(t+7,s,B=257,batch=64)
    assert np.allclose(c-a,7)
    assert np.allclose(shifted-ci,7)
    assert np.array_equal(a,boot_diff(t,s,B=257,batch=64)[1])
    with pytest.raises(ValueError): boot_diff(np.array([0.,np.nan]),s)


def test_directional_tests_and_unequal_spreads():
    t=np.array([-8.,-6.,-4.,-2.,0.]); s=np.array([0.,.1,.2,.3,.4,.5])
    high=run_tests(t,s,"High"); low=run_tests(t,s,"Low")
    assert high["welch_p"]<.05 and low["welch_p"]>.95
    assert high["cohens_d"]<0
    assert high["sd_ratio_tou_over_std"]>10
    assert high["welch_df"]<len(t)+len(s)-2
