"""Lin's fresh-local-clone test, with a separately created clean Python environment.

Run after committing the working project:
python scripts/verify_reproduction.py --python /path/to/clean/env/bin/python

The script never downloads raw data or installs packages. It copies only the supplied
prepared matrix and tariff workbook, runs the whole prepared route, and compares exact
hashes with the committed expected outputs. Logs and SVG timestamps are not targets.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--python",required=True,help="Python in a clean environment with pinned requirements")
    args=ap.parse_args()
    executable=Path(args.python).absolute()
    if not executable.exists(): ap.error("Python executable not found")
    # Query sys.prefix from the interpreter. Resolving a venv's Python symlink would
    # point back to the base interpreter and lose the environment identity.
    info=json.loads(subprocess.check_output([str(executable),"-c",
        "import sys,json;print(json.dumps({'prefix':sys.prefix,'base':sys.base_prefix,'version':sys.version}))"],text=True))
    cfg=Path(info["prefix"])/"pyvenv.cfg"
    if info["prefix"]==info["base"] or not cfg.exists() or "include-system-site-packages = false" not in cfg.read_text().lower():
        ap.error("Use a clean virtual environment without inherited system packages")
    baseline=json.loads((ROOT/"docs/expected_output_hashes.json").read_text())
    commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    (ROOT/"tmp").mkdir(exist_ok=True)
    destination=Path(tempfile.mkdtemp(prefix="fresh-clone-",dir=ROOT/"tmp"))/"project"
    subprocess.run(["git","clone","--no-hardlinks",str(ROOT),str(destination)],check=True)
    for relative in ["data/interim/H2013.npy","data/raw/Tariffs.xlsx"]:
        target=destination/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,target)
    started=datetime.now(timezone.utc).isoformat()
    subprocess.run([str(executable),"run_all.py"],cwd=destination,check=True)
    comparisons={}
    for relative,expected in baseline.items():
        actual=hashlib.sha256((destination/relative).read_bytes()).hexdigest()
        comparisons[relative]={"expected_sha256":expected,"actual_sha256":actual,"exact_match":actual==expected}
    passed=all(row["exact_match"] for row in comparisons.values())
    receipt={"status":"passed" if passed else "failed","source_commit":commit,
             "scope":"fresh local clone, clean Python environment, supplied prepared matrix and frozen calibration",
             "python":info["version"],"started_utc":started,
             "finished_utc":datetime.now(timezone.utc).isoformat(),
             "checked_outputs":comparisons,"raw_download_reproduction":False,
             "original_historical_git_order_verified":False}
    (ROOT/"results/reproducibility.json").write_text(json.dumps(receipt,indent=2)+"\n")
    table="\n".join(f"| `{p}` | {'Exact match' if r['exact_match'] else 'DIFFERENT'} |" for p,r in comparisons.items())
    report=f"""# Reproducibility check

**Status: {receipt['status']}.** A fresh local clone at commit `{commit}` ran
`python run_all.py` in a separate clean environment with the pinned packages.
The virtual environment did not inherit system packages. The supplied prepared matrix
and tariff workbook were copied as external inputs, with frozen Stage 4 calibration
already committed. This tests Lin's complete prepared-input route.

| Output | Comparison |
|---|---|
{table}

The result dictionary comparison is byte-for-byte, stronger than checking rounded
report values. Main bootstrap draws and all empirical coverage-trial records are also
checked exactly. Tests are append-only, so execution timestamps and commit labels are
not expected to match. SVG metadata timestamps are not a numerical target.

This does **not** establish a fresh raw-download reproduction of the full team project:
original household CSVs and EDA scripts were not supplied, Nyo's original 4,000 trials
were audited rather than regenerated, and historical preregistration cannot be proved.
The original independent raw-CSV hand check needs those files. The supplied reading
export's arithmetic and raw-writer edge cases have separate automated tests.

Machine-readable evidence: `results/reproducibility.json`. The clone is retained under
`tmp/` for inspection and is excluded from Git. No remote repository was changed.
"""
    (ROOT/"reports/REPRODUCIBILITY.md").write_text(report)
    print(report)
    if not passed: raise SystemExit("Reproduction differs. Preserve both runs and investigate.")


if __name__=="__main__": main()
