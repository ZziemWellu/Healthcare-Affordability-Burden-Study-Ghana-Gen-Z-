"""
Re-runs every model script in order and writes all outputs to ./outputs.
Usage:  python run_all.py
The GLSS7 extraction (ghana_survey_toolkit.py) needs the survey microdata, which is not
redistributed here, so it is not run by this script.
"""
import subprocess, sys, os
os.makedirs("outputs", exist_ok=True)
steps = [
    "simulation.py",                # main model: primary 2026-2051 results (Table 4, Figures 1-2)
    "extended_simulation.py",       # 2026-2061 results (Section 4.4, Figure 6)
    "reconciliation_analysis.py",   # Ghana-empirical calibration (Table 6)
    "requirements_5_6_analysis.py", # debt-trigger grid (Table 7) and probabilistic analysis (Table 8, Figure 12)
    "sensitivity_analysis.py",      # one-at-a-time tornado (Table 5, Figure 11), common random numbers
    "reanchor_sensitivity.py",      # baseline 6% vs GLSS7 0.75% (decision item)
    "analysis_v4.py",               # v4 pipeline: primary (GLSS7 baseline) and upper bound, all figures
]
for s in steps:
    print(f"\n=== {s} ===", flush=True)
    r = subprocess.run([sys.executable, s], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(f"{s} failed")
    print("ok")
print("\nAll model outputs written to ./outputs")
