# Stages 0 and 7: Decisions and reproducibility (Sabrina)

**Status: done (13 Nov 2026), apart from two team actions listed at the end.** Prepared by Nyo on Sabrina's behalf from the guideline (§10 and §15), `decisions.md` and every team member's submission. **Sabrina: please read it, check it and change anything you disagree with.**

---

## Stage 0: Decisions

Goal (guideline §10): every rule fixed and committed before any outcome is seen.

| Task | Status | Where |
|---|---|---|
| 1. `decisions.md` in `docs/` | ✅ Done | `docs/decisions.md`. Lines 1–174 are byte-identical to the 9 Nov version; changes are only added under "Changes" |
| 2. Commit "Stage 0 decisions (before any scoring)" | ⚠️ Not possible any more | The team GitHub repository holds only the EDA scripts. The file was first committed on 11 Nov in Lin's local checkpoint (`7341120`), after scoring existed. This is recorded honestly under "Changes" (13 Nov, item 2) |
| 3. Schofield check | ✅ Done | **Opt-in confirmed**: Schofield (2015), Ch. 4, pp. 65–67, Table 4.1. Recorded under "Changes" (13 Nov, item 1) |
| 4. Javed's regression spec check (§11) | ✅ Done by Ahmad Jawid on 10 Nov | `README_P6.md` §2 |
| 5. `log_test` in `src/pipeline_lib.py` | ✅ Done | Next to `save_result`; used by every stage from 3 onwards |

### The Schofield check in one paragraph

The thesis says households joined the trial on an opt-in basis. The dynamic-tariff (ToU) group was then recruited "again on an opt-in basis", and households that did not join became the flat-rate (Std) group. The planned equal split was not reached because of this. Table 4.1 gives 1,119 dToU and 4,417 non-ToU households at the start. So assignment was **not random**, and `decisions.md` §2 stands: results apply to households likely to sign up, and the 2012 comparison is evidence of comparability, not proof. The page numbers come from the printed footers of the online PDF; check them against the PDF before citing.

---

## Stage 7: Reproducibility

Goal (guideline §15): someone clones the repository, runs one command and gets every figure and number.

| Task | Status | Where |
|---|---|---|
| 1. `run_all.py` runs every script in order and stops on the first error | ✅ Done | `run_all.py`. Covers Stages 2–6, the write-up and the EDA figures. Stage 4 reuses its committed results (the simulation takes an hour) and the gate checks them |
| EDA scripts and how to rerun them | ✅ Done | `eda/profile_households.py` and `eda/make_figures.py`, copied from the team GitHub repository. `make_figures.py` runs inside `run_all.py`; the README says how to rerun the slow first step |
| 2. Pinned `requirements.txt` and the Python version in the README | ✅ Done | `requirements.txt` (pandas, numpy, scipy, statsmodels, matplotlib, openpyxl, exact versions), `requirements-lock.txt` (all packages), Python 3.12 |
| 3. Seeds listed in the README | ✅ Done | README → "Random seeds". All are 2013; cross-validation has none |
| 4. `DATA_CARD.md` | ✅ Done | Source and link, licence, what each raw file holds, every cleaning step with its count, the 8 known limitations, and personal data |
| 5. README | ✅ Done | What the project is, how to get the data, install, run, run time, which script makes which figure, where the numbers are |

### Fresh-clone check (13 Nov)

A fresh clone of commit `71b64d0`, run with `H2013.npy` and `Tariffs.xlsx`, went through every step of `run_all.py` except the two regression scripts. Those need statsmodels, which this machine doesn't have.

- **Result:** every number in `results/results.json` matches the committed file. The largest relative difference is 4 × 10⁻¹⁴, which is floating-point rounding from slightly newer numpy/scipy versions than the pinned ones. The decision and all reported numbers are unchanged.
- **Run time:** 103 seconds on 2 cores.
- **Fix made:** `results/tests_summary.txt` had been saved from a check run. It is now Arpan's original, which matches the fresh run.

---

## Still to do (team)

1. **Lin's fresh-clone test** (guideline §15, Lin's steps). On a laptop with the pinned packages, clone, run `python run_all.py`, then `python scripts/verify_reproduction.py`. "Done when" requires an exact match, including the two regression scripts.
2. **Push to GitHub.** Push the `team-integrated` branch to `SaniahKayenat/Megamind` and open a pull request. Keep the hidden `.git` folder, because the gate needs commit `7341120`.

Sabrina's report and presentation parts (Stages 8–9) are separate: report section 1 (question and decision), section 7 (ethics) and section 8 (conclusion, with Lin), and slides 1–2. `DATA_CARD.md` and the Schofield check above give most of the ethics section.
