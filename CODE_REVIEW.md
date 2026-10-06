# Code review and reproduction check

Repository: steveprempeh23/Healthcare-Affordability-Burden-Study-Ghana-Gen-Z- (public, MIT licence).
Reviewed on 6 October 2026, on Windows 10 with numpy 2.2.5, pandas 2.2.3, scipy 1.16.1, matplotlib 3.10.5.

## 1. Reproduction of the manuscript numbers

The model code reproduces the manuscript's simulation numbers, rounded to the manuscript's precision.

| Manuscript item | Manuscript value | Code output | Match |
|---|---|---|---|
| Table 4, status quo: mean 2026 / 2051 | 8.1 / 19.6 | 8.14 / 19.57 | yes |
| Table 4, status quo: median / P90 2051 | 14.1 / 30.9 | 14.13 / 30.89 | yes |
| Table 4, status quo: P(at least 1 catastrophic event) / mean debt events | 88.7 / 1.98 | 88.74 / 1.98 | yes |
| Table 4, reform: mean 2026 / 2051 | 7.6 / 5.7 | 7.58 / 5.73 | yes |
| Table 4, reform: P(at least 1 event) | 82.0 | 82.04 | yes |
| Table 4, shock-heavy: mean 2051 / median / P90 | 64.7 / 56.3 / 120.0 | 64.69 / 56.25 / 120.00 | yes |
| Section 4.4, age 60 (2061): status quo / reform / shock-heavy | 26.71 / 7.06 / 99.25 | 26.71 / 7.06 / 99.25 | yes |
| Table 6, Ghana-empirical calibration 2051 (status quo / reform / shock-heavy) | 15.6 / 4.7 / 60.9 | 15.55 / 4.68 / 60.93 | yes |
| Table 6, Ghana-empirical calibration 2061 | 22.2 / 5.8 / 97.8 | 22.17 / 5.78 / 97.81 | yes |
| Table 7, debt-trigger grid (16 cells; base 87.3, most conservative 51.7) | as printed | as printed | yes |
| Section 4.5, probabilistic analysis: mean / median / P10-P90 / share above 20% | 30.3 / 28.7 / 12.3-52.4 / 73.3 | 30.34 / 28.68 / 12.33-52.43 / 73.3 | yes |
| Table 8, Spearman rho (baseline OOP share, wage growth, shock frequency) | 0.65, -0.59, 0.49 | 0.648, -0.587, 0.486 | yes |
| Table 5, one-at-a-time swings (original seeds) | 0.4, 3.6, 5.5, 6.4, 22.4, 23.4, 25.0 | 0.36, 3.62, 5.52, 6.44, 22.40, 23.38, 24.97 | yes, but see issue 4 |
| Section 4.1, GLSS7 empirical statistics (0.75%, 1.08%, deciles, age and sex groups, literacy) | as printed | not runnable | cannot check (data not in repo) |
| Figures 1-2, 3-12 | as printed | no script in this repository produces them | cannot check |

## 2. Issues found (ranked)

1. **The baseline burden is not estimated from the survey data (critical).** `BASE_OOP_FRACTION = 0.06` is an author calibration. GLSS7 gives a mean of 0.75% of expenditure. Re-anchoring the baseline to 0.75% (`reanchor_sensitivity.py`) changes the central conclusion. The status-quo mean burden in 2051 falls to 2.5% (from 19.6%), the shock-heavy scenario falls to 10.5% (from 64.7%), and the catastrophic-threshold share of households in 2051 falls to 0.3% (from 22.7%). The paper's headline catastrophic-burden finding depends on this choice, and this must be disclosed or changed before submission.
2. **The period count does not match the manuscript text (major).** The code uses `N_YEARS = 26` (2026-2051 inclusive), and the extended run uses 36 periods (2026-2061). The manuscript says T = 25 and T = 35. The reported probabilities (88.7%, 82.0%) match 1-(1-p)^26, so the code's 26-period definition is the one that produced the numbers. The text must say 26 and 36 annual observations.
3. **The OOP-share parameter has no effect in the model (major).** The burden formula divides by `OOP_SHARE_OF_HEALTH_SPEND` and multiplies by the same share, so it cancels unless the share drifts. The 0.4-point swing in Table 5 and the rho of 0.02 in Table 8 are therefore Monte Carlo noise. That noise comes from giving each sensitivity arm a different random seed. The manuscript says this parameter has the "weakest evidentiary basis and smallest swing". The conclusion is right, but the reason given is wrong.
4. **Sensitivity arms use different random seeds (major).** The one-at-a-time analysis gives the low, high and baseline arms different seeds, so every swing includes noise. Common random numbers (one seed for all arms) fix this. With them, the OOP-share swing is exactly 0.00, and the other swings change slightly: severity 3.19 (paper 3.62), import pass-through 5.15 (5.52), catastrophic probability 6.79 (6.44), baseline OOP share 22.01 (22.40), shock frequency 23.01 (23.38), wage growth 25.20 (24.97). The top three parameters keep their ranking. This fix is in the reviewed copy.
5. **Classification conflicts with the results text (major).** The manuscript says the most influential parameters are the best grounded. But the two top-ranked parameters after wage growth, baseline OOP share and shock frequency, are both author calibrations (C). The 12% shock frequency is hard-coded and does not match the "about 4 episodes in 25 years" source, which gives 16%.
6. **Hard-coded paths (blocking for anyone else).** Every script writes to `/home/claude/arf_paper/`, so nothing runs on another machine as published. The reviewed copy writes to `./outputs`.
7. **Side effects on import (moderate).** `extended_simulation.py`, `reconciliation_analysis.py` and `requirements_5_6_analysis.py` import `simulation.py`, which runs the full model and writes files as soon as it is imported. Move the model into functions and put the runs under `if __name__ == "__main__":`.
8. **Two different sensitivity models (moderate).** `sensitivity_analysis.py` clips burden at 150% while the main model clips at 120%. It uses 5,000 households instead of 10,000 and has no OOP drift. Its baseline (19.7%) therefore differs slightly from the main model (19.6%). Use one model for every analysis.
9. **Duplicate file (minor).** `simulation (1).py` is identical to `simulation.py`. Delete it.
10. **GLSS7 extraction is not reproducible from this repository (blocking for Section 4.1).** `ghana_survey_toolkit.py` (1,078 lines) detects columns by name heuristics. It does not contain the variables the paper names (TOTHLTH, HHEXP_N, WTA_S, s1q3). The configuration used for the paper's Table 3 and Figures 3-10 is not in the repository. Commit that configuration, state the GLSS7 file names and versions, and include the output tables.
11. **No script generates the main figures (moderate).** Figures 1-2 and 6-12 are produced outside this repository. Add the plotting code.
12. **Documentation is out of date (minor).** The README says the code is "being prepared" and leaves status items unchecked, although the code is present. It also refers to a `src/` layout that does not exist. The SSRN draft abstract is an older version than the manuscript.
13. **Dependency specification (minor).** `requirements.txt` lists `seaborn`, `jupyter` and `pyyaml`, which the model code does not use. Pin the versions that produced the outputs.
14. **Submission status conflict (administrative).** The README says the manuscript is "submitted to a Springer journal (under review)". The planned journal is Health Economics Review. Confirm which is true before any change is made to the journal version.

## 3. Changes in the reviewed copy (`Prempeh_repro`)

- Output paths changed to `./outputs`.
- Sensitivity analysis uses common random numbers.
- `reanchor_sensitivity.py` added (baseline 6% vs 0.75%).
- `run_all.py` added to run every model script in order. Runs cleanly in full.

The original GitHub repository has not been changed. These changes are in a separate copy for the author to review.
