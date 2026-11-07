"""
Baseline re-anchoring sensitivity (decision item for the manuscript).

The main model sets the non-crisis OOP burden to 6% of income in every year
(BASE_OOP_FRACTION). GLSS7 gives a weighted mean of 0.75% of household
expenditure. This script re-runs the three scenarios with the baseline set to
0.75%, leaving every other parameter unchanged, so the authors can see how much
the headline numbers depend on that choice. Income and expenditure are not the
same denominator, so 0.75% is an approximation.
"""
import os, io, contextlib
os.makedirs("outputs", exist_ok=True)
import numpy as np, pandas as pd
with contextlib.redirect_stdout(io.StringIO()):
    import simulation as S          # runs the main model once, silently

rows = []
for label, base in [("main case (6%)", 0.06), ("re-anchored to GLSS7 (0.75%)", 0.0075)]:
    S.BASE_OOP_FRACTION = base
    for name, params in S.SCENARIOS.items():
        seed = 20260814 + int(__import__("hashlib").md5(name.encode()).hexdigest(), 16) % 100000
        res = S.run_scenario(params, seed=seed)
        burden26 = res["annual_oop_pct"][0] * 100
        burden51 = res["annual_oop_pct"][25] * 100
        final = res["annual_oop_pct"][-1] * 100
        rows.append({
            "baseline": label, "scenario": name,
            "mean_2026_pct": burden26.mean(), "mean_2051_pct": burden51.mean(),
            "median_2051_pct": np.median(burden51),
            "p90_2051_pct": np.percentile(burden51, 90),
            "share_debt_events_by_50": ((res["cumulative_debt_events"] >= 1).mean() * 100),
            "mean_debt_events": res["cumulative_debt_events"].mean(),
            "share_over_20pct_2051": (burden51 > 20).mean() * 100,
        })
S.BASE_OOP_FRACTION = 0.06
df = pd.DataFrame(rows)
df.to_csv("outputs/reanchor_sensitivity.csv", index=False)
print(df.round(2).to_string(index=False))
