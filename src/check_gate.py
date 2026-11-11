"""Validate committed pre-analysis evidence without loading any real group effects.

This verifies the continuation's checkpoint, not the team's unavailable prior history.
The simulation's prespecified tests are false positives for null scenarios and
interval coverage for threshold scenarios. Other coverage rates are also retained.
"""
import hashlib
import json
import subprocess

import pandas as pd

from config import PRE_ANALYSIS_COMMIT, RESULTS, ROOT
from pipeline_lib import save_result


def require_gate():
    """Raise before real analysis if checkpoint evidence is missing or altered."""
    hashes = {}
    for name in ["docs/decisions.md", "results/simulation_trials.csv", "results/dist_fits.csv"]:
        committed = subprocess.check_output(
            ["git", "show", f"{PRE_ANALYSIS_COMMIT}:{name}"], cwd=ROOT)
        if name != "docs/decisions.md" and committed != (ROOT / name).read_bytes():
            raise RuntimeError(f"Pre-analysis evidence changed: {name}; review and document it")
        hashes[name] = hashlib.sha256(committed).hexdigest()
    trials = pd.read_csv(RESULTS / "simulation_trials.csv", keep_default_na=False)
    checks = {}
    for name in ["null", "threshold", "stress_null", "stress_threshold"]:
        d = trials[trials.scenario == name]
        if len(d) != 1000 or d.trial.nunique() != 1000:
            raise RuntimeError(f"Need 1,000 distinct committed trials: {name}")
        metric = "rejected" if name.endswith("null") else "covers_true"
        rate = float(d[metric].mean())
        lo, hi = (0.036, 0.064) if metric == "rejected" else (0.936, 0.964)
        if not lo <= rate <= hi:
            raise RuntimeError(f"Simulation acceptance check failed: {name}: {rate}")
        checks[name] = {"metric": metric, "rate": rate, "pass": True}
    return {"checkpoint": PRE_ANALYSIS_COMMIT, "evidence_sha256": hashes,
            "checks": checks, "historical_preregistration_verified": False,
            "scope": "continuation only; inherited High simulation"}


if __name__ == "__main__":
    audit = require_gate()
    (RESULTS / "gate_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    save_result("results_gate", audit)
    print("Continuation gate passed. Historical ordering remains unverified.")
