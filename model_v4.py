"""
Version 4 of the Gen Z healthcare-affordability simulation (single source of truth).

Two configurations are run with identical equations and random-number order:

  PRIMARY (re-anchored):   baseline non-crisis OOP burden = 0.75% of income
                           (GLSS7 weighted mean of OOP burden as share of expenditure, 2016/17),
                           burden floor = 0% (GLSS7 weighted median is 0%).
  UPPER BOUND (paper v3):  baseline non-crisis OOP burden = 6% of income, burden floor = 1%.
                           This reproduces the v3 manuscript exactly.

Equations (per household i, year t, t = 0 is 2026):
  shock_it ~ Bernoulli(p_shock); inflation ~ N(mu_regime, sd_regime), clipped to [-2%, 65%]
  income index I_t = I_{t-1} * (1 + wage CAGR)
  health-cost index H_t = H_{t-1} * (1 + inflation + import premium)
  OOP share S_t = clip(S_{t-1} + drift, 10%, 55%), starting at 26%
  gap ratio G_t = H_t / I_t
  base burden B_it = base * S_t / 26% * G_t
  crisis_it ~ Bernoulli(p_crisis); severity M ~ U(3, 7)
  burden = B * M if crisis else B, clipped to [floor, 120%] of income
  debt event: crisis AND (burden - 1/12 of income) > 15 percentage points

Random numbers are drawn in the same order as the v3 code, so the upper-bound configuration
reproduces the v3 numbers exactly.
"""
import hashlib
import numpy as np

N_HOUSEHOLDS = 10_000
YEARS_PRIMARY = 26        # 2026-2051 inclusive (26 annual observations)
YEARS_EXTENDED = 36       # 2026-2061 inclusive (36 annual observations)
WAGE_CAGR = 0.109
OOP_SHARE_START = 0.26
LIQUIDITY_BUFFER = 1 / 12
CEILING = 1.20

CONFIGS = {
    "primary": dict(label="Primary: GLSS7 re-anchored (0.75% baseline)", base=0.0075, floor=0.0),
    "upper": dict(label="Upper bound: v3 calibration (6% baseline)", base=0.06, floor=0.01),
}

SCENARIOS = {
    "status_quo": dict(
        label="Status quo",
        p_shock_year=0.12,
        shock_inflation_mean=0.30, shock_inflation_sd=0.10,
        stable_inflation_mean=0.10, stable_inflation_sd=0.03,
        import_premium_shock=0.06, import_premium_stable=0.02,
        p_health_crisis=0.08, oop_share_drift=0.0),
    "reform": dict(
        label="Financing reform (Abuja target)",
        p_shock_year=0.12,
        shock_inflation_mean=0.30, shock_inflation_sd=0.10,
        stable_inflation_mean=0.10, stable_inflation_sd=0.03,
        import_premium_shock=0.03, import_premium_stable=0.01,
        p_health_crisis=0.064, oop_share_drift=-0.006),
    "shock_heavy": dict(
        label="Repeated currency shocks",
        p_shock_year=0.25,
        shock_inflation_mean=0.35, shock_inflation_sd=0.12,
        stable_inflation_mean=0.10, stable_inflation_sd=0.03,
        import_premium_shock=0.09, import_premium_stable=0.02,
        p_health_crisis=0.08, oop_share_drift=0.004),
}


def seed_for(scenario_name):
    """Deterministic per-scenario seed (same scheme as v3)."""
    return 20260814 + int(hashlib.md5(scenario_name.encode()).hexdigest(), 16) % 100000


def run(params, base, floor, n=N_HOUSEHOLDS, years=YEARS_PRIMARY, seed=None,
        p_crisis_override=None, severity=(3.0, 7.0), wage=WAGE_CAGR):
    """Returns dict with burden matrix (years x n, fraction of income) and debt-event counts."""
    rng = np.random.default_rng(seed)
    p_crisis = params["p_health_crisis"] if p_crisis_override is None else p_crisis_override
    inc = np.ones(n)
    hc = np.ones(n)
    share = np.full(n, OOP_SHARE_START)
    burden_all = np.zeros((years, n))
    crisis_all = np.zeros((years, n), dtype=bool)
    debt_counts = np.zeros(n, dtype=int)
    for t in range(years):
        shock = rng.random(n) < params["p_shock_year"]
        infl = np.where(
            shock,
            rng.normal(params["shock_inflation_mean"], params["shock_inflation_sd"], n),
            rng.normal(params["stable_inflation_mean"], params["stable_inflation_sd"], n),
        )
        infl = np.clip(infl, -0.02, 0.65)
        prem = np.where(shock, params["import_premium_shock"], params["import_premium_stable"])
        inc *= (1 + wage)
        hc *= (1 + infl + prem)
        share = np.clip(share + params["oop_share_drift"], 0.10, 0.55)
        gap = hc / inc
        crisis = rng.random(n) < p_crisis
        base_burden = base * share / OOP_SHARE_START * gap
        mult = rng.uniform(severity[0], severity[1], n)
        burden = np.where(crisis, base_burden * mult, base_burden)
        burden = np.clip(burden, floor, CEILING)
        burden_all[t] = burden
        crisis_all[t] = crisis
        debt_counts += (((burden - LIQUIDITY_BUFFER) > 0.15) & crisis).astype(int)
    return {"burden": burden_all, "crisis": crisis_all, "debt_by_end": debt_counts}


def run_config(config_key, scenario_key, years=YEARS_PRIMARY, n=N_HOUSEHOLDS, p_crisis=None):
    cfg = CONFIGS[config_key]
    return run(SCENARIOS[scenario_key], cfg["base"], cfg["floor"], n=n, years=years,
               seed=seed_for(scenario_key), p_crisis_override=p_crisis)


def summarise(res):
    """Headline statistics, in percent of income, at the end of the run."""
    b = res["burden"] * 100
    end = b[-1]
    return {
        "mean_2026": b[0].mean(),
        "mean_end": end.mean(),
        "median_end": np.median(end),
        "p10_end": np.percentile(end, 10),
        "p25_end": np.percentile(end, 25),
        "p75_end": np.percentile(end, 75),
        "p90_end": np.percentile(end, 90),
        "share_over_10_end": (end > 10).mean() * 100,
        "share_over_20_end": (end > 20).mean() * 100,
        "share_che10_year1": (b[0] > 10).mean() * 100,
        "p_any_crisis_by_50": (res["crisis"][:26].any(axis=0)).mean() * 100,
        "p_any_debt_event_by_50": (res["debt_by_end"] >= 1).mean() * 100,
        "mean_debt_events_by_50": res["debt_by_end"].mean(),
    }
