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
from docx.enum.text import WD_LINE_SPACING, WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

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

def fig_parts(caption):
    """'Figure 3. Title text. Legend...' -> ('Figure 3', 'Title text', 'Legend...')."""
    label, rest = caption.split(". ", 1)
    title, _, legend = rest.partition(". ")
    return label, title.rstrip("."), legend


def journal_layout(doc):
    """Double line spacing, continuous line numbers and centred page numbers (HER requirements)."""
    for name in ("Normal", "List Bullet"):
        pf = doc.styles[name].paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    for s in doc.sections:
        ln = OxmlElement("w:lnNumType")
        ln.set(qn("w:countBy"), "1"); ln.set(qn("w:restart"), "continuous"); ln.set(qn("w:distance"), "360")
        s._sectPr.append(ln)
        p = s.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run()
        for tag, attr in (("w:fldChar", "begin"), ("w:instrText", None), ("w:fldChar", "end")):
            el = OxmlElement(tag)
            if attr:
                el.set(qn("w:fldCharType"), attr)
            else:
                el.set(qn("xml:space"), "preserve"); el.text = "PAGE"
            r._r.append(el)


def build(blocks, path, banner=None, figures_inline=True, journal=False):
    doc = Document()
    st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(1)
    if journal:
        journal_layout(doc)
    if banner:
        rich(doc.add_paragraph(), banner, italic=True, size=9)
    for b in blocks:
        k = b[0]
        if k == "title": doc.add_heading(b[1], level=0)
        elif k == "h1": doc.add_heading(b[1], level=1)
        elif k == "h2": doc.add_heading(b[1], level=2)
        elif k == "p": rich(doc.add_paragraph(), b[1])
        elif k == "lp":
            p = doc.add_paragraph(); r = p.add_run(b[1] + ": "); r.bold = True; rich(p, b[2])
        elif k == "bullet": rich(doc.add_paragraph(style="List Bullet"), b[1])
        elif k == "eq": p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.4); rich(p, b[1])
        elif k == "fig" and not figures_inline:
            # journal format: image uploaded as a separate file; title (bold) and legend stay in the text
            label, title, legend = fig_parts(b[3])
            p = doc.add_paragraph(); r = p.add_run(f"{label}. {title}."); r.bold = True
            if legend:
                rich(p, " " + legend)
        elif k == "fig":
            doc.add_picture(os.path.join(FIG, b[1]), width=Inches(b[2]))
            rich(doc.add_paragraph(), b[3], italic=True, size=9.5)
        elif k == "table":
            _, cap, header, rows = b[:4]
            legend = b[4] if len(b) > 4 else None
            rich(doc.add_paragraph(), cap, bold=True, size=10)
            t = doc.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
            for i, h in enumerate(header):
                rich(t.rows[0].cells[i].paragraphs[0], h, bold=True, size=9.5)
            for row in rows:
                cells = t.add_row().cells
                for i, v in enumerate(row):
                    rich(cells[i].paragraphs[0], str(v), size=9.5)
            for row in t.rows:
                for c in row.cells:
                    c.paragraphs[0].paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            if legend:
                rich(doc.add_paragraph(), legend, size=9.5)
            else:
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
    "Bloomberg. 2022. “Ghana Inflation Exceeds 37% as Data Compilation Is Changed.” October 12, 2022. https://www.bloomberg.com/news/articles/2022-10-12/ghana-annual-inflation-at-37-2-as-data-compilation-is-changed. Accessed 8 November 2026.",
    "Agyekum, Enoch Oti, Elisha Ngetich, Owen Smith, Soazic Elise Wang Sonne, Dorothee Chen, and Paul Andres Corral Rodas. 2023. Public Health Expenditure for Universal Health Coverage in Ghana. Health, Nutrition and Population Discussion Paper. Washington, DC: World Bank. https://hdl.handle.net/10986/41148.",
    "Finex Insights. 2025. “Ghana's Minimum Wage Growth: A Decade of Gradual Gains and Sudden Jumps (2015–2025).” August 19, 2025. https://www.finexinsights.com/post/ghana-s-minimum-wage-growth-a-decade-of-gradual-gains-and-sudden-jumps-2015-2025. Accessed 8 November 2026.",
    "MyJoyOnline. 2025. “Government Raises Public Sector Salaries, Minimum Wage by 9% for 2026.” November 10, 2025. https://www.myjoyonline.com/government-raises-public-sector-salaries-minimum-wage-by-9-for-2026/. Accessed 8 November 2026.",
    "Ghana Statistical Service. 2018. Ghana Living Standards Survey (GLSS VII) 2016-2017, version 01 (September 2018). Ref. GHA_2016_GLSS_v01_M. Accra: Ghana Statistical Service. https://microdata.statsghana.gov.gh/index.php/catalog/97. Accessed 8 November 2026.",
    "Okoroh, Juliet, Sarpong Essoun, Anthony Seddoh, Hobart Harris, Joel S. Weissman, Lydia Dsane-Selby, and Robert Riviello. 2018. “Evaluating the Impact of the National Health Insurance Scheme of Ghana on Out-of-Pocket Expenditures: A Systematic Review.” BMC Health Services Research 18: 426. https://doi.org/10.1186/s12913-018-3249-9.",
    "Pharmexcil (Pharmaceuticals Export Promotion Council of India). 2020. Ghana Pharma Market & Regulatory Report. Hyderabad: Pharmexcil. https://pharmexcil.com/uploads/countryreports/Ghana_Market_Regulatory_report2020.pdf. Accessed 8 November 2026.",
    "Prempeh, Nana Owusu Achiaw, and Patrick Ziem Wellu. 2026. Healthcare Affordability Burden Study: Ghana's Generation Z (code, outputs and run pipeline). GitHub. https://github.com/ZziemWellu/Healthcare-Affordability-Burden-Study-Ghana-Gen-Z-. Accessed 8 November 2026.",
    "Baah-Abekah, J., D. K. Ibrahim, T. A. Atugba, S. Theodore, S. A. Seidu, D. Casley-Hayford, L. Deborah, and B. Ahulu. 2025. “An Analysis of Household Catastrophic Health Expenditure and Food Insecurity in Ghana.” medRxiv preprint. https://doi.org/10.1101/2025.03.31.25324988.",
    "Sataru, Fuseini, Kwame Twumasi-Ankrah, and Anthony Seddoh. 2022. “An Analysis of Catastrophic Out-of-Pocket Health Expenditures in Ghana.” Frontiers in Health Services 2. https://doi.org/10.3389/frhs.2022.706216.",
    "Trading Economics. 2026. “Ghana Inflation Rate.” https://tradingeconomics.com/ghana/inflation-cpi. Accessed 8 November 2026.",
    "Wellu, Patrick Ziem, Adawu Redeemer, Michael Annor Peprah, Daniel Amakye, Emmanuel Prempeh Agyemang, Prince Peprah, and Williams Agyemang-Duah. 2026. “Catastrophic health expenditure and household food insecurity among older adults with health conditions in Ghana: a cross-sectional analysis.” BMC Public Health. Published 17 July 2026. https://doi.org/10.1186/s12889-026-28188-1.",
    "WHO Regional Office for Africa. 2023. “Ghana: Universal Health Coverage/Communicable and Non-communicable Diseases” (country profile). Brazzaville: WHO Regional Office for Africa. https://www.afro.who.int/sites/default/files/2023-08/Ghana.pdf. Accessed 8 November 2026.",
    "World Bank. n.d. “Out-of-Pocket Expenditure (% of Current Health Expenditure) – Ghana.” World Bank Open Data. https://data.worldbank.org/indicator/SH.XPD.OOPC.CH.ZS?locations=GH. Accessed 4 November 2026.",
]

MANUSCRIPT = [
    ("title", "Projecting the Healthcare Affordability Gap: A Stochastic Stress-Test of Out-of-Pocket Healthcare Burden for Ghana's Generation Z Cohort, 2026–2061"),
    ("p", "Nana Owusu Achiaw Prempeh (corresponding author), Department of Data Science, Academic City University College, Accra, Ghana. nana.prempeh@acity.edu.gh"),
    ("p", "Patrick Ziem Wellu (co-corresponding author), Department of Computer Science, University of Ghana, Accra, Ghana. pzwellu@st.ug.edu.gh. ORCID: 0009-0004-5808-2675"),
        ("h1", "Abstract"),
    ("lp", "Background", "Ghana's National Health Insurance Scheme was designed to protect households from catastrophic out-of-pocket (OOP) healthcare costs, yet OOP payments still account for more than a quarter of current health expenditure. This paper asks a generational question: if current trends in healthcare costs, wages and macroeconomic volatility persist, what OOP burden will Ghana's Generation Z cohort face around age 50?"),
    ("lp", "Methods", "We computed household OOP burden from GLSS7 (2016/17) microdata (n = 14,009 households). We then ran a stochastic stress-test simulation of 10,000 household trajectories from 2026 to 2051 under three scenarios: status quo, financing reform to the Abuja target, and repeated currency shocks. The primary analysis is anchored to the GLSS7 baseline; an alternative calibration with a 6 percent non-crisis burden is reported as an upper bound."),
    ("lp", "Results", f"The GLSS7 weighted mean OOP burden is 0.75 percent of household expenditure, and 0 percent at the median. Under this baseline, the status-quo mean burden in 2051 is {f1(P_SQ.mean_end)} percent of income, the financing-reform scenario is {f1(P_RF.mean_end)} percent, and repeated currency shocks reach {f1(P_SH.mean_end)} percent, with a 90th percentile of {f1(P_SH.p90_end)} percent. Only {f1(P_SQ.share_over_20_end)} percent of status-quo households exceed the 20 percent catastrophic-expenditure threshold in 2051. The 6 percent calibration produces materially higher burdens (status quo {f1(U_SQ.mean_end)} percent in 2051), but the GLSS7 data do not support that baseline. The model does not reproduce the GLSS7 catastrophic-expenditure incidence in year one."),
    ("lp", "Conclusions", "Under the data-supported baseline, the generational risk lies in exposure to currency shocks rather than in the average household's burden, and financing reform keeps burden low under every calibration. Results are model-implied outcomes under stated assumptions, not forecasts for individual households."),
    ("p", "Keywords: catastrophic health expenditure; out-of-pocket payments; National Health Insurance Scheme; Ghana; generational projection; Monte Carlo simulation; GLSS7."),

    ("h1", "Background"),
    ("p", "Out-of-pocket payments account for more than a quarter of current health expenditure in Ghana (World Bank, n.d.), and catastrophic health expenditure (CHE) falls hardest on poorer households (Akazili et al. 2017a; Akazili et al. 2017b; Ataguba and Kabaniha 2022). Most of the CHE literature in Ghana is retrospective and cross-sectional. It describes the burden in a survey year and does not ask what a cohort will face as it ages. This paper projects the burden for a cohort of young adults, representative of Generation Z, to around age 50."),
    ("p", "Generation Z is used as an analytical cohort, not a homogeneous population. The primary simulation represents a household aged 25 in 2026, which corresponds to a 2001 birth year. It runs for 26 annual observations (2026–2051) and, in an extended analysis, for 36 annual observations (2026–2061, age 60)."),
    ("p", "A companion study by the same team analysed AHIES 2022 data on catastrophic expenditure and food insecurity among adults aged 50 and over with a health condition (Wellu et al. 2026). That study is cross-sectional and covers a different population and outcome. The present paper is a forward projection built on GLSS7 (2016/17) and does not reuse the 2022 AHIES analysis."),
    ("p", "The paper makes three contributions. It shows what the GLSS7 microdata imply for the starting burden. It sets out a transparent stochastic model and classifies every parameter by its evidence. And it shows how strongly the generational conclusion depends on the baseline calibration, which we treat as the main decision in the analysis."),

    ("h2", "Catastrophic health expenditure and NHIS in Ghana"),
    ("p", "The National Health Insurance Scheme was introduced in 2003 to reduce OOP payments. The pre-NHIS baseline, based on the 2005/06 Ghana Living Standards Survey, found that OOP payments increased poverty and were regressive across income deciles (Akazili et al. 2017a). A companion analysis from the same survey round estimated the share of households spending more than 20 percent of income on OOP care (Akazili et al. 2017b). Okoroh et al. (2018) reviewed NHIS impact studies and found that uninsured households paid substantially more out of pocket than insured households, while a meaningful minority of insured households still incurred catastrophic payments. OOP payments are the regressive component of Ghana's health financing (Akazili, Gyapong and McIntyre 2011); in their data, the poorest fifth of households bears 6.9 percent of OOP spending against 5.5 percent of income (Ataguba and Kabaniha 2022). Sataru, Twumasi-Ankrah and Seddoh (2022) analyse catastrophic OOP expenditure in Ghana using GLSS7 and find an incidence of 1.0 percent at the 10 percent threshold."),
    ("h2", "Financing gaps and macroeconomic volatility"),
    ("p", "Government health spending in Ghana has remained below the Abuja Declaration target of 15 percent of the national budget (Agyekum et al. 2023). Ghana's inflation has been volatile, with an annual average of about 17 percent since 1998 (Trading Economics 2026) and a sharp rise in 2022 (Bloomberg 2022). About 70 percent of Ghana's pharmaceutical requirements are imported (Pharmexcil 2020), so currency depreciation raises health costs independently of domestic wages. Minimum wages rose by about 211 percent in nominal terms between 2015 and 2026 (Finex Insights 2025; MyJoyOnline 2025), but adjustments lagged inflation for much of that period."),
    ("h2", "Contribution of this study"),
    ("p", "Prior work measures CHE at a point in time. This paper complements it with a forward projection, anchored to the GLSS7 baseline, and tests how far its conclusions depend on the baseline."),

    ("h1", "Methods"),
    ("h2", "Parameter evidence classification"),
    ("p", "Each parameter is classified as (A) Ghana-specific empirical, (B) external empirical, or (C) author calibration or judgement. Table 1 lists every parameter with its primary and upper-bound value, its class and its source. Of the ten parameters, three are Ghana-specific empirical values in the primary configuration (A), one is blended from external evidence (B), and six are author calibrations (C)."),
    ("table", "Table 1. Parameter values and evidence classification.",
     ["Parameter", "Primary value", "Upper-bound value", "Class", "Source or basis"],
     [
         ["Nominal minimum-wage CAGR, 2015–2026", "10.9%", "10.9%", "A", "GHS 7.00 (2015; Finex Insights 2025) to GHS 21.77 (2026; MyJoyOnline 2025)"],
         ["Non-crisis OOP burden, % of income", "0.75%", "6.0%", "A (primary) / C (upper)", "GLSS7 weighted mean of OOP share of expenditure (0.75%); the 6% value is an author calibration to the CHE literature"],
         ["Burden floor, % of income", "0%", "1%", "C", "GLSS7 median is 0%; a 1% floor would lift 91% of primary-case draws, so the primary case uses no floor"],
         ["OOP share of current health expenditure", "26%", "26%", "A", "Okoroh et al. 2018; Agyekum et al. 2023. Cancels out of the burden formula unless it drifts (see Methods, Sensitivity analysis)"],
         ["Annual probability of a catastrophic event", "8%", "8%", "B (blended)", "Blended from sub-Saharan CHE incidence of 12.9–20.4% (Baah-Abekah et al. 2025) and Ghana-specific findings; sensitivity 1.1–15%"],
         ["Crisis severity multiplier", "3–7×", "3–7×", "C", "Author calibration to the qualitative CHE severity gap"],
         ["Annual probability of a currency-shock year", "12%", "12%", "C", "Author estimate. Note: about 4 episodes in 25 years would give 16%; see Limitations"],
         ["Stable and shock inflation (means, SDs)", "10% (3%); 30% (10%)", "same", "C", "Author calibration to 2024–2026 disinflation and the 2022–2023 episode; Trading Economics 2026; Bloomberg 2022"],
         ["Import-cost premium, shock / stable years", "6% / 2%", "6% / 2%", "C", "Author calibration; about 70% of pharmaceuticals are imported (Pharmexcil 2020), which supports the direction of effect, not the size"],
         ["Liquidity buffer; debt-trigger threshold", "1 month; 15 pp", "same", "C", "Illustrative; sensitivity grid in Table 7"],
     ],
     "Class A: Ghana-specific empirical; B: external empirical; C: author calibration or judgement. CAGR: compound annual growth rate; CHE: catastrophic health expenditure; GHS: Ghana cedi; OOP: out-of-pocket; pp: percentage points; SD: standard deviation."),
    ("h2", "Model structure"),
    ("p", "We simulate n = 10,000 households over 26 annual observations (2026–2051) for the primary analysis, and over 36 observations (2026–2061) for the extended analysis. The 26 observations span the 25-year interval from 2026 to 2051 inclusive. Each year a household is assigned to a shock or stable regime, with inflation drawn from a regime-specific normal distribution clipped to [−2%, 65%]. Income grows at the minimum-wage CAGR. Health-cost growth equals inflation plus an import-cost premium. The affordability-gap ratio is the health-cost index divided by the income index. Base burden is the non-crisis burden times the OOP-share ratio times the gap ratio. A catastrophic event in a household-year multiplies that year's base burden by a severity factor drawn from U(3, 7). Burden is clipped to [floor, 120%] of income. A debt event occurs when a catastrophic year's burden exceeds the liquidity buffer by more than 15 percentage points."),
    ("eq", "Base burden: B(i,t) = base × S(t) / 26% × H(t)/I(t);  burden = B × M if a catastrophic event occurs, otherwise B; clipped to [floor, 120%]."),
    ("p", "Here base is the non-crisis burden, S(t) is the OOP share of current health expenditure in year t (26 percent at baseline), H(t) and I(t) are the health-cost and income indices (both 1 in 2026), and M is the severity multiplier drawn for a catastrophic year."),
    ("h2", "Scenarios"),
    ("p", "The three scenarios share the same equations and differ only in the parameter values in Table 2. Financing reform lowers the import premium and the catastrophic-event probability and lets the OOP share drift down; repeated currency shocks more than double the shock frequency, raise the shock-year import premium and let the OOP share drift up."),
    ("table", "Table 2. Scenario parameters.",
     ["Scenario", "Shock frequency", "Import premium (shock / stable)", "Catastrophic-event probability", "OOP-share drift"],
     [["Status quo", "12%/yr", "6.0% / 2.0%", "8.0%/yr", "0.0%/yr"],
      ["Financing reform (Abuja target)", "12%/yr", "3.0% / 1.0%", "6.4%/yr", "−0.6%/yr"],
      ["Repeated currency shocks", "25%/yr", "9.0% / 2.0%", "8.0%/yr", "+0.4%/yr"]],
     "Shock frequency is the annual probability of a currency-shock year. Import premium is added to inflation to give health-cost growth. OOP-share drift is the annual change in the OOP share of current health expenditure. All other parameters are as in Table 1."),
    ("h2", "GLSS7 empirical baseline"),
    ("p", "The GLSS7 baseline is computed from the household expenditure and health expenditure aggregates, weighted by the household sampling weight. The files used are: the household roster g7sec1.dta (person-level, 59,864 rows, household identifier hid, reduced to one row per household by the relationship variable s1q3, head = code 1); the health-expenditure aggregate 06_GHA_EXPHLTH.dta; and the poverty and welfare aggregate 18_GHA_POV_2017_GLSS7.dta. Burden is TOTHLTH divided by HHEXP_N, weighted by WTA_S. File and variable names follow the GSS data documentation for GLSS7 (Ghana Statistical Service 2018). The full configuration is in glss7_extraction_config.yaml in the code repository (Prempeh and Wellu 2026). Table 3 summarises the resulting household estimates: the median household reports no OOP spending, and the poorest expenditure decile carries a higher mean burden than the richest."),
    ("table", "Table 3. GLSS7 (2016/17) household OOP burden, computed by the authors from GSS microdata.",
     ["Statistic", "Value"],
     [["Households (weighted analysis sample)", "14009"],
      ["Weighted mean OOP burden (% of expenditure)", "0.75%"],
      ["Weighted median OOP burden (% of expenditure)", "0.00%"],
      ["CHE incidence at 10% / 20% / 25% of expenditure", "1.08% / 0.21% / 0.13%"],
      ["Mean OOP burden, poorest and richest expenditure deciles", "1.11% and 0.62%"]],
     "Burden is household OOP health spending (TOTHLTH) as a percentage of nominal household expenditure (HHEXP_N), weighted by the household sampling weight (WTA_S). CHE: catastrophic health expenditure; OOP: out-of-pocket."),
    ("p", "Burden in the GLSS7 analysis is a share of total expenditure, while the simulation expresses burden as a share of income. This difference in denominator is a limitation of the comparison (see Limitations)."),
    ("h2", "Sensitivity analysis"),
    ("p", f"We ran a one-at-a-time (OAT) analysis on the primary configuration using common random numbers, so every arm uses the same random seed and the swing reflects the parameter alone. We also ran a probabilistic analysis with 300 joint draws (n = 2,000 households per draw). The OOP share of health expenditure is passed through the model but cancels out of the burden formula, so its effect is zero by construction. The OAT swing for this parameter is {f2(K['oop_share_swing_common_seed'])} percentage points."),
    ("h2", "Scope of the model"),
    ("p", "The model is a stylised stress test. It does not include household-level heterogeneity, behavioural responses, informal risk-sharing (susu schemes, family transfers, remittances), or changes in NHIS financing architecture. The catastrophic-event hazard is a per-household annual probability, whereas the GLSS7 incidence is a realised share of households in one survey year. The two are conceptually different (see Results, Validation against GLSS7 catastrophic-expenditure incidence)."),
    ("h2", "Use of artificial intelligence tools"),
    ("p", "An AI assistant (Claude, Anthropic) was used, under the authors' direction, for literature search, editing and drafting of text, reference checking, and writing and checking analysis and figure code. The authors designed the study, made all modelling decisions, verified all content and code, and take full responsibility for the work."),

    ("h1", "Results"),
    ("h2", "Primary results: GLSS7-anchored baseline"),
    ("p", f"Under the GLSS7 baseline, the mean household burden under the status quo rises from {f1(P_SQ.mean_2026)} percent of income in 2026 to {f1(P_SQ.mean_end)} percent in 2051. The median is {f1(P_SQ.median_end)} percent, and the 90th percentile is {f1(P_SQ.p90_end)} percent. In the financing-reform scenario, mean burden is {f1(P_RF.mean_end)} percent in 2051. In the repeated-shock scenario, mean burden rises to {f1(P_SH.mean_end)} percent, with a median of {f1(P_SH.median_end)} percent and a 90th percentile of {f1(P_SH.p90_end)} percent. Table 4 reports these results for all three scenarios, together with the share of households above the 20 percent threshold and the debt-event outcomes. Figure 1 shows the mean burden path from 2026 to 2051 under each scenario, with the 6% upper bound drawn as dashed lines for comparison. Figure 2 shows how widely household burden is spread in 2051: the 10th–90th percentile range is {f1(K['primary.status_quo.p10_end'])}–{f1(K['primary.status_quo.p90_end'])} percent under the status quo but {f1(K['primary.shock_heavy.p10_end'])}–{f1(K['primary.shock_heavy.p90_end'])} percent under repeated currency shocks."),
    ("table", "Table 4. Primary results (GLSS7 baseline), 2051 unless stated.",
     ["Scenario", "Mean 2026 (%)", "Mean 2051 (%)", "Median 2051 (%)", "P90 2051 (%)", "Share above 20% in 2051", "P(at least one debt event by 2051)", "Mean debt events by 2051"],
     [[lbl, f1(r.mean_2026), f1(r.mean_end), f1(r.median_end), f1(r.p90_end), f"{f1(r.share_over_20_end)}%", f"{f1(r.p_any_debt_event_by_50)}%", f2(r.mean_debt_events_by_50)]
      for lbl, r in [("Status quo", P_SQ), ("Financing reform", P_RF), ("Repeated shocks", P_SH)]],
     "Burden is OOP health spending as a percentage of household income, across 10000 simulated households per scenario. A debt event is a catastrophic year in which burden exceeds the one-month liquidity buffer by more than 15 percentage points. P90: 90th percentile; P: probability."),
    ("fig", "figure1_paths_2026_2051.png", 6.0, "Figure 1. Projected mean household OOP burden, 2026–2051, by scenario and configuration. Mean burden as a percentage of household income across 10,000 simulated households, under the GLSS7 baseline (primary) and the 6% upper bound."),
    ("fig", "figure2_distribution_2051.png", 5.5, "Figure 2. Distribution of household OOP burden in 2051, GLSS7 baseline, by scenario. Boxes show the interquartile range and median; whiskers show the 10th and 90th percentiles."),
    ("h2", "Validation against GLSS7 catastrophic-expenditure incidence"),
    ("p", f"In the first year, the primary model produces a catastrophic-expenditure incidence of {f2(K['validation.primary.year1_che10'])} percent at the 10 percent threshold, against {f2(1.08)} percent in GLSS7. The reason is structural. With a baseline of 0.75 percent, the largest crisis-year burden the model can produce in 2026 is {f2(MAX_CRISIS_PRIMARY)} percent of income. Reaching 10 percent would need a severity multiplier of about {f1(SEV_NEEDED)}×, well outside the 3–7× range. The primary model therefore does not reproduce the GLSS7 incidence, and its catastrophic burden arises from the widening cost-to-income gap rather than from first-year events. The 6% upper bound overshoots in the other direction, at {f2(K['validation.upper.year1_che10'])} percent. Neither calibration reproduces the observed year-one incidence."),
    ("p", f"We therefore keep the structural model unchanged and report this mismatch as a limitation, rather than raising the severity range until the first-year figure matches. Raising the range to reach 10 percent would fit the model to a target its mechanism cannot reach by construction, and would change the tail of the distribution. As a check on the starting point, the primary model gives a 2026 mean burden of {f2(P_SQ.mean_2026)} percent, against {f2(0.75)} percent in GLSS7. This is {f1((P_SQ.mean_2026/0.75-1)*100)} percent above the survey mean, and we report it as the validation of the starting level."),
    ("p", f"We also tested the annual hazard. Setting it to the GLSS7 incidence of 1.08 percent, or to any value between 4 and 15 percent, does not change the first-year incidence in the primary configuration (Table 5). The hazard therefore affects the tail of the 2051 distribution but not the year-one validation."),
    ("table", "Table 5. Hazard sensitivity, primary configuration, status quo.",
     ["Annual catastrophic-event probability", "Share above 10% in 2026 (%)", "Mean 2051 (%)", "P90 2051 (%)", "Share above 20% in 2051 (%)"],
     [[f"{r.p_health_crisis*100:.2f}%", f2(r.share_over_10_year1), f2(r.mean_2051), f2(r.p90_2051), f2(r.share_over_20_2051)] for _, r in H.iterrows()],
     "Burden is OOP health spending as a percentage of household income. Shares are percentages of simulated households above the stated burden. 1.08% is the GLSS7 incidence at the 10% threshold. P90: 90th percentile."),
    ("h2", "Upper bound: the 6% calibration"),
    ("p", f"The 6% calibration, an author calibration to the CHE literature, gives a status-quo mean of {f1(U_SQ.mean_end)} percent in 2051 and a 90th percentile of {f1(U_SQ.p90_end)} percent. It is reported as an upper bound. The GLSS7 data do not support a non-crisis burden of 6 percent of income: the median household spends nothing in a typical year, and the mean is 0.75 percent of expenditure. Table 6 compares the two configurations for each scenario. The share of status-quo households above 20 percent in 2051 is {f1(P_SQ.share_over_20_end)} percent under the GLSS7 baseline and {f1(U_SQ.share_over_20_end)} percent under the upper bound."),
    ("table", "Table 6. Comparison of the primary (GLSS7) and upper-bound (6%) configurations, 2051.",
     ["Scenario", "Primary mean (%)", "Upper-bound mean (%)", "Primary share above 20%", "Upper-bound share above 20%"],
     [[lbl, f1(p.mean_end), f1(u.mean_end), f"{f1(p.share_over_20_end)}%", f"{f1(u.share_over_20_end)}%"]
      for lbl, p, u in [("Status quo", P_SQ, U_SQ), ("Financing reform", P_RF, U_RF), ("Repeated shocks", P_SH, U_SH)]],
     "Mean burden is OOP health spending as a percentage of household income. Primary: GLSS7 non-crisis burden of 0.75%; upper bound: non-crisis burden of 6%. Shares are percentages of simulated households with burden above 20% of income."),
    ("h2", "Debt-trigger sensitivity (primary configuration)"),
    ("p", f"Under the GLSS7 baseline, debt events are rare. The base case (one-month buffer, 15-point threshold) gives a probability of at least one debt event by 2051 of {f2(K['debt.base'])} percent, and the grid ranges from {f2(K['debt.min'])} to {f2(K['debt.max'])} percent (Table 7). Under the 6% upper bound, by contrast, {f1(K['upper.status_quo.p_any_debt_event_by_50'])} percent of status-quo households face at least one debt event by 2051, so the debt result also depends on the baseline."),
    ("table", "Table 7. Debt-trigger grid, primary configuration, status quo, 2051.",
     ["Buffer (months)", "Threshold (pp)", "Mean debt events", "P(at least one) %"],
     [[f1(r.buffer_months), int(r.threshold_pp), f2(r.mean_debt_events), f2(r.p_at_least_one)] for _, r in G.iterrows()],
     "Buffer: liquidity buffer in months of income. Threshold: the margin, in percentage points of income, by which a catastrophic year's burden must exceed the buffer to count as a debt event. P(at least one): percentage of households with at least one debt event by 2051. pp: percentage points."),
    ("h2", "One-at-a-time and probabilistic sensitivity"),
    ("p", f"Table 8 reports the OAT swings with common random numbers. For the primary configuration, the largest swings are for nominal wage growth ({f2(tor('primary','wage').swing_pp)} points), currency-shock frequency ({f2(tor('primary','p_shock_year').swing_pp)} points) and the baseline non-crisis burden ({f2(tor('primary','base').swing_pp)} points). The OOP share of health expenditure has no effect ({f2(tor('primary','oop_share_of_health').swing_pp)} points). The two wage and shock parameters are the largest drivers of the 2051 outcome. Of these, only wage growth is classed as well grounded (A). Currency-shock frequency and the baseline burden are author calibrations (C)."),
    ("table", "Table 8. One-at-a-time sensitivity, primary configuration, status quo, 2051.",
     ["Parameter", "Range tested", "Mean at low (%)", "Mean at high (%)", "Swing (pp)"],
     [[*re.match(r"(.*) \((.*)\)$", tor('primary', p).label).groups(), f2(tor('primary', p).mean2051_at_low), f2(tor('primary', p).mean2051_at_high), f2(tor('primary', p).swing_pp)]
      for p in ["wage", "p_shock_year", "base", "p_health_crisis", "import_premium_shock", "sev_high", "oop_share_of_health"]],
     "Each parameter is set to the low and the high end of its range with all others at baseline. Every arm uses the same random seed (common random numbers), so the swing reflects the parameter alone. Mean: mean burden as a percentage of household income in 2051. Swing: absolute difference between the two means, in percentage points (pp)."),
    ("p", f"The upper-bound configuration shows the same top three parameters, with swings of {f1(tor('upper','wage').swing_pp)}, {f1(tor('upper','p_shock_year').swing_pp)} and {f1(tor('upper','base').swing_pp)} percentage points. Figure 3 shows the primary-configuration swings, ranked from largest to smallest, around the baseline 2051 mean of {f1(K['tornado.primary.baseline'])} percent."),
    ("fig", "figure11_tornado_primary.png", 6.0, "Figure 3. One-at-a-time sensitivity of 2051 mean burden, primary configuration, status quo. Each bar spans the 2051 mean burden at the low and high value of one parameter, with common random numbers across arms."),
    ("p", f"Probabilistic analysis (300 joint draws, primary configuration) gives a median 2051 burden of {f1(PSA['primary']['median'])} percent (10th–90th percentile {f1(PSA['primary']['p10'])}–{f1(PSA['primary']['p90'])} percent). No draw exceeds 20 percent. For the upper-bound configuration, the median is {f1(PSA['upper']['median'])} percent and {f1(PSA['upper']['share_over_20'])} percent of draws exceed 20 percent. The OOP-share parameter is left out of the joint draws because it has no effect (see Methods, Sensitivity analysis). Figure 4 shows the distribution of the 300 primary-configuration draws around their median."),
    ("fig", "figure12_psa_primary.png", 5.5, "Figure 4. Probabilistic sensitivity of 2051 mean burden, primary configuration (300 joint draws). Histogram of the 2051 mean burden across joint parameter draws, each with 2,000 simulated households."),
    ("h2", "Extended projection to age 60"),
    ("p", f"Through age 60 (2061), the primary status-quo mean reaches {f1(K['primary.status_quo.mean2061'])} percent of income and the repeated-shock mean reaches {f1(K['primary.shock_heavy.mean2061'])} percent. The extended projection is a separate analysis and should not be read with the same weight as the 2051 results. Figure 5 extends the mean paths of Figure 1 to 2061 for both configurations. Figure 6 shows the status-quo OOP share of household income at ages 25, 50 and 60 ({f1(P_SQ.mean_2026)}, {f1(P_SQ.mean_end)} and {f1(K['primary.status_quo.mean2061'])} percent). Figure 7 compares the three scenarios at age 60: {f1(K['primary.status_quo.mean2061'])} percent under the status quo, {f1(K['primary.reform.mean2061'])} percent under financing reform and {f1(K['primary.shock_heavy.mean2061'])} percent under repeated currency shocks."),
    ("fig", "figure6_extended_2061.png", 6.0, "Figure 5. Extended projection of mean household OOP burden to age 60 (2026–2061). Mean burden as a percentage of household income, under the GLSS7 baseline (primary) and the 6% upper bound."),
    ("fig", "figure7_budget_status_quo.png", 4.5, "Figure 6. Health share of household income at ages 25, 50 and 60, status quo. Mean OOP burden as a share of household income, primary configuration."),
    ("fig", "figure8_budget_age60.png", 5.0, "Figure 7. Health share of household income at age 60, by scenario. Mean OOP burden as a share of household income in 2061, primary configuration."),

    ("h1", "Discussion"),
    ("p", "The central result changes with the baseline. Under the GLSS7-anchored baseline, a typical household spends a small share of income on OOP healthcare, and the generational risk lies in the tail. The status quo drives a small rise in mean burden, while repeated currency shocks produce large increases concentrated in a minority of households. A projection in which the status quo brings the mean household close to the catastrophic threshold requires a 6% non-crisis baseline, which the data do not support (Table 6)."),
    ("p", "The drivers of the outcome are, in order: nominal wage growth, currency-shock frequency and the baseline burden. Wage growth is the best-evidenced of the three. Shock frequency and the baseline are author calibrations, and the conclusions depend on them. Policy levers that reduce shock exposure, such as local production of medicines and reserves, therefore matter more in this analysis than the level of the OOP share."),
    ("p", "The policy message is therefore targeted. Financing reform keeps burden flat under every calibration. The status quo is manageable on average but leaves a tail that the shock scenarios make large. Protection against that tail requires limiting exposure to currency shocks and making NHIS coverage reliable, in addition to raising government health spending."),
    ("h2", "Structural drivers"),
    ("p", "Three structural features are documented in the literature and are consistent with the model's mechanisms: currency exposure in imported medical inputs (Pharmexcil 2020), NHIS coverage that has expanded in breadth faster than in depth (Okoroh et al. 2018), and government financing below the Abuja target (Agyekum et al. 2023). The model captures the first through the import-cost premium, and the second and third only indirectly."),
    ("h2", "Generational and clinical considerations"),
    ("p", "Non-communicable diseases accounted for 45 percent of deaths in Ghana in 2019 (WHO Regional Office for Africa 2023), and they tend to generate longer, repeat-cost care. The model does not represent this, so the projections probably understate the burden of chronic conditions."),
    ("h2", "Limitations"),
    ("bullet", "The primary model does not reproduce the GLSS7 catastrophic-expenditure incidence in year one (see Results, Validation against GLSS7 catastrophic-expenditure incidence). The severity range would need to be far higher to do so."),
    ("bullet", "The GLSS7 burden is measured against total expenditure, and the simulation uses income. These denominators are not the same."),
    ("bullet", "The shock frequency of 12% is an author estimate. Four episodes in 25 years would give 16%. A sensitivity range of 6–25% is reported (Table 8)."),
    ("bullet", "The model is a stylised stress test. It uses one representative cohort and omits heterogeneity, behavioural responses and informal risk-sharing."),
    ("bullet", "The GLSS7 statistics (Table 3) were computed by the authors from the restricted microdata and cannot be regenerated from the public repository. They agree closely with an independent analysis of the same 14,009 households (Sataru, Twumasi-Ankrah and Seddoh 2022)."),
    ("bullet", "The catastrophic-event probability of 8% was blended from regional literature. Its interpretation as an annual per-household hazard is not directly supported by the survey data."),
    ("h1", "Conclusions"),
    ("p", f"A stochastic projection calibrated to the GLSS7 baseline finds that the mean OOP burden for a Generation Z cohort rises modestly under the status quo, to {f1(P_SQ.mean_end)} percent of income by 2051, while repeated currency shocks produce a large tail, with a 90th percentile of {f1(P_SH.p90_end)} percent. The generational risk lies in shock exposure, and financing reform keeps burden low under every calibration. Higher-burden projections depend on an assumed 6% non-crisis burden that the survey data do not support."),
    ("h1", "Abbreviations"),
    ("p", "AHIES: Annual Household Income and Expenditure Survey; CAGR: compound annual growth rate; CHE: catastrophic health expenditure; GLSS7: Ghana Living Standards Survey Round 7; GSS: Ghana Statistical Service; NCD: non-communicable disease; NHIS: National Health Insurance Scheme; OAT: one-at-a-time; OOP: out-of-pocket; pp: percentage points; SD: standard deviation."),
    ("h1", "Declarations"),
    ("h2", "Ethics approval and consent to participate"),
    ("p", "Not applicable. The study is a secondary analysis of anonymised GLSS7 microdata released by the Ghana Statistical Service, combined with a simulation model that involves no human participants. Ethics approval was therefore not required."),
    ("h2", "Consent for publication"),
    ("p", "Not applicable."),
    ("h2", "Availability of data and materials"),
    ("p", "The GLSS7 (2016/17) microdata that support the baseline estimates are available from the Ghana Statistical Service microdata catalogue after registration, https://microdata.statsghana.gov.gh/index.php/catalog/97 (Ghana Statistical Service 2018). Restrictions apply to these data, which were used under the survey's terms of use and cannot be redistributed by the authors. The simulation outputs supporting the conclusions of this article are available in the GitHub repository, https://github.com/ZziemWellu/Healthcare-Affordability-Burden-Study-Ghana-Gen-Z- (Prempeh and Wellu 2026), together with the code that generates every simulation table and figure (python run_all.py) and the GLSS7 extraction configuration. The other public data sources are cited in Table 1 and the reference list."),
    ("lp", "Project name", "Healthcare Affordability Burden Study: Ghana's Generation Z"),
    ("lp", "Project home page", "https://github.com/ZziemWellu/Healthcare-Affordability-Burden-Study-Ghana-Gen-Z-"),
    ("lp", "Archived version", "a Zenodo archive with a DOI will be created for the accepted version"),
    ("lp", "Operating system(s)", "platform independent"),
    ("lp", "Programming language", "Python 3"),
    ("lp", "Other requirements", "numpy, pandas, scipy and matplotlib (versions pinned in requirements.txt)"),
    ("lp", "License", "MIT"),
    ("lp", "Any restrictions to use by non-academics", "none for the code; the GLSS7 microdata are subject to the Ghana Statistical Service terms of use"),
    ("h2", "Competing interests"),
    ("p", "The authors declare that they have no competing interests."),
    ("h2", "Funding"),
    ("p", "This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors."),
    ("h2", "Authors' contributions"),
    ("p", "NOAP was responsible for the experiments, the analysis and drafting the manuscript. ZPW reviewed and corrected all experiments and analyses and placed the manuscript in perspective. Both authors read and approved the final manuscript."),
    ("h2", "Acknowledgements"),
    ("p", "We thank an anonymous clinician for clinical input."),
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
    ["12", "Preprint and Springer paper", "Corrected. Crossref and the medRxiv API (4 Nov 2026) show the medRxiv preprint 10.1101/2025.03.31.25324988 is by Baah-Abekah et al., not by the authors, and is not linked to the BMC Public Health paper. The 'earlier version' claim is removed; the preprint is now cited only as the source of the 12.9–20.4% SSA CHE range in Table 1. Wellu et al. 2026 is cited by DOI (online first; no volume yet).", "Done"],
    ["13", "Co-author and clinical consultant", "Ziem P. Wellu named as co-corresponding author with affiliation, ORCID and contribution statement.", "Done. ORCID for N. O. A. Prempeh still to add"],
    ["14", "Journal and status", "Target: Health Economics Review. The README claim of submission and review is incorrect and should be corrected.", "Done. README in ZziemWellu repository corrected (not submitted; target journal stated)"],
    ["15", "Reproducibility of the pipeline", "All v4 outputs are generated by analysis_v4.py from model_v4.py. The upper-bound configuration reproduces the v3 numbers exactly.", "Done"],
    ["16", "Descriptive subgroup comparisons", "Removed (Section 4.7 and the literacy hypothesis). A test needs household-level data, which are not available to the team.", "Done"],
    ["17", "Okoroh et al. 2018 author list", "The reference listed two authors; Crossref lists seven. In-text citation changed to Okoroh et al.", "Done"],
    ["18", "Journal format (Health Economics Review)", "Structured abstract without citations; Abbreviations; Declarations with the journal subheadings; numbered (Vancouver) references in order of citation; figures as separate files with titles and legends in the text. Built as manuscript/submission/.", "Done"],
    ["19", "Author decisions (4 Nov 2026)", "AI use: stated in the manuscript Declarations. Ethics: not required (secondary anonymised data). Clinician identity: not disclosed. Archive DOI: to be added at proof stage.", "Done"],
]

# ------------------------------------------------------------------ submission copy (Health Economics Review)
# Numbered (Vancouver) references in order of first citation. Author lists and journal details for every
# DOI reference were checked against Crossref on 4 Nov 2026.
VANCOUVER = {
    "Akazili, Gyapong and McIntyre 2011": "Akazili J, Gyapong J, McIntyre D. Who pays for health care in Ghana? Int J Equity Health. 2011;10:26. https://doi.org/10.1186/1475-9276-10-26.",
    "Akazili et al. 2017a": "Akazili J, Ataguba JE, Kanmiki EW, Gyapong J, Sankoh O, Oduro A, McIntyre D. Assessing the impoverishment effects of out-of-pocket healthcare payments prior to the uptake of the national health insurance scheme in Ghana. BMC Int Health Hum Rights. 2017;17:13. https://doi.org/10.1186/s12914-017-0121-7.",
    "Akazili et al. 2017b": "Akazili J, McIntyre D, Kanmiki EW, Gyapong J, Oduro A, Sankoh O, Ataguba JE. Assessing the catastrophic effects of out-of-pocket healthcare payments prior to the uptake of a nationwide health insurance scheme in Ghana. Glob Health Action. 2017;10(1):1289735. https://doi.org/10.1080/16549716.2017.1289735.",
    "Ataguba and Kabaniha 2022": "Ataguba JE, Kabaniha GA. Characterizing key misconceptions of equity in health financing for universal health coverage. Health Policy Plan. 2022;37(7):928–31. https://doi.org/10.1093/heapol/czac041.",
    "Baah-Abekah et al. 2025": "Baah-Abekah J, Ibrahim DK, Atugba TA, Theodore S, Seidu SA, Casley-Hayford D, Deborah L, Ahulu B. An analysis of household catastrophic health expenditure and food insecurity in Ghana. medRxiv. 2025. Preprint. https://doi.org/10.1101/2025.03.31.25324988.",
    "Bloomberg 2022": "Bloomberg. Ghana inflation exceeds 37% as data compilation is changed. 12 October 2022. https://www.bloomberg.com/news/articles/2022-10-12/ghana-annual-inflation-at-37-2-as-data-compilation-is-changed. Accessed 8 November 2026.",
    "MyJoyOnline 2025": "MyJoyOnline. Government raises public sector salaries, minimum wage by 9% for 2026. 10 November 2025. https://www.myjoyonline.com/government-raises-public-sector-salaries-minimum-wage-by-9-for-2026/. Accessed 8 November 2026.",
    "Finex Insights 2025": "Finex Insights. Ghana's minimum wage growth: a decade of gradual gains and sudden jumps (2015–2025). 19 August 2025. https://www.finexinsights.com/post/ghana-s-minimum-wage-growth-a-decade-of-gradual-gains-and-sudden-jumps-2015-2025. Accessed 8 November 2026.",
    "Ghana Statistical Service 2018": "Ghana Statistical Service. Ghana Living Standards Survey (GLSS VII) 2016–2017, version 01. Ref. GHA_2016_GLSS_v01_M. Accra: Ghana Statistical Service; 2018. https://microdata.statsghana.gov.gh/index.php/catalog/97. Accessed 8 November 2026.",
    "Okoroh et al. 2018": "Okoroh J, Essoun S, Seddoh A, Harris H, Weissman JS, Dsane-Selby L, Riviello R. Evaluating the impact of the national health insurance scheme of Ghana on out of pocket expenditures: a systematic review. BMC Health Serv Res. 2018;18:426. https://doi.org/10.1186/s12913-018-3249-9.",
    "Pharmexcil 2020": "Pharmaceuticals Export Promotion Council of India (Pharmexcil). Ghana pharma market & regulatory report. Hyderabad: Pharmexcil; 2020. https://pharmexcil.com/uploads/countryreports/Ghana_Market_Regulatory_report2020.pdf. Accessed 8 November 2026.",
    "Prempeh and Wellu 2026": "Prempeh NOA, Wellu PZ. Healthcare affordability burden study: Ghana's Generation Z (code, outputs and run pipeline). GitHub; 2026. https://github.com/ZziemWellu/Healthcare-Affordability-Burden-Study-Ghana-Gen-Z-. Accessed 8 November 2026.",
    "Sataru, Twumasi-Ankrah and Seddoh 2022": "Sataru F, Twumasi-Ankrah K, Seddoh A. An analysis of catastrophic out-of-pocket health expenditures in Ghana. Front Health Serv. 2022;2:706216. https://doi.org/10.3389/frhs.2022.706216.",
    "Trading Economics 2026": "Trading Economics. Ghana inflation rate. https://tradingeconomics.com/ghana/inflation-cpi. Accessed 8 November 2026.",
    "Wellu et al. 2026": "Wellu PZ, Redeemer A, Peprah MA, Amakye D, Agyemang EP, Peprah P, Agyemang-Duah W. Catastrophic health expenditure and household food insecurity among older adults with health conditions in Ghana: a cross-sectional analysis. BMC Public Health. 2026. https://doi.org/10.1186/s12889-026-28188-1.",
    "WHO Regional Office for Africa 2023": "WHO Regional Office for Africa. Ghana: universal health coverage/communicable and non-communicable diseases (country profile). Brazzaville: WHO Regional Office for Africa; 2023. https://www.afro.who.int/sites/default/files/2023-08/Ghana.pdf. Accessed 8 November 2026.",
    "Agyekum et al. 2023": "Agyekum EO, Ngetich E, Smith O, Wang Sonne SE, Chen D, Corral Rodas PA. Public health expenditure for universal health coverage in Ghana. Health, Nutrition and Population Discussion Paper. Washington, DC: World Bank; 2023. https://hdl.handle.net/10986/41148.",
    "World Bank, n.d.": "World Bank. Out-of-pocket expenditure (% of current health expenditure) – Ghana. World Bank Open Data. https://data.worldbank.org/indicator/SH.XPD.OOPC.CH.ZS?locations=GH. Accessed 4 November 2026.",
}
# narrative citations: "Okoroh et al. (2018) reviewed" -> "Okoroh et al. [n] reviewed"
NARRATIVE = {
    "Okoroh et al. (2018)": ("Okoroh et al.", "Okoroh et al. 2018"),
    "Sataru, Twumasi-Ankrah and Seddoh (2022)": ("Sataru et al.", "Sataru, Twumasi-Ankrah and Seddoh 2022"),
}


def to_numbered(blocks):
    """Replace author-year citations with [n] in order of first appearance; return (blocks, ordered keys)."""
    order = []

    def num(key):
        if key not in order:
            order.append(key)
        return order.index(key) + 1

    def fmt(ns):
        ns = sorted(set(ns)); out = []; i = 0
        while i < len(ns):
            j = i
            while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
                j += 1
            out.append(f"{ns[i]}–{ns[j]}" if j - i >= 2 else ", ".join(str(n) for n in ns[i:j + 1]))
            i = j + 1
        return "[" + ", ".join(out) + "]"

    def conv(text):
        if not isinstance(text, str):
            return text
        # one left-to-right pass so numbers follow the order of first appearance
        narr = "|".join(re.escape(k) for k in NARRATIVE)
        bare = "|".join(re.escape(k) for k in sorted(VANCOUVER, key=len, reverse=True))

        def one(m):
            if m.group("narr"):
                name, key = NARRATIVE[m.group("narr")]
                return f"{name} [{num(key)}]"
            if m.group("par") is not None:
                parts = [x.strip() for x in m.group("par").split(";")]
                if all(x in VANCOUVER for x in parts):
                    return (" " if m.group(0).startswith(" ") else "") + fmt([num(x) for x in parts])
                lead = " " if m.group(0).startswith(" ") else ""
                return lead + "(" + conv(m.group("par")) + ")"   # mixed text: convert citations inside
            return f"[{num(m.group('bare'))}]"     # bare citation, e.g. in a table cell
        text = re.sub(rf"(?P<narr>{narr})| ?\((?P<par>[^()]*)\)|(?P<bare>{bare})", one, text)
        # merge adjacent groups such as "[13]; [14]" -> "[13, 14]"
        while re.search(r"\[([\d, –]+)\]; \[([\d, –]+)\]", text):
            text = re.sub(r"\[([\d, –]+)\]; \[([\d, –]+)\]", r"[\1, \2]", text, count=1)
        return text

    out = []
    for b in blocks:
        if b[0] == "refs":
            continue
        if b[0] == "table":
            _, cap, header, rows = b[:4]
            out.append(("table", conv(cap), [conv(h) for h in header], [[conv(str(v)) for v in r] for r in rows]) + tuple(conv(x) for x in b[4:]))
        elif b[0] == "fig":
            out.append((b[0], b[1], b[2], conv(b[3])))
        elif b[0] == "lp":
            out.append((b[0], b[1], conv(b[2])))
        else:
            out.append((b[0], conv(b[1])) + tuple(b[2:]))
    return out, order


def build_submission():
    import shutil
    sub = os.path.join(MS, "submission"); os.makedirs(sub, exist_ok=True)
    blocks, order = to_numbered(MANUSCRIPT)
    missing = set(VANCOUVER) - set(order)
    assert not missing, f"references never cited: {missing}"
    strings = [x for b in blocks for x in (
        [b[1]] + b[2] + [c for r in b[3] for c in r] + list(b[4:]) if b[0] == "table" else [y for y in b[1:] if isinstance(y, str)])]
    bad = [x for x in strings if "[[" in x]
    assert not bad, f"unresolved [[...]] placeholder in submission text: {bad[:3]}"
    leftover = re.findall(r"[A-Z][A-Za-z\-]+(?: et al\.)?,? (?:and [A-Z][A-Za-z\-]+ )?\(?(?:19|20)\d\d[ab]?\)?", " ".join(strings))
    leftover = [x for x in leftover if not re.match(r"(GLSS|AHIES|Figure|Table|Section)", x)]
    if leftover:
        print("check possible unconverted citations:", leftover)
    lines = [f"{i}. {VANCOUVER[k]}" for i, k in enumerate(order, 1)]
    blocks.append(("h1", "References"))
    blocks += [("p", l) for l in lines]
    # figures: separate files numbered as in the text
    n = 0
    for b in blocks:
        if b[0] == "fig":
            n += 1
            label, title, _ = fig_parts(b[3])
            assert label == f"Figure {n}", (label, n)
            assert len(title.split()) <= 15, f"{label} title over 15 words: {title}"
            shutil.copyfile(os.path.join(FIG, b[1]), os.path.join(sub, f"Figure{n}.png"))
    for b in blocks:
        if b[0] == "table":
            title = b[1].split(". ", 1)[1].rstrip(".")
            assert len(title.split()) <= 15, f"table title over 15 words: {title}"
            assert not any(re.search(r"\d,\d{3}", str(c)) for r in b[3] for c in r), f"thousands comma in {b[1]}"
    build(blocks, os.path.join(sub, "Manuscript_HER_submission.docx"), figures_inline=True, journal=True)
    print(f"{len(order)} references, {n} figure files in {sub}")


def main():
    build_submission()
    build(MANUSCRIPT, os.path.join(MS, "Revised_manuscript_v4.docx"),
          banner="REVISED MANUSCRIPT (v4) FOR AUTHOR REVIEW. Numbers are generated from outputs/v4 at build time. Highlighted items must be resolved before submission to Health Economics Review.")
    build([("title", "Issue log (v4): Gen Z healthcare affordability manuscript"),
           ("table", "Issues raised in review and their status", ["#", "Item", "What changed", "Status"], ISSUE_LOG)],
          os.path.join(MS, "Issue_log_v4.docx"))

if __name__ == "__main__":
    main()
