"""
Runs every v4 analysis and writes outputs to outputs/v4/ and figures to figures/.
Usage:  python analysis_v4.py
Every number in the revised manuscript is read from outputs/v4/key_numbers.json, so the text
cannot drift from the run.
"""
import json
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

import model_v4 as M

OUT = os.path.join("outputs", "v4")
FIG = "figures"
os.makedirs(OUT, exist_ok=True)
os.makedirs(FIG, exist_ok=True)
KEY = {}
CHE_GLSS = 1.08          # GLSS7 CHE incidence at 10% of expenditure (%)
SC = list(M.SCENARIOS)
SCL = {k: M.SCENARIOS[k]["label"] for k in SC}

# ---------------------------------------------------------------- 1. main runs (36 years, first 26 = primary horizon)
runs36 = {(c, s): M.run_config(c, s, years=M.YEARS_EXTENDED) for c in M.CONFIGS for s in SC}

rows = []
for (c, s), r in runs36.items():
    r26 = {"burden": r["burden"][:26], "crisis": r["crisis"][:26], "debt_by_end": r["debt_by_end"]}
    # debt events by 2051 need the first 26 years only
    r26["debt_by_end"] = (((r["burden"][:26] - M.LIQUIDITY_BUFFER) > 0.15) & r["crisis"][:26]).sum(axis=0)
    d = M.summarise(r26)
    d.update({"config": c, "scenario": s})
    rows.append(d)
summary = pd.DataFrame(rows)
summary.to_csv(os.path.join(OUT, "summary_primary_horizon.csv"), index=False)

paths = []
for (c, s), r in runs36.items():
    m = r["burden"].mean(axis=1) * 100
    p10 = np.percentile(r["burden"], 10, axis=1) * 100
    p90 = np.percentile(r["burden"], 90, axis=1) * 100
    share10 = (r["burden"] > 0.10).mean(axis=1) * 100
    for t in range(M.YEARS_EXTENDED):
        paths.append({"config": c, "scenario": s, "year": 2026 + t, "age": 25 + t,
                      "mean": m[t], "p10": p10[t], "p90": p90[t], "share_over_10": share10[t]})
paths = pd.DataFrame(paths)
paths.to_csv(os.path.join(OUT, "annual_paths_36y.csv"), index=False)

def pick(c, s, col, year):
    return float(paths[(paths.config == c) & (paths.scenario == s) & (paths.year == year)][col].iloc[0])

for c in M.CONFIGS:
    for s in SC:
        KEY[f"{c}.{s}.mean2026"] = pick(c, s, "mean", 2026)
        KEY[f"{c}.{s}.mean2051"] = pick(c, s, "mean", 2051)
        KEY[f"{c}.{s}.mean2061"] = pick(c, s, "mean", 2061)
for c in M.CONFIGS:
    for s in SC:
        row = summary[(summary.config == c) & (summary.scenario == s)].iloc[0]
        for col in ["median_end", "p10_end", "p25_end", "p75_end", "p90_end", "share_over_10_end",
                    "share_over_20_end", "share_che10_year1", "p_any_debt_event_by_50", "mean_debt_events_by_50"]:
            KEY[f"{c}.{s}.{col}"] = float(row[col])

# ---------------------------------------------------------------- 2. validation against GLSS7 CHE incidence (year 1)
val = []
for c in M.CONFIGS:
    for s in SC:
        val.append({"config": c, "scenario": s,
                    "model_share_over_10pct_2026": pick(c, s, "share_over_10", 2026),
                    "glss7_che10_incidence": CHE_GLSS})
pd.DataFrame(val).to_csv(os.path.join(OUT, "validation_year1_che10.csv"), index=False)
KEY["validation.primary.year1_che10"] = pick("primary", "status_quo", "share_over_10", 2026)
KEY["validation.upper.year1_che10"] = pick("upper", "status_quo", "share_over_10", 2026)

# Hazard sensitivity on the primary configuration: can any annual hazard reproduce GLSS7 incidence in year 1?
haz = []
for p in [0.0108, 0.04, 0.08, 0.15]:
    r = M.run(M.SCENARIOS["status_quo"], M.CONFIGS["primary"]["base"], M.CONFIGS["primary"]["floor"],
              years=36, seed=M.seed_for("status_quo"), p_crisis_override=p)
    b = r["burden"] * 100
    haz.append({"p_health_crisis": p, "share_over_10_year1": (b[0] > 10).mean() * 100,
                "mean_2051": b[25].mean(), "p90_2051": np.percentile(b[25], 90),
                "share_over_20_2051": (b[25] > 20).mean() * 100})
haz = pd.DataFrame(haz)
haz.to_csv(os.path.join(OUT, "hazard_sensitivity_primary.csv"), index=False)
KEY["haz.max_year1_share_over10"] = float(haz.share_over_10_year1.max())

# ---------------------------------------------------------------- 3. debt-trigger grid (primary, status quo, 26 years)
grid = []
rsq = runs36[("primary", "status_quo")]
bsq, csq = rsq["burden"][:26], rsq["crisis"][:26]
for buf in [0.5, 1.0, 2.0, 3.0]:
    for thr in [10, 15, 20, 25]:
        ev = (((bsq - buf / 12) > thr / 100) & csq).sum(axis=0)
        grid.append({"buffer_months": buf, "threshold_pp": thr,
                     "mean_debt_events": ev.mean(), "p_at_least_one": (ev >= 1).mean() * 100})
grid = pd.DataFrame(grid)
grid.to_csv(os.path.join(OUT, "debt_grid_primary.csv"), index=False)
KEY["debt.base"] = float(grid[(grid.buffer_months == 1.0) & (grid.threshold_pp == 15)].p_at_least_one.iloc[0])
KEY["debt.min"] = float(grid.p_at_least_one.min())
KEY["debt.max"] = float(grid.p_at_least_one.max())

# ---------------------------------------------------------------- 4. one-at-a-time sensitivity, common random numbers
N_OAT = 10_000
BASE_OAT = dict(base=None)

def oat_outcome(config, params_override, sev_high=7.0, base=None):
    cfg = M.CONFIGS[config]
    b = cfg["base"] if base is None else base
    p = dict(M.SCENARIOS["status_quo"]); p.update(params_override)
    r = M.run(p, b, cfg["floor"], n=N_OAT, years=26, seed=M.seed_for("status_quo"),
              severity=(3.0, sev_high), wage=p.get("wage", M.WAGE_CAGR))
    return r["burden"][25].mean() * 100

OAT_RANGES = {
    "primary": {
        "base": ("Baseline non-crisis OOP share (0.5% to 1.0%)", (0.005, 0.010)),
        "p_health_crisis": ("Catastrophic-event probability (4% to 15%)", (0.04, 0.15)),
        "sev_high": ("Severity multiplier, upper bound (4x to 10x)", (4.0, 10.0)),
        "p_shock_year": ("Currency-shock frequency (6% to 25% per year)", (0.06, 0.25)),
        "import_premium_shock": ("Import cost pass-through in shock years (2% to 12%)", (0.02, 0.12)),
        "wage": ("Nominal wage growth (8% to 13%)", (0.08, 0.13)),
        "oop_share_of_health": ("OOP share of health expenditure (20% to 32%)", (0.20, 0.32)),
    },
    "upper": {
        "base": ("Baseline non-crisis OOP share (3% to 10%)", (0.03, 0.10)),
        "p_health_crisis": ("Catastrophic-event probability (4% to 15%)", (0.04, 0.15)),
        "sev_high": ("Severity multiplier, upper bound (4x to 10x)", (4.0, 10.0)),
        "p_shock_year": ("Currency-shock frequency (6% to 25% per year)", (0.06, 0.25)),
        "import_premium_shock": ("Import cost pass-through in shock years (2% to 12%)", (0.02, 0.12)),
        "wage": ("Nominal wage growth (8% to 13%)", (0.08, 0.13)),
        "oop_share_of_health": ("OOP share of health expenditure (20% to 32%)", (0.20, 0.32)),
    },
}

def apply(cfg_key, pname, value):
    """Map a sensitivity parameter to the model. oop_share_of_health cancels out of the formula, so it is
    passed through but has no effect (structural zero), which is reported as such."""
    if pname == "base":
        return dict(), value
    if pname == "sev_high":
        return dict(), None
    if pname == "oop_share_of_health":
        return dict(), None
    if pname == "wage":
        return dict(wage=value), None
    return {pname: value}, None

tornado = []
for c in ["primary", "upper"]:
    base_mean = oat_outcome(c, {})
    for pname, (label, (lo, hi)) in OAT_RANGES[c].items():
        out = []
        for v in (lo, hi):
            ov, base_override = apply(c, pname, v)
            if pname == "sev_high":
                out.append(oat_outcome(c, {}, sev_high=v))
            elif pname == "oop_share_of_health":
                out.append(oat_outcome(c, {}))
            else:
                out.append(oat_outcome(c, ov, base=base_override))
        tornado.append({"config": c, "parameter": pname, "label": label, "low_value": lo, "high_value": hi,
                        "mean2051_at_low": out[0], "mean2051_at_high": out[1],
                        "swing_pp": abs(out[1] - out[0]), "baseline_mean2051": base_mean})
tornado = pd.DataFrame(tornado).sort_values(["config", "swing_pp"], ascending=[True, True])
tornado.to_csv(os.path.join(OUT, "tornado_crn.csv"), index=False)
for c in ["primary", "upper"]:
    t = tornado[tornado.config == c]
    KEY[f"tornado.{c}.baseline"] = float(t.baseline_mean2051.iloc[0])
    for _, r in t.iterrows():
        KEY[f"tornado.{c}.{r.parameter}.swing"] = float(r.swing_pp)

# ---------------------------------------------------------------- 5. probabilistic sensitivity (300 joint draws)
PSA_RANGES = {
    "primary": {"base": (0.005, 0.010), "wage": (0.08, 0.13), "p_shock_year": (0.06, 0.25),
                "import_premium_shock": (0.02, 0.12), "p_health_crisis": (0.04, 0.15), "sev_high": (4.0, 10.0)},
    "upper": {"base": (0.03, 0.10), "wage": (0.08, 0.13), "p_shock_year": (0.06, 0.25),
              "import_premium_shock": (0.02, 0.12), "p_health_crisis": (0.04, 0.15), "sev_high": (4.0, 10.0)},
}
psa_summary = {}
psa_all = {}
for c in ["primary", "upper"]:
    draw_rng = np.random.default_rng(2026)
    recs = []
    for k in range(300):
        d = {p: draw_rng.uniform(lo, hi) for p, (lo, hi) in PSA_RANGES[c].items()}
        p = dict(M.SCENARIOS["status_quo"])
        p.update(p_shock_year=d["p_shock_year"], import_premium_shock=d["import_premium_shock"],
                 p_health_crisis=d["p_health_crisis"])
        p["wage"] = d["wage"]
        r = M.run(p, d["base"], M.CONFIGS[c]["floor"], n=2000, years=26, seed=3000 + k,
                  severity=(3.0, d["sev_high"]), wage=d["wage"])
        recs.append({**d, "outcome_2051_pct": r["burden"][25].mean() * 100})
    df = pd.DataFrame(recs)
    psa_all[c] = df
    df.to_csv(os.path.join(OUT, f"psa_draws_{c}.csv"), index=False)
    y = df.outcome_2051_pct
    rho = {p: float(spearmanr(df[p], y).correlation) for p in PSA_RANGES[c]}
    psa_summary[c] = dict(mean=y.mean(), median=y.median(), p10=y.quantile(0.1), p90=y.quantile(0.9),
                          share_over_20=(y > 20).mean() * 100, rho=rho)
    KEY[f"psa.{c}.mean"] = float(y.mean()); KEY[f"psa.{c}.median"] = float(y.median())
    KEY[f"psa.{c}.p10"] = float(y.quantile(0.1)); KEY[f"psa.{c}.p90"] = float(y.quantile(0.9))
    KEY[f"psa.{c}.share_over_20"] = float((y > 20).mean() * 100)
    for p, v in rho.items():
        KEY[f"psa.{c}.rho.{p}"] = v
with open(os.path.join(OUT, "psa_summary.json"), "w") as f:
    json.dump(psa_summary, f, indent=2, default=float)

# ---------------------------------------------------------------- 6. key numbers for the manuscript
KEY["oop_share_swing_common_seed"] = float(tornado[(tornado.config == "primary") & (tornado.parameter == "oop_share_of_health")].swing_pp.iloc[0])
with open(os.path.join(OUT, "key_numbers.json"), "w") as f:
    json.dump(KEY, f, indent=2, default=float)

# ---------------------------------------------------------------- 7. figures
colour = {"status_quo": "#B3541E", "reform": "#1F7A5A", "shock_heavy": "#7A1F2B"}

def path_plot(ax, config, years_to, style, label_suffix):
    for s in SC:
        sub = paths[(paths.config == config) & (paths.scenario == s) & (paths.year <= 2026 + years_to - 1)]
        ax.plot(sub.year, sub["mean"], style, color=colour[s], lw=2, label=f"{SCL[s]}{label_suffix}")

# Figure 1: mean path 2026-2051, primary (solid) and upper bound (dashed)
fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
path_plot(ax, "primary", 26, "-", " (GLSS7 baseline)")
path_plot(ax, "upper", 26, "--", " (6% upper bound)")
ax.axhline(20, color="grey", ls=":", lw=1)
ax.text(2027, 20.8, "20% catastrophic-expenditure threshold", fontsize=8, color="grey")
ax.set_xlabel("Year"); ax.set_ylabel("Mean household OOP burden (% of income)")
ax.set_title("Figure 1. Projected mean household OOP burden, Ghana Gen Z cohort, 2026-2051", fontsize=10, loc="left")
ax.legend(fontsize=7, frameon=False); ax.grid(axis="y", color="#e5e5e5")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure1_paths_2026_2051.png")); plt.close(fig)

# Figure 2: distribution of 2051 burden (primary), box plot per scenario
fig, ax = plt.subplots(figsize=(7.5, 5), dpi=200)
data = [runs36[("primary", s)]["burden"][25] * 100 for s in SC]
bp = ax.boxplot(data, whis=(10, 90), showfliers=False, patch_artist=True)
for patch, s in zip(bp["boxes"], SC):
    patch.set_facecolor(colour[s]); patch.set_alpha(0.4)
ax.axhline(20, color="grey", ls=":", lw=1)
ax.set_xticks(range(1, 4)); ax.set_xticklabels([SCL[s] for s in SC], fontsize=8)
ax.set_ylabel("Household OOP burden in 2051 (% of income)")
ax.set_title("Figure 2. Distribution of 2051 burden, GLSS7 baseline (whiskers: 10th-90th percentile)", fontsize=9.5, loc="left")
ax.grid(axis="y", color="#e5e5e5")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure2_distribution_2051.png")); plt.close(fig)

# Figure 6: extended paths to 2061 (primary solid; upper dashed)
fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
path_plot(ax, "primary", 36, "-", " (GLSS7 baseline)")
path_plot(ax, "upper", 36, "--", " (6% upper bound)")
ax.axhline(20, color="grey", ls=":", lw=1)
ax.axvline(2051, color="grey", ls=":", lw=0.8); ax.text(2051.3, 1, "age 50", fontsize=7, color="grey")
ax.set_xlabel("Year (age 25 in 2026, age 60 in 2061)"); ax.set_ylabel("Mean household OOP burden (% of income)")
ax.set_title("Figure 6. Extended projection through age 60 (2026-2061)", fontsize=10, loc="left")
ax.legend(fontsize=7, frameon=False); ax.grid(axis="y", color="#e5e5e5")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure6_extended_2061.png")); plt.close(fig)

# Figures 7-8: health share of household income (status quo across ages; scenarios at age 60)
fig, ax = plt.subplots(figsize=(6.5, 4.5), dpi=200)
ages = ["Age 25 (2026)", "Age 50 (2051)", "Age 60 (2061)"]
vals = [pick("primary", "status_quo", "mean", y) for y in (2026, 2051, 2061)]
ax.bar(ages, vals, color="#B3541E", width=0.5)
ax.bar(ages, [100 - v for v in vals], bottom=vals, color="#dfd6c8", width=0.5)
for i, v in enumerate(vals):
    ax.text(i, v + 2, f"{v:.1f}%", ha="center", fontsize=9)
ax.set_ylabel("Share of household income (%)"); ax.set_ylim(0, 105)
ax.set_title("Figure 7. Health (OOP) share of income, status quo, GLSS7 baseline", fontsize=9.5, loc="left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure7_budget_status_quo.png")); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4.5), dpi=200)
v60 = [pick("primary", s, "mean", 2061) for s in SC]
ax.bar([SCL[s] for s in SC], v60, color=[colour[s] for s in SC], width=0.5)
ax.bar([SCL[s] for s in SC], [100 - v for v in v60], bottom=v60, color="#dfd6c8", width=0.5)
for i, v in enumerate(v60):
    ax.text(i, v + 2, f"{v:.1f}%", ha="center", fontsize=9)
ax.set_ylim(0, 105); ax.set_ylabel("Share of household income (%)"); ax.tick_params(axis="x", labelsize=8)
ax.set_title("Figure 8. Health share of household income at age 60 (2061), by scenario", fontsize=9.5, loc="left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure8_budget_age60.png")); plt.close(fig)

# Figure 11: tornado (CRN), primary
t = tornado[tornado.config == "primary"].sort_values("swing_pp")
fig, ax = plt.subplots(figsize=(8.5, 5), dpi=200)
y = np.arange(len(t))
left = np.minimum(t.mean2051_at_low, t.mean2051_at_high)
ax.barh(y, np.abs(t.mean2051_at_high - t.mean2051_at_low), left=left, color="#B3541E", alpha=0.75, height=0.55)
ax.axvline(t.baseline_mean2051.iloc[0], color="#333", ls="--", lw=1)
ax.set_yticks(y); ax.set_yticklabels(t.label, fontsize=7.5)
ax.set_xlabel("Mean household OOP burden in 2051 (% of income)")
ax.set_title("Figure 11. One-at-a-time sensitivity, GLSS7 baseline (common random numbers)", fontsize=9.5, loc="left")
ax.grid(axis="x", color="#e5e5e5")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure11_tornado_primary.png")); plt.close(fig)

# Figure 12: PSA histogram, primary
fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=200)
ax.hist(psa_all["primary"].outcome_2051_pct, bins=30, color="#B3541E", alpha=0.8)
ax.axvline(20, color="grey", ls=":"); ax.axvline(psa_summary["primary"]["median"], color="#1F7A5A", label="median")
ax.set_xlabel("Mean household OOP burden in 2051 (% of income)"); ax.set_ylabel("Joint parameter draws")
ax.legend(fontsize=8, frameon=False)
ax.set_title("Figure 12. Probabilistic sensitivity, GLSS7 baseline (300 joint draws)", fontsize=9.5, loc="left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "figure12_psa_primary.png")); plt.close(fig)

print("v4 analysis complete. Key numbers:")
for k in ["primary.status_quo.mean2051", "primary.reform.mean2051", "primary.shock_heavy.mean2051",
          "upper.status_quo.mean2051", "validation.primary.year1_che10", "debt.base", "psa.primary.median",
          "oop_share_swing_common_seed"]:
    print(f"  {k}: {KEY[k]:.3f}")
