"""Record inherited tests transparently, without inventing original execution times.

The log timestamp is the import time. The notes explicitly state that original
timestamps and Git commits are unavailable. Re-running this script appends records,
as required by the project's no-deletion rule.
"""
import pandas as pd
from config import RESULTS
from pipeline_lib import log_test


def main():
    note="Imported supplied result; timestamp is import time; original run commit/time unavailable."
    fits=pd.read_csv(RESULTS/"dist_fits.csv")
    for r in fits.itertuples():
        for model,prefix in [("lognormal","ln"),("gamma","ga")]:
            log_test("Nyo (imported)","distribution goodness of fit",str(r.LCLid),
                     model+"_parametric_bootstrap_KS",getattr(r,prefix+"_ks_d"),
                     getattr(r,prefix+"_ks_p"),"",note)
    trials=pd.read_csv(RESULTS/"simulation_trials.csv",keep_default_na=False)
    for r in trials.itertuples():
        log_test("Nyo (imported)","H1 simulated",f"{r.scenario}/{r.trial}",
                 "welch_less",r.t,r.p,r.estimate,note)
    print(f"Imported {2*len(fits)+len(trials)} supplied tests with provenance notes.")


if __name__=="__main__": main()
