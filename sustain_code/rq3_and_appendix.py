"""
rq3_and_appendix.py — (1) RQ3 air-quality table: CS ATT of net-zero adoption on
PM2.5 exposure, PM2.5 damage and clean-cooking access, plus the PM2.5-GHG
correlation for the prose; (2) Appendix: cross-sectional determinants of
adoption (selection-into-treatment table) on baseline-2012 covariates.

Outputs: tables/airquality_rq3.csv, tables/airquality_meta.json,
         tables/adoption_determinants.csv, tables/cohort_countries.json
"""
import warnings, json
import numpy as np, pandas as pd
from csdid.att_gt import ATTgt
import pyfixest as pf
warnings.filterwarnings("ignore"); np.random.seed(20260612)

YMIN = 2012
p = pd.read_csv("out/analysis_panel.csv")
p = p[(p.year >= YMIN) & (~p.self_achieved)].copy()
p.loc[p.first_treat > 2024, "first_treat"] = 0

def stars(b, s):
    z = abs(b / s) if s else 0
    return "***" if z > 2.576 else "**" if z > 1.96 else "*" if z > 1.645 else ""

def bal(df, y, ymax):
    cols = ["country_id", "iso3", "year", "first_treat", y]
    d = df.loc[df.year.between(YMIN, ymax), cols].dropna(subset=[y]).copy()
    d.loc[d.first_treat > ymax, "first_treat"] = 0
    c = d.groupby("country_id")["year"].count()
    return d[d.country_id.isin(c[c == d.year.nunique()].index)]

def ymx(y, n=55):
    ok = p.groupby("year")[y].count(); v = ok[ok >= n].index
    return int(min(v.max(), 2024)) if len(v) else 2020

def cs(y, ymax):
    d = bal(p, y, ymax)
    m = ATTgt(yname=y, gname="first_treat", idname="country_id", tname="year",
              xformla=f"{y}~1", data=d, control_group="nevertreated"
              ).fit(est_method="reg", bstrap=True)
    m.aggte(typec="group", bstrap=True, cband=True, na_rm=True)
    a = m.atte; f = lambda x: float(np.atleast_1d(np.asarray(x, float))[0])
    return f(a["overall_att"]), f(a["overall_se"]), d, ymax

# ---------------------------------------------------------------- (1) RQ3 table
print("=== RQ3: air-quality outcomes ===")
rows = []
OUTS = [("ln_pm25", "PM2.5 exposure (ln, pop-weighted µg/m³)", "pct"),
        ("pm_damage_gni", "PM2.5 damage (% of GNI)", "pp"),
        ("clean_cook_pct", "Clean-cooking access (% population)", "pp")]
for y, lab, unit in OUTS:
    if y not in p.columns: continue
    ym = ymx(y)
    b, s, d, ym = cs(y, ym)
    if unit == "pct":
        eff = f"{100*(np.exp(b)-1):+.1f}%"
    else:
        eff = f"{b:+.2f} pp"
    ci_lo, ci_hi = b - 1.96 * s, b + 1.96 * s
    if unit == "pct":
        ci = f"({100*(np.exp(ci_lo)-1):+.1f}, {100*(np.exp(ci_hi)-1):+.1f})"
    else:
        ci = f"({ci_lo:+.2f}, {ci_hi:+.2f})"
    rows.append({"outcome": lab, "att": round(b, 4), "se": round(s, 4),
                 "effect": eff, "ci": ci, "sig": stars(b, s),
                 "n_countries": int(d.country_id.nunique()),
                 "n_obs": int(len(d)), "window": f"{YMIN}-{ym}"})
    print(f"  {lab:44s} {eff}{stars(b,s):3s} {ci}  [{YMIN}-{ym}, {d.country_id.nunique()} countries]")
pd.DataFrame(rows).to_csv("tables/airquality_rq3.csv", index=False)

dd = p[["pm25", "co2_per_capita", "ghg_per_capita"]].dropna()
meta = {"corr_pm25_co2pc": round(float(dd.pm25.corr(dd.co2_per_capita)), 3),
        "corr_pm25_ghgpc": round(float(dd.pm25.corr(dd.ghg_per_capita)), 3),
        "corr_n": int(len(dd))}
json.dump(meta, open("tables/airquality_meta.json", "w"), indent=1)
print("  correlations:", meta)

# -------------------------------------- (2) determinants of adoption (appendix)
print("\n=== Appendix: determinants of adoption (baseline-2012 cross-section) ===")
bl = p[p.year == YMIN].copy()
bl["adopted"] = (bl.first_treat > 0).astype(float)
bl["ln_gdppc_ppp"] = np.log(bl["gdp_pc_ppp"].where(bl["gdp_pc_ppp"] > 0))
XV = [("ln_gdppc_ppp", "Log GDP per capita (PPP, 2012)"),
      ("ln_ghgpc", "Log GHG per capita (2012)"),
      ("ln_pop", "Log population (2012)"),
      ("urban_pct", "Urbanisation (%, 2012)"),
      ("trade_pct_gdp", "Trade openness (% GDP, 2012)"),
      ("industry_pct_gdp", "Industry (% GDP, 2012)"),
      ("ln_energy_int", "Energy intensity (ln, 2012)"),
      ("v2x_polyarchy", "Electoral democracy (2012)"),
      ("v2x_rule", "Rule of law (2012)")]
xcols = [c for c, _ in XV]
cs_d = bl[["iso3", "adopted"] + xcols].dropna().copy()
m = pf.feols("adopted ~ " + " + ".join(xcols), data=cs_d, vcov="HC1")
co, se = m.coef(), m.se()
det = []
for c, lab in XV:
    b, s = float(co[c]), float(se[c])
    det.append({"variable": lab, "coef": f"{b:+.3f}{stars(b, s)}",
                "se": f"({s:.3f})"})
det.append({"variable": "Observations (countries)", "coef": str(len(cs_d)), "se": ""})
det.append({"variable": "R²", "coef": f"{float(m._r2):.3f}", "se": ""})
pd.DataFrame(det).to_csv("tables/adoption_determinants.csv", index=False)
for r in det: print(f"  {r['variable']:34s} {r['coef']:>10s} {r['se']}")

# -------------------------------------- (3) cohort country lists (appendix)
ad = pd.read_csv("tables/adoption_countries.csv")
ad = ad[ad.adopted == 1]
def bucket(ft):
    ft = int(ft)
    if ft <= 2018: return "Pre-2019"
    if ft == 2019: return "2019 (COP25 wave)"
    if ft <= 2021: return "2020-2021"
    return "2022 or later"
ad["bucket"] = ad.first_treat.map(bucket)
never = pd.read_csv("tables/adoption_countries.csv")
groups = {b: sorted(g.country.tolist()) for b, g in ad.groupby("bucket")}
groups["Never adopted"] = sorted(never[never.adopted == 0].country.tolist())
json.dump(groups, open("tables/cohort_countries.json", "w"), indent=1)
print("\ncohort list sizes:", {k: len(v) for k, v in groups.items()})
print("saved tables/airquality_rq3.csv, adoption_determinants.csv, cohort_countries.json")
