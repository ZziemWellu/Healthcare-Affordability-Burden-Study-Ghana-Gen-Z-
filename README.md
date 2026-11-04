# Healthcare Affordability Burden Study: Ghana's Generation Z

Code, outputs and manuscript for **"Projecting the Healthcare Affordability Gap: A Stochastic Stress-Test of Out-of-Pocket Healthcare Burden for Ghana's Generation Z Cohort, 2026–2061"** (Prempeh and Wellu).

> Status: the v4 manuscript is formatted for submission to *Health Economics Review*. It has **not** yet been submitted or peer reviewed.

## What the study does

1. **GLSS7 baseline.** Household out-of-pocket (OOP) health burden from GLSS7 (2016/17) microdata, n = 14,009 households: weighted mean 0.75% of household expenditure, median 0%.
2. **Stochastic stress test.** 10,000 simulated household trajectories, a cohort aged 25 in 2026, over 26 annual observations (2026–2051) and 36 in an extended run to age 60 (2061). Three scenarios: status quo, financing reform (Abuja target) and repeated currency shocks.
3. **Sensitivity.** One-at-a-time analysis with common random numbers, 300-draw probabilistic analysis, debt-trigger grid and hazard sensitivity.

The primary analysis is anchored to the GLSS7 baseline (0.75%). The v3 calibration (6% non-crisis burden) is kept as an upper bound.

### Key results (mean OOP burden, % of income, 2051)

| Scenario | Primary (GLSS7 0.75%) | Upper bound (6%) |
|---|---:|---:|
| Status quo | 2.5 | 19.6 |
| Financing reform | 0.7 | 5.7 |
| Repeated currency shocks | 10.5 (P90 19.8) | 64.7 |

All numbers come from `outputs/v4/key_numbers.json`.

## Repository contents

| Path | What it is |
|---|---|
| `model_v4.py` | The v4 model (used by every v4 analysis) |
| `analysis_v4.py` | v4 pipeline: primary and upper-bound runs, sensitivity, figures → `outputs/v4/`, `figures/` |
| `build_manuscript_v4.py` | Builds the submission copy, the review copy and the issue log from `outputs/v4` |
| `run_all.py` | Runs every model script in order |
| `simulation.py`, `extended_simulation.py`, `sensitivity_analysis.py`, `requirements_5_6_analysis.py`, `reconciliation_analysis.py`, `reanchor_sensitivity.py` | v3 scripts (6% baseline), kept for traceability → `outputs/` |
| `ghana_survey_toolkit.py` | GLSS7/AHIES extraction toolkit (needs the microdata) |
| `glss7_extraction_config.yaml` | Files, variables and definitions used for the GLSS7 statistics |
| `manuscript/submission/` | **Journal submission copy** for *Health Economics Review*: `Manuscript_HER_submission.docx` (numbered references, no review notes) and `Figure1.png`–`Figure7.png` |
| `manuscript/` | Review copy of the v4 manuscript (author-year references, embedded figures) and the issue log |
| `CODE_REVIEW.md` | Reproduction check of the v3 code (6 Oct 2026) |
| `SSRN_submission_draft.md` | Preprint submission text (v4) |
| `healthcare_affordability_gap_genz_ghana_revised.pdf` | **Superseded** v3 draft (6% baseline), kept for the record |

## Reproducing the results

```bash
git clone https://github.com/ZziemWellu/Healthcare-Affordability-Burden-Study-Ghana-Gen-Z-.git
cd Healthcare-Affordability-Burden-Study-Ghana-Gen-Z-
pip install -r requirements.txt
python run_all.py                # about 30 s; writes outputs/ and figures/
python build_manuscript_v4.py    # rebuilds the manuscript from outputs/v4
```

All runs are seeded. Re-running on 4 Nov 2026 (Python 3.13.4, Windows 10) reproduced every committed output byte for byte.

Figures 1, 2, 6, 7, 8, 11 and 12 come from the model. Figures 3–5, 9 and 10 and Table 3 come from the GLSS7 microdata and are not regenerated here.

## Data access

GLSS7 (2016/17) microdata belong to the Ghana Statistical Service and are available after registration from the [GSS microdata catalog (study 97)](https://microdata.statsghana.gov.gh/index.php/catalog/97) (reference DDI-GHA-GSS-GLSS7-2017-v1). The public data dictionary is on the [IHSN catalog](https://catalog.ihsn.org/catalog/7967). This repository does not redistribute any survey data. Do not commit `.dta`/`.sav` files.

## Citation

```
Prempeh, N. O. A., and Wellu, Z. P. (2026). Projecting the Healthcare Affordability Gap: A Stochastic
Stress-Test of Out-of-Pocket Healthcare Burden for Ghana's Generation Z Cohort, 2026–2061.
Manuscript in preparation. https://github.com/ZziemWellu/Healthcare-Affordability-Burden-Study-Ghana-Gen-Z-
```

## Authors

- **Nana Owusu Achiaw Prempeh** (corresponding), Department of Data Science, Academic City University College, Accra. GitHub [@steveprempeh23](https://github.com/steveprempeh23)
- **Ziem P. Wellu** (co-corresponding), Department of Computer Science, University of Ghana, Accra. ORCID [0009-0004-5808-2675](https://orcid.org/0009-0004-5808-2675). GitHub [@ZziemWellu](https://github.com/ZziemWellu)

## Licence

MIT (see `LICENSE`).
