"""
Builds the revised manuscript (v4) and the issue log from outputs/v4/.
Every number in the text and tables is read from outputs/v4 at build time.
Highlighted [[...]] items are placeholders or items the authors must confirm.

Output: manuscript/Revised_manuscript_v4.docx, manuscript/Issue_log_v4.docx
"""
import json
import os
import re
import pandas as pd
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Inches, Pt

OUT = os.path.join("outputs", "v4")
FIG = "figures"
MS = "manuscript"
os.makedirs(MS, exist_ok=True)
K = json.load(open(os.path.join(OUT, "key_numbers.json")))
PSA = json.load(open(os.path.join(OUT, "psa_summary.json")))
S = pd.read_csv(os.path.join(OUT, "summary_primary_horizon.csv"))
T = pd.read_csv(os.path.join(OUT, "tornado_crn.csv"))
H = pd.read_csv(os.path.join(OUT, "hazard_sensitivity_primary.csv"))
G = pd.read_csv(os.path.join(OUT, "debt_grid_primary.csv"))
V = pd.read_csv(os.path.join(OUT, "validation_year1_che10.csv"))

def srow(c, s):
    return S[(S.config == c) & (S.scenario == s)].iloc[0]

def f1(x):
    return f"{x:.1f}"

def f2(x):
    return f"{x:.2f}"

P_SQ, P_RF, P_SH = srow("primary", "status_quo"), srow("primary", "reform"), srow("primary", "shock_heavy")
U_SQ, U_RF, U_SH = srow("upper", "status_quo"), srow("upper", "reform"), srow("upper", "shock_heavy")
SEV_NEEDED = 10.0 / 0.75          # crisis multiplier needed to push a 0.75% baseline to 10% of income
MAX_CRISIS_PRIMARY = 7 * 0.75     # largest crisis-year burden the primary model can produce in 2026 (%)

def tor(c, p):
    return T[(T.config == c) & (T.parameter == p)].iloc[0]

# ------------------------------------------------------------------ document helpers
CITE = re.compile(r"(\[\[.*?\]\])")

def rich(p, text, italic=False, bold=False, size=None):
    for tok in CITE.split(text):
        if not tok:
            continue
        if tok.startswith("[["):
            r = p.add_run("[" + tok[2:-2] + "]")
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        else:
            r = p.add_run(tok)
        r.italic = italic; r.bold = bold
        if size:
            r.font.size = Pt(size)

def build(blocks, path, banner=None):
    doc = Document()
    st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(1)
    if banner:
        rich(doc.add_paragraph(), banner, italic=True, size=9)
    for b in blocks:
        k = b[0]
        if k == "title": doc.add_heading(b[1], level=0)
        elif k == "h1": doc.add_heading(b[1], level=1)
        elif k == "h2": doc.add_heading(b[1], level=2)
        elif k == "p": rich(doc.add_paragraph(), b[1])
        elif k == "bullet": rich(doc.add_paragraph(style="List Bullet"), b[1])
        elif k == "eq": p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.4); rich(p, b[1])
        elif k == "fig":
            doc.add_picture(os.path.join(FIG, b[1]), width=Inches(b[2]))
            rich(doc.add_paragraph(), b[3], italic=True, size=9.5)
        elif k == "table":
            _, cap, header, rows = b
            rich(doc.add_paragraph(), cap, bold=True, size=10)
            t = doc.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
            for i, h in enumerate(header):
                rich(t.rows[0].cells[i].paragraphs[0], h, bold=True, size=9.5)
            for row in rows:
                cells = t.add_row().cells
                for i, v in enumerate(row):
                    rich(cells[i].paragraphs[0], str(v), size=9.5)
            doc.add_paragraph()
        elif k == "refs":
            doc.add_heading("References", level=1)
            for line in b[1]:
                rich(doc.add_paragraph(), line, size=10)
        else:
            raise ValueError(k)
    doc.save(path)
    print("wrote", path)

# ------------------------------------------------------------------ manuscript content
REFS = [
    "Akazili, James, John Gyapong, and Di McIntyre. 2011. “Who Pays for Health Care in Ghana?” International Journal for Equity in Health 10: 26. https://doi.org/10.1186/1475-9276-10-26.",
    "Akazili, James, John Ele-Ojo Ataguba, Edmund Wedam Kanmiki, John Gyapong, Osman Sankoh, Abraham Oduro, and Di McIntyre. 2017a. “Assessing the Impoverishment Effects of Out-of-Pocket Healthcare Payments Prior to the Uptake of the National Health Insurance Scheme in Ghana.” BMC International Health and Human Rights 17: 13. https://doi.org/10.1186/s12914-017-0121-7.",
    "Akazili, James, Diane McIntyre, Edmund W. Kanmiki, John Gyapong, Abraham Oduro, Osman Sankoh, and John E. Ataguba. 2017b. “Assessing the Catastrophic Effects of Out-of-Pocket Healthcare Payments Prior to the Uptake of a Nationwide Health Insurance Scheme in Ghana.” Global Health Action 10 (1): 1289735. https://doi.org/10.1080/16549716.2017.1289735.",
    "Ataguba, John E., and Grace A. Kabaniha. 2022. “Characterizing Key Misconceptions of Equity in Health Financing for Universal Health Coverage.” Health Policy and Planning 37 (7): 928–931. https://doi.org/10.1093/heapol/czac041.",
    "Bloomberg. 2022. “Ghana Inflation Exceeds 37% as Data Compilation Is Changed.” October 12, 2022. https://www.bloomberg.com/news/articles/2022-10-12/ghana-annual-inflation-at-37-2-as-data-compilation-is-changed.",
    "Fair Wages and Salaries Commission. 2025. “2026 National Daily Minimum Wage.” Accra: Government of Ghana.",
    "Finex Insights. 2025. “Ghana's Minimum Wage Growth: A Decade of Gradual Gains and Sudden Jumps (2015–2025).” August 19, 2025.",
    "Ghana Statistical Service. 2018. Ghana Living Standards Survey (GLSS VII) 2016-2017, version 01 (September 2018). Ref. GHA_2016_GLSS_v01_M. Accra: Ghana Statistical Service. https://microdata.statsghana.gov.gh/index.php/catalog/97.",
    "Okoroh, Juliet, and Sarpong Essoun. 2018. “Evaluating the Impact of the National Health Insurance Scheme of Ghana on Out-of-Pocket Expenditures: A Systematic Review.” BMC Health Services Research 18: 426. https://doi.org/10.1186/s12913-018-3249-9.",
    "Pharmexcil (Pharmaceuticals Export Promotion Council of India). 2020. Ghana Pharma Market & Regulatory Report. Hyderabad: Pharmexcil. https://pharmexcil.com/uploads/countryreports/Ghana_Market_Regulatory_report2020.pdf.",
    "Prempeh, Nana Owusu Achiaw, and Ziem P. Wellu. 2025. “An Analysis of Household Catastrophic Health Expenditure and Food Insecurity in Ghana.” medRxiv preprint. https://doi.org/10.1101/2025.03.31.25324988.",
    "Sataru, Fuseini, Kwame Twumasi-Ankrah, and Anthony Seddoh. 2022. “An Analysis of Catastrophic Out-of-Pocket Health Expenditures in Ghana.” Frontiers in Health Services 2. https://doi.org/10.3389/frhs.2022.706216.",
    "Trading Economics. 2026. “Ghana Inflation Rate.” Accessed August 2026. https://tradingeconomics.com/ghana/inflation-cpi.",
    "Wellu, Patrick Ziem, Adawu Redeemer, Michael Annor Peprah, Daniel Amakye, Emmanuel Prempeh Agyemang, Prince Peprah, and Williams Agyemang-Duah. 2026. “Catastrophic health expenditure and household food insecurity among older adults with health conditions in Ghana: a cross-sectional analysis.” BMC Public Health. Published 17 July 2026. https://doi.org/10.1186/s12889-026-28188-1. [[Crossref on 4 Nov 2026 lists no volume or article number yet; ADD them if assigned before submission]]",
    "WHO Regional Office for Africa. 2023. “Ghana: Universal Health Coverage/Communicable and Non-communicable Diseases” (country profile). Brazzaville: WHO Regional Office for Africa. https://www.afro.who.int/sites/default/files/2023-08/Ghana.pdf.",
    "World Bank. 2023. “Public Health Expenditure for Universal Health Coverage in Ghana.” Washington, DC: World Bank Group.",
    "World Bank. n.d. “Out-of-Pocket Expenditure (% of Current Health Expenditure) – Ghana.” World Bank Open Data. https://data.worldbank.org/indicator/SH.XPD.OOPC.CH.ZS?locations=GH.",
]

MANUSCRIPT = [
    ("title", "Projecting the Healthcare Affordability Gap: A Stochastic Stress-Test of Out-of-Pocket Healthcare Burden for Ghana's Generation Z Cohort, 2026–2061"),
    ("p", "Nana Owusu Achiaw Prempeh (corresponding author), Department of Data Science, Academic City University College, Accra, Ghana. nana.prempeh@acity.edu.gh"),
    ("p", "Ziem P. Wellu (co-corresponding author), Department of Computer Science, University of Ghana, Accra, Ghana. pzwellu@st.ug.edu.gh. ORCID: 0009-0004-5808-2675"),
        ("h1", "Abstract"),
    ("p", f"Ghana's National Health Insurance Scheme was designed to protect households from catastrophic out-of-pocket (OOP) healthcare costs, yet OOP payments still account for about 26 percent of current health expenditure nationally (World Bank, n.d.). This paper asks a generational question: if current trends in healthcare costs, wages and macroeconomic volatility persist, what OOP burden will Ghana's Generation Z cohort face around age 50? We combine two approaches. First, we compute household OOP burden from GLSS7 (2016/17) microdata (n = 14,009 households) and find a weighted mean of 0.75 percent of household expenditure, which is 0 percent at the median. Second, we run a stochastic stress-test simulation of 10,000 household trajectories under three scenarios (status quo, financing reform to the Abuja target, and repeated currency shocks). The primary analysis uses the GLSS7 baseline. Under this baseline, the status-quo mean burden in 2051 is {f1(P_SQ.mean_end)} percent of income, the financing-reform scenario is {f1(P_RF.mean_end)} percent, and repeated currency shocks reach {f1(P_SH.mean_end)} percent, with a 90th percentile of {f1(P_SH.p90_end)} percent. Only {f1(P_SQ.share_over_20_end)} percent of status-quo households exceed the 20 percent catastrophic-expenditure threshold in 2051, and risk is concentrated in the shock scenarios. A previous calibration that set the non-crisis burden at 6 percent of income produces materially higher burdens (status quo {f1(U_SQ.mean_end)} percent in 2051). We report it as an upper bound because the GLSS7 data do not support that baseline. The model does not reproduce the GLSS7 catastrophic-expenditure incidence in year one, and we report this as a limitation. Results are model-implied outcomes under stated assumptions, not forecasts for individual households."),
    ("p", "Keywords: catastrophic health expenditure; out-of-pocket payments; National Health Insurance Scheme; Ghana; generational projection; Monte Carlo simulation; GLSS7."),

    ("h1", "1. Introduction"),
    ("p", "Out-of-pocket payments remain a large share of health spending in Ghana, and catastrophic health expenditure (CHE) falls hardest on poorer households (Akazili et al. 2017a; Akazili et al. 2017b; Ataguba and Kabaniha 2022). Most of the CHE literature in Ghana is retrospective and cross-sectional. It describes the burden in a survey year and does not ask what a cohort will face as it ages. This paper projects the burden for a cohort of young adults, representative of Generation Z, to around age 50."),
    ("p", "Generation Z is used as an analytical cohort, not a homogeneous population. The primary simulation represents a household aged 25 in 2026, which corresponds to a 2001 birth year. It runs for 26 annual observations (2026–2051) and, in an extended analysis, for 36 annual observations (2026–2061, age 60)."),
    ("p", "A companion study by the same team analysed AHIES 2022 data on catastrophic expenditure and food insecurity among adults aged 50 and over with a health condition (Wellu et al. 2026; an earlier version was posted as Prempeh and Wellu 2025). That study is cross-sectional and covers a different population and outcome. The present paper is a forward projection built on GLSS7 (2016/17) and does not reuse the 2022 AHIES analysis."),
    ("p", "The paper makes three contributions. It shows what the GLSS7 microdata imply for the starting burden. It sets out a transparent stochastic model and classifies every parameter by its evidence. And it shows how strongly the generational conclusion depends on the baseline calibration, which we treat as the main decision in the analysis."),

    ("h1", "2. Literature Review"),
    ("h2", "2.1 Catastrophic health expenditure and NHIS in Ghana"),
    ("p", "The National Health Insurance Scheme was introduced in 2003 to reduce OOP payments. The pre-NHIS baseline, based on the 2005/06 Ghana Living Standards Survey, found that OOP payments increased poverty and were regressive across income deciles (Akazili et al. 2017a). A companion analysis from the same survey round estimated the share of households spending more than 20 percent of income on OOP care (Akazili et al. 2017b). Okoroh and Essoun (2018) reviewed NHIS impact studies and found that uninsured households paid substantially more out of pocket than insured households, while a meaningful minority of insured households still incurred catastrophic payments. OOP payments are the regressive component of Ghana's health financing (Akazili, Gyapong and McIntyre 2011); in their data, the poorest fifth of households bears 6.9 percent of OOP spending against 5.5 percent of income (Ataguba and Kabaniha 2022). Sataru, Twumasi-Ankrah and Seddoh (2022) analyse catastrophic OOP expenditure in Ghana using GLSS7 and find an incidence of 1.0 percent at the 10 percent threshold."),
    ("h2", "2.2 Financing gaps and macroeconomic volatility"),
    ("p", "Government health spending in Ghana has remained below the Abuja Declaration target of 15 percent of the national budget (World Bank 2023). Ghana's inflation has been volatile, with an annual average of about 17 percent since 1998 (Trading Economics 2026) and a sharp rise in 2022 (Bloomberg 2022). About 70 percent of Ghana's pharmaceutical requirements are imported (Pharmexcil 2020), so currency depreciation raises health costs independently of domestic wages. Minimum wages rose by about 211 percent in nominal terms between 2015 and 2026 (Fair Wages and Salaries Commission 2025; Finex Insights 2025), but adjustments lagged inflation for much of that period."),
    ("h2", "2.3 Contribution"),
    ("p", "Prior work measures CHE at a point in time. This paper complements it with a forward projection, anchored to the GLSS7 baseline, and tests how far its conclusions depend on the baseline."),

    ("h1", "3. Data and Methods"),
    ("h2", "3.1 Parameter evidence classification"),
    ("p", "Each parameter is classified as (A) Ghana-specific empirical, (B) external empirical, or (C) author calibration or judgement. Table 1 gives the classification. The classification was revised in this version. Two parameters that were previously described as well-grounded are now marked as author calibrations (C)."),
    ("table", "Table 1. Parameter values and evidence classification.",
     ["Parameter", "Primary value", "Upper-bound value", "Class", "Source or basis"],
     [
         ["Nominal minimum-wage CAGR, 2015–2026", "10.9%", "10.9%", "A", "GHS 7.00 (2015) to GHS 21.77 (2026); Fair Wages and Salaries Commission 2025; Finex Insights 2025"],
         ["Non-crisis OOP burden, % of income", "0.75%", "6.0%", "A (primary) / C (upper)", "GLSS7 weighted mean of OOP share of expenditure (0.75%); the 6% value is an author calibration to the CHE literature"],
         ["Burden floor, % of income", "0%", "1%", "C", "GLSS7 median is 0%; the 1% floor in the v3 model lifted 91% of primary-case draws and was removed for the primary case"],
         ["OOP share of current health expenditure", "26%", "26%", "A", "Okoroh and Essoun 2018; World Bank 2023. Cancels out of the burden formula unless it drifts (see Section 3.4)"],
         ["Annual probability of a catastrophic event", "8%", "8%", "B (blended)", "Blended from sub-Saharan CHE incidence (12.9–20.4%) and Ghana-specific findings; sensitivity 1.1–15%"],
         ["Crisis severity multiplier", "3–7×", "3–7×", "C", "Author calibration to the qualitative CHE severity gap"],
         ["Annual probability of a currency-shock year", "12%", "12%", "C", "Author estimate. Note: about 4 episodes in 25 years would give 16%; see Section 6"],
         ["Stable and shock inflation (means, SDs)", "10% (3%); 30% (10%)", "same", "C", "Author calibration to 2024–2026 disinflation and the 2022–2023 episode; Trading Economics 2026; Bloomberg 2022"],
         ["Import-cost premium, shock / stable years", "6% / 2%", "6% / 2%", "C", "Author calibration; the import share of pharmaceuticals (about 70%; Pharmexcil 2020) supports the direction of effect, not the size"],
         ["Liquidity buffer; debt-trigger threshold", "1 month; 15 pp", "same", "C", "Illustrative; sensitivity grid in Section 4.4"],
     ]),
    ("h2", "3.2 Model structure"),
    ("p", "We simulate n = 10,000 households over 26 annual observations (2026–2051) for the primary analysis, and over 36 observations (2026–2061) for the extended analysis. The 26 observations span the 25-year interval from 2026 to 2051 inclusive. Each year a household is assigned to a shock or stable regime, with inflation drawn from a regime-specific normal distribution clipped to [−2%, 65%]. Income grows at the minimum-wage CAGR. Health-cost growth equals inflation plus an import-cost premium. The affordability-gap ratio is the health-cost index divided by the income index. Base burden is the non-crisis burden times the OOP-share ratio times the gap ratio. A catastrophic event in a household-year multiplies that year's base burden by a severity factor drawn from U(3, 7). Burden is clipped to [floor, 120%] of income. A debt event occurs when a catastrophic year's burden exceeds the liquidity buffer by more than 15 percentage points."),
    ("eq", "Base burden: B(i,t) = base × S(t) / 26% × H(t)/I(t);  burden = B × M if a catastrophic event occurs, otherwise B; clipped to [floor, 120%]."),
    ("h2", "3.3 Scenarios"),
    ("p", "The three scenarios share the same equations and differ only in the parameter values in Table 2. Scenario definitions are unchanged from the earlier version."),
    ("table", "Table 2. Scenario parameters.",
     ["Scenario", "Shock frequency", "Import premium (shock / stable)", "Catastrophic-event probability", "OOP-share drift"],
     [["Status quo", "12%/yr", "6.0% / 2.0%", "8.0%/yr", "0.0%/yr"],
      ["Financing reform (Abuja target)", "12%/yr", "3.0% / 1.0%", "6.4%/yr", "−0.6%/yr"],
      ["Repeated currency shocks", "25%/yr", "9.0% / 2.0%", "8.0%/yr", "+0.4%/yr"]]),
    ("h2", "3.4 GLSS7 empirical baseline"),
    ("p", "The GLSS7 baseline is computed from the household expenditure and health expenditure aggregates, weighted by the household sampling weight. The files used are: the household roster g7sec1.dta (person-level, 59,864 rows, household identifier hid, reduced to one row per household by the relationship variable s1q3, head = code 1); the health-expenditure aggregate 06_GHA_EXPHLTH.dta; and the poverty and welfare aggregate 18_GHA_POV_2017_GLSS7.dta. Burden is TOTHLTH divided by HHEXP_N, weighted by WTA_S. File and variable names follow the GSS data documentation for GLSS7 (Ghana Statistical Service 2018). The full configuration is in glss7_extraction_config.yaml in the code repository."),
    ("table", "Table 3. GLSS7 (2016/17) empirical household OOP burden, computed by the authors from the GSS microdata.",
     ["Statistic", "Value"],
     [["Households (weighted analysis sample)", "14,009"],
      ["Weighted mean OOP burden (% of expenditure)", "0.75%"],
      ["Weighted median OOP burden (% of expenditure)", "0.00%"],
      ["CHE incidence at 10% / 20% / 25% of expenditure", "1.08% / 0.21% / 0.13%"],
      ["Mean OOP burden, poorest and richest expenditure deciles", "1.11% and 0.62%"]]),
    ("p", "Burden in the GLSS7 analysis is a share of total expenditure, while the simulation expresses burden as a share of income. This difference in denominator is a limitation of the comparison (Section 6)."),
    ("h2", "3.5 Sensitivity analysis"),
    ("p", f"We ran a one-at-a-time (OAT) analysis on the primary configuration using common random numbers, so every arm uses the same random seed and the swing reflects the parameter alone. We also ran a probabilistic analysis with 300 joint draws (n = 2,000 households per draw). The OOP share of health expenditure is passed through the model but cancels out of the burden formula, so its effect is zero by construction. The OAT swing for this parameter is {f2(K['oop_share_swing_common_seed'])} percentage points."),
    ("h2", "3.6 Limitations of the modelling approach"),
    ("p", "The model is a stylised stress test. It does not include household-level heterogeneity, behavioural responses, informal risk-sharing (susu schemes, family transfers, remittances), or changes in NHIS financing architecture. The catastrophic-event hazard is a per-household annual probability, whereas the GLSS7 incidence is a realised share of households in one survey year. The two are conceptually different (Section 4.2)."),

    ("h1", "4. Results"),
    ("h2", "4.1 Primary results: GLSS7-anchored baseline"),
    ("p", f"Under the GLSS7 baseline, the mean household burden under the status quo rises from {f1(P_SQ.mean_2026)} percent of income in 2026 to {f1(P_SQ.mean_end)} percent in 2051. The median is {f1(P_SQ.median_end)} percent, and the 90th percentile is {f1(P_SQ.p90_end)} percent. In the financing-reform scenario, mean burden is {f1(P_RF.mean_end)} percent in 2051. In the repeated-shock scenario, mean burden rises to {f1(P_SH.mean_end)} percent, with a median of {f1(P_SH.median_end)} percent and a 90th percentile of {f1(P_SH.p90_end)} percent."),
    ("table", "Table 4. Primary results (GLSS7 baseline), 2051 unless stated.",
     ["Scenario", "Mean 2026 (%)", "Mean 2051 (%)", "Median 2051 (%)", "P90 2051 (%)", "Share above 20% in 2051", "P(at least one debt event by 2051)", "Mean debt events by 2051"],
     [[lbl, f1(r.mean_2026), f1(r.mean_end), f1(r.median_end), f1(r.p90_end), f"{f1(r.share_over_20_end)}%", f"{f1(r.p_any_debt_event_by_50)}%", f2(r.mean_debt_events_by_50)]
      for lbl, r in [("Status quo", P_SQ), ("Financing reform", P_RF), ("Repeated shocks", P_SH)]]),
    ("fig", "figure1_paths_2026_2051.png", 6.0, "Figure 1. Projected mean household OOP burden, 2026–2051. Solid: GLSS7 baseline (primary). Dashed: 6% upper bound."),
    ("fig", "figure2_distribution_2051.png", 5.5, "Figure 2. Distribution of 2051 household burden under the GLSS7 baseline (whiskers: 10th–90th percentile)."),
    ("h2", "4.2 Validation against GLSS7 catastrophic-expenditure incidence"),
    ("p", f"In the first year, the primary model produces a catastrophic-expenditure incidence of {f2(K['validation.primary.year1_che10'])} percent at the 10 percent threshold, against {f2(1.08)} percent in GLSS7. The reason is structural. With a baseline of 0.75 percent, the largest crisis-year burden the model can produce in 2026 is {f2(MAX_CRISIS_PRIMARY)} percent of income. Reaching 10 percent would need a severity multiplier of about {f1(SEV_NEEDED)}×, well outside the 3–7× range. The primary model therefore does not reproduce the GLSS7 incidence, and its catastrophic burden arises from the widening cost-to-income gap rather than from first-year events. The 6% upper bound overshoots in the other direction, at {f2(K['validation.upper.year1_che10'])} percent. Neither calibration reproduces the observed year-one incidence."),
    ("p", f"Our recommendation is to keep the structural model unchanged and report this mismatch as a limitation, rather than raising the severity range until the first-year figure matches. Raising the range to reach 10 percent would fit the model to a target its mechanism cannot reach by construction, and would change the tail of the distribution. As a check on the starting point, the primary model gives a 2026 mean burden of {f2(P_SQ.mean_2026)} percent, against {f2(0.75)} percent in GLSS7. This is {f1((P_SQ.mean_2026/0.75-1)*100)} percent above the survey mean, and we report it as the validation of the starting level."),
    ("p", f"We also tested the annual hazard. Setting it to the GLSS7 incidence of 1.08 percent, or to any value between 4 and 15 percent, does not change the first-year incidence in the primary configuration (Table 5). The hazard therefore affects the tail of the 2051 distribution but not the year-one validation."),
    ("table", "Table 5. Hazard sensitivity, primary configuration, status quo.",
     ["Annual catastrophic-event probability", "Share above 10% in 2026", "Mean 2051 (%)", "P90 2051 (%)", "Share above 20% in 2051"],
     [[f"{r.p_health_crisis*100:.2f}%", f2(r.share_over_10_year1), f2(r.mean_2051), f2(r.p90_2051), f2(r.share_over_20_2051)] for _, r in H.iterrows()]),
    ("h2", "4.3 Upper bound: the 6% calibration"),
    ("p", f"The 6% calibration, which is the v3 manuscript's central case, gives a status-quo mean of {f1(U_SQ.mean_end)} percent in 2051 and a 90th percentile of {f1(U_SQ.p90_end)} percent. It is reported as an upper bound. The GLSS7 data do not support a non-crisis burden of 6 percent of income: the median household spends nothing in a typical year, and the mean is 0.75 percent of expenditure."),
    ("table", "Table 6. Comparison of the primary (GLSS7) and upper-bound (6%) configurations, 2051.",
     ["Scenario", "Primary mean (%)", "Upper-bound mean (%)", "Primary share above 20%", "Upper-bound share above 20%"],
     [[lbl, f1(p.mean_end), f1(u.mean_end), f"{f1(p.share_over_20_end)}%", f"{f1(u.share_over_20_end)}%"]
      for lbl, p, u in [("Status quo", P_SQ, U_SQ), ("Financing reform", P_RF, U_RF), ("Repeated shocks", P_SH, U_SH)]]),
    ("h2", "4.4 Debt-trigger sensitivity (primary configuration)"),
    ("p", f"Under the GLSS7 baseline, debt events are rare. The base case (one-month buffer, 15-point threshold) gives a probability of at least one debt event by 2051 of {f2(K['debt.base'])} percent, and the grid ranges from {f2(K['debt.min'])} to {f2(K['debt.max'])} percent (Table 7). The v3 conclusion that most households face a debt event does not hold under this baseline."),
    ("table", "Table 7. Debt-trigger grid, primary configuration, status quo, 2051.",
     ["Buffer (months)", "Threshold (pp)", "Mean debt events", "P(at least one) %"],
     [[f1(r.buffer_months), int(r.threshold_pp), f2(r.mean_debt_events), f2(r.p_at_least_one)] for _, r in G.iterrows()]),
    ("h2", "4.5 Sensitivity analysis"),
    ("p", f"Table 8 reports the OAT swings with common random numbers. For the primary configuration, the largest swings are for nominal wage growth ({f2(tor('primary','wage').swing_pp)} points), currency-shock frequency ({f2(tor('primary','p_shock_year').swing_pp)} points) and the baseline non-crisis burden ({f2(tor('primary','base').swing_pp)} points). The OOP share of health expenditure has no effect ({f2(tor('primary','oop_share_of_health').swing_pp)} points). The two wage and shock parameters are the largest drivers of the 2051 outcome. Of these, only wage growth is classed as well grounded (A). Currency-shock frequency and the baseline burden are author calibrations (C)."),
    ("table", "Table 8. One-at-a-time sensitivity, status quo, 2051, common random numbers.",
     ["Parameter", "Range tested", "Mean at low (%)", "Mean at high (%)", "Swing (pp)"],
     [[tor('primary', p).label, f"{tor('primary', p).low_value} to {tor('primary', p).high_value}", f2(tor('primary', p).mean2051_at_low), f2(tor('primary', p).mean2051_at_high), f2(tor('primary', p).swing_pp)]
      for p in ["wage", "p_shock_year", "base", "p_health_crisis", "import_premium_shock", "sev_high", "oop_share_of_health"]]),
    ("p", f"The upper-bound configuration shows the same top three parameters, with swings of {f1(tor('upper','wage').swing_pp)}, {f1(tor('upper','p_shock_year').swing_pp)} and {f1(tor('upper','base').swing_pp)} percentage points."),
    ("fig", "figure11_tornado_primary.png", 6.0, "Figure 3. One-at-a-time sensitivity, primary configuration (common random numbers)."),
    ("p", f"Probabilistic analysis (300 joint draws, primary configuration) gives a median 2051 burden of {f1(PSA['primary']['median'])} percent (10th–90th percentile {f1(PSA['primary']['p10'])}–{f1(PSA['primary']['p90'])} percent). No draw exceeds 20 percent. For the upper-bound configuration, the median is {f1(PSA['upper']['median'])} percent and {f1(PSA['upper']['share_over_20'])} percent of draws exceed 20 percent. The probabilistic analysis was re-run without the OOP-share parameter, which has no effect, so these values differ slightly from v3 (median 28.7 percent)."),
    ("fig", "figure12_psa_primary.png", 5.5, "Figure 4. Probabilistic sensitivity, primary configuration (300 joint draws)."),
    ("h2", "4.6 Extended projection to age 60"),
    ("p", f"Through age 60 (2061), the primary status-quo mean reaches {f1(K['primary.status_quo.mean2061'])} percent of income and the repeated-shock mean reaches {f1(K['primary.shock_heavy.mean2061'])} percent. The extended projection is a separate analysis and should not be read with the same weight as the 2051 results."),
    ("fig", "figure6_extended_2061.png", 6.0, "Figure 5. Extended projection to age 60 (2026–2061)."),
    ("fig", "figure7_budget_status_quo.png", 4.5, "Figure 6. Health share of household income at ages 25, 50 and 60, status quo, primary configuration."),
    ("fig", "figure8_budget_age60.png", 5.0, "Figure 7. Health share of household income at age 60, by scenario, primary configuration."),

    ("h1", "5. Discussion"),
    ("p", "The central result changes with the baseline. Under the GLSS7-anchored baseline, a typical household spends a small share of income on OOP healthcare, and the generational risk lies in the tail. The status quo drives a small rise in mean burden, while repeated currency shocks produce large increases concentrated in a minority of households. The earlier headline, in which the status quo brings the mean household to near the catastrophic threshold, depended on a 6% non-crisis baseline that the data do not support."),
    ("p", "The drivers of the outcome are, in order: nominal wage growth, currency-shock frequency and the baseline burden. Wage growth is the best-evidenced of the three. Shock frequency and the baseline are author calibrations, and the conclusions depend on them. Policy levers that reduce shock exposure, such as local production of medicines and reserves, therefore matter more in this analysis than the level of the OOP share."),
    ("p", "The policy message is narrower than the earlier draft. Financing reform keeps burden flat under every calibration. The status quo is manageable on average but leaves a tail that the shock scenarios make large. Protection against that tail requires limiting exposure to currency shocks and making NHIS coverage reliable, in addition to raising government health spending."),
    ("h2", "5.1 Structural drivers"),
    ("p", "Three structural features are documented in the literature and are consistent with the model's mechanisms: currency exposure in imported medical inputs (Pharmexcil 2020), NHIS coverage that has expanded in breadth faster than in depth (Okoroh and Essoun 2018), and government financing below the Abuja target (World Bank 2023). The model captures the first through the import-cost premium, and the second and third only indirectly."),
    ("h2", "5.2 Generational and clinical considerations"),
    ("p", "Non-communicable diseases accounted for 45 percent of deaths in Ghana in 2019 (WHO Regional Office for Africa 2023), and they tend to generate longer, repeat-cost care. The model does not represent this, so the projections probably understate the burden of chronic conditions."),
    ("h1", "6. Limitations"),
    ("bullet", "The primary model does not reproduce the GLSS7 catastrophic-expenditure incidence in year one (Section 4.2). The severity range would need to be far higher to do so."),
    ("bullet", "The GLSS7 burden is measured against total expenditure, and the simulation uses income. These denominators are not the same."),
    ("bullet", "The shock frequency of 12% is an author estimate. Four episodes in 25 years would give 16%. A sensitivity range of 6–25% is reported (Table 8)."),
    ("bullet", "The model is a stylised stress test. It uses one representative cohort and omits heterogeneity, behavioural responses and informal risk-sharing."),
    ("bullet", "The GLSS7 statistics (Table 3) were computed by the authors from the restricted microdata and cannot be regenerated from the public repository. They agree closely with an independent analysis of the same 14,009 households (Sataru, Twumasi-Ankrah and Seddoh 2022)."),
    ("bullet", "The catastrophic-event probability of 8% was blended from regional literature. Its interpretation as an annual per-household hazard is not directly supported by the survey data."),
    ("h1", "7. Conclusion"),
    ("p", f"A stochastic projection calibrated to the GLSS7 baseline finds that the mean OOP burden for a Generation Z cohort rises modestly under the status quo, to {f1(P_SQ.mean_end)} percent of income by 2051, while repeated currency shocks produce a large tail, with a 90th percentile of {f1(P_SH.p90_end)} percent. The generational risk lies in shock exposure, and financing reform keeps burden low under every calibration. The earlier, higher-burden projection depended on an assumed 6% non-crisis burden that the survey data do not support."),
    ("h1", "Data and Code Availability"),
    ("p", "GLSS7 (2016/17) microdata are held by the Ghana Statistical Service and are available on application through its standard procedure. The microdata cannot be redistributed. The simulation code, the sensitivity and reconciliation scripts, and the run pipeline are available at https://github.com/ZziemWellu/Healthcare-Affordability-Burden-Study-Ghana-Gen-Z- under the MIT licence, together with the v4 pipeline (model_v4.py, analysis_v4.py, run_all.py), its outputs and the GLSS7 extraction configuration. Running python run_all.py regenerates every simulation table and figure in this paper. The other public data sources are cited in Table 1 and the references. [[ADD archived DOI (e.g. Zenodo release of the repository) before submission]]"),
    ("h1", "Declarations"),
    ("p", "Use of AI tools: AI tools were used to check grammar and wording. [[AUTHORS TO CONFIRM BEFORE SUBMISSION: the project records show that an AI assistant also wrote the simulation, sensitivity and figure code, and drafted sections of the text. Journal policy requires disclosure of those uses. Suggested wording: “An AI assistant was used to draft and check text, to write and check the simulation and analysis code, and to generate figures. All modelling decisions, parameter choices and conclusions are the authors’ own, and the code was re-run and checked by the authors.”]]"),
    ("p", "Ethics: the study uses no identifiable personal data. [[CONFIRM whether institutional review is required for the GLSS7 analysis]]"),
    ("p", "Funding: This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors. Competing interests: The authors declare no competing interests. Author contributions: Nana Owusu Achiaw Prempeh was responsible for experiments, analysis and drafting the manuscript. Ziem P. Wellu was responsible for reviewing and correcting all experiments and analysis and for placing the manuscript in perspective."),
    ("p", "Acknowledgements: We thank an anonymous clinician for clinical input. [[EDITOR NOTE: the journal may require the identity of all contributors to be disclosed to the editor, even if not published]]"),
    ("refs", REFS),
]

ISSUE_LOG = [
    ["1", "Baseline re-anchoring", "Primary analysis now uses the GLSS7 baseline (0.75%). The 6% baseline is retained as an upper bound.", "Done. Headline numbers changed (Table 4, Table 6)."],
    ["2", "Period count", "Text now says 26 annual observations (2026–2051) and 36 (2026–2061), matching the code.", "Done"],
    ["3", "OOP-share parameter", "Reported as 0.00 under common random numbers, with the reason it cancels.", "Done"],
    ["4", "Sensitivity seeds", "Common random numbers used for every arm; swings recomputed.", "Done (Table 8)"],
    ["5", "Parameter classification", "Table 1 rewritten. Baseline burden is A in the primary (GLSS7) configuration and C in the upper bound; shock frequency is C. The text no longer says the most influential parameters are the best grounded.", "Done"],
    ["6", "GLSS7 extraction configuration", "glss7_extraction_config.yaml in the repository. Roster file (g7sec1, 59,864 cases), hid, s1q2, s1q3 and s1q5y confirmed from the GLSS7 data dictionary (IHSN GHA_2016_GLSS_v01_M; GSS catalog 97, DDI-GHA-GSS-GLSS7-2017-v1).", "Done for the reported statistics. Literacy and region are no longer used (Section 4.7 removed). Table 3 cannot be re-run without GSS access; corroborated against Sataru et al. 2022 (same 14,009 households: CHE 1.0% at 10%, 0.1% at 25%)"],
    ["7", "Figures", "All seven manuscript figures are generated from the model and renumbered 1–7 in order of appearance (files figure1, figure2, figure11→3, figure12→4, figure6→5, figure7→6, figure8→7). The v3 GLSS7 figures are not used.", "Done"],
    ["8", "Year-one validation", "Model does not reproduce the GLSS7 CHE incidence (1.08%) in year one under either calibration. Reported as a limitation.", "Open. Needs a decision on how to handle the structural mismatch"],
    ["9", "Burden floor", "Primary uses 0% floor; the 1% floor in v3 lifted 91% of draws under the GLSS7 baseline.", "Done (Table 1)"],
    ["10", "Probabilistic analysis", "Re-run without the OOP-share parameter; upper-bound median 27.8% (v3: 28.7%).", "Done; explained in Section 4.5"],
    ["11", "Citations", "WHO attribution, Zhang et al., Lule et al. and the AHIES attribution removed. Akazili cited as 2017a and 2017b. Medium-risk items flagged [[VERIFY]].", "Done. Findex and the WHO 15–20% placeholder were uncited and are removed; WHO AFRO source found and verified (2023 Ghana profile: NCDs 45% of deaths in 2019). Knoema replaced by Pharmexcil 2020 (70% of pharmaceuticals imported). Ataguba and Kabaniha 2022 verified (Table 2, Ghana quintiles); Akazili et al. 2011 added. The unsupported 12.8% figure is not used"],
    ["12", "Preprint and Springer paper", "Confirmed the medRxiv preprint is the same study as the published BMC Public Health paper. Both are cited in the Introduction as prior work.", "Done. DOI confirmed on Crossref; volume and article number not yet assigned (4 Nov 2026)"],
    ["13", "Co-author and clinical consultant", "Ziem P. Wellu named as co-corresponding author with affiliation, ORCID and contribution statement.", "Done. ORCID for N. O. A. Prempeh still to add"],
    ["14", "Journal and status", "Target: Health Economics Review. The README claim of submission and review is incorrect and should be corrected.", "Done. README in ZziemWellu repository corrected (not submitted; target journal stated)"],
    ["15", "Reproducibility of the pipeline", "All v4 outputs are generated by analysis_v4.py from model_v4.py. The upper-bound configuration reproduces the v3 numbers exactly.", "Done"],
    ["16", "Descriptive subgroup comparisons", "Removed (Section 4.7 and the literacy hypothesis). A test needs household-level data, which are not available to the team.", "Done"],
]

def main():
    build(MANUSCRIPT, os.path.join(MS, "Revised_manuscript_v4.docx"),
          banner="REVISED MANUSCRIPT (v4) FOR AUTHOR REVIEW. Numbers are generated from outputs/v4 at build time. Highlighted items must be resolved before submission to Health Economics Review.")
    build([("title", "Issue log (v4): Gen Z healthcare affordability manuscript"),
           ("table", "Issues raised in review and their status", ["#", "Item", "What changed", "Status"], ISSUE_LOG)],
          os.path.join(MS, "Issue_log_v4.docx"))

if __name__ == "__main__":
    main()
