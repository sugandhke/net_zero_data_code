"""
extended_robustness.py — additional reviewer-proofing analyses on the headline
GHG result (ln GHG per capita, Callaway–Sant'Anna, never-treated controls).

Adds to robustness_ghg.py:
  (1) Extended specification suite:
        - anticipation = 1 year
        - exclude COVID years 2020-2021 (keep 2022-24; unbalanced CS)
        - exclude Europe (result should weaken -> honest heterogeneity)
        - drop countries that later reversed their target
        - broader treatment coding (any neutrality-type target)
        - total (not per-capita) GHG
        - consumption-based CO2 per capita (carbon-leakage test)
        - corrected doubly-robust CS: baseline-2012 covariates, complete case
  (2) Permutation (randomisation) inference: reassign adoption cohorts across
      countries, preserving cohort sizes; empirical p-value for the ATT.
  (3) HonestDiD (Rambachan & Roth 2023) relative-magnitudes sensitivity on the
      2019-cohort event study (TWFE, never-treated controls), reporting robust
      CIs for the average post-adoption effect as a multiple (Mbar) of the
      largest pre-period deviation.
  (4) Raw-trends export: mean ln GHG pc by treated/never-treated, for the
      descriptive figure.

Outputs: tables/robustness_extended.csv, tables/permutation_test.json,
         tables/permutation_draws.csv, tables/honestdid_sensitivity.csv,
         tables/raw_trends.csv, tables/eventstudy_2x2.csv
"""
import warnings, json
import numpy as np, pandas as pd
from csdid.att_gt import ATTgt
import pyfixest as pf
warnings.filterwarnings("ignore"); np.random.seed(20260612)

YMIN = 2012; Y = "ln_ghgpc"
p = pd.read_csv("out/analysis_panel.csv")
p = p[(p.year >= YMIN) & (~p.self_achieved)].copy()
p.loc[p.first_treat > 2024, "first_treat"] = 0
p["ln_ghg_total"] = np.log((p.ghg_per_capita * p.population)
                           .where(p.ghg_per_capita > 0))

def stars(b, s):
    z = abs(b / s) if s else 0
    return "***" if z > 2.576 else "**" if z > 1.96 else "*" if z > 1.645 else ""
def pct(b): return 100 * (np.exp(b) - 1)

def bal(df, y, ymax, covs=None):
    cols = ["country_id", "iso3", "year", "first_treat", y] + (covs or [])
    d = df.loc[df.year.between(YMIN, ymax), cols].dropna(subset=[y]).copy()
    d.loc[d.first_treat > ymax, "first_treat"] = 0
    nyr = d.year.nunique()
    c = d.groupby("country_id")["year"].count()
    return d[d.country_id.isin(c[c == nyr].index)]

def ymx(df, y, n=55):
    ok = df.groupby("year")[y].count(); v = ok[ok >= n].index
    return int(min(v.max(), 2024)) if len(v) else 2020

def cs(df, y, ymax, ctrl="nevertreated", anticipation=0, xcovs=None,
       balanced=True, bstrap=True):
    d = bal(df, y, ymax, covs=xcovs) if balanced else \
        df.loc[df.year.between(YMIN, ymax)].dropna(subset=[y]).copy()
    if not balanced:
        d.loc[d.first_treat > ymax, "first_treat"] = 0
    xf = (f"{y}~" + "+".join(xcovs)) if xcovs else f"{y}~1"
    m = ATTgt(yname=y, gname="first_treat", idname="country_id", tname="year",
              xformla=xf, data=d, control_group=ctrl, anticipation=anticipation,
              panel=balanced, allow_unbalanced_panel=not balanced
              ).fit(est_method="dr" if xcovs else "reg", bstrap=bstrap)
    m.aggte(typec="group", bstrap=bstrap, cband=bstrap, na_rm=True)
    a = m.atte; f = lambda x: float(np.atleast_1d(np.asarray(x, float))[0])
    return f(a["overall_att"]), f(a["overall_se"]), int(d.country_id.nunique())

rows = []
def add(name, b, s, n, note=""):
    rows.append({"spec": name, "att": round(b, 4), "se": round(s, 4),
                 "effect_pct": round(pct(b), 1), "sig": stars(b, s),
                 "cell": f"{pct(b):+.1f}%{stars(b, s)}", "n_countries": n,
                 "note": note})
    print(f"  {name:44s} {pct(b):+6.1f}%{stars(b, s):3s} (se {s:.4f}, {n} countries)")

YM = ymx(p, Y)
print("=== EXTENDED ROBUSTNESS (ln GHG pc) ===")

b, s, n = cs(p, Y, YM); add("Baseline (CS, never-treated)", b, s, n)
b, s, n = cs(p, Y, YM, anticipation=1); add("Anticipation: 1 year", b, s, n)

try:
    b, s, n = cs(p[~p.year.isin([2020, 2021])], Y, YM, balanced=False)
    add("Exclude COVID years (2020-2021)", b, s, n, "unbalanced CS")
except Exception as e:
    print("  unbalanced CS failed:", repr(e))
    d = p[(p.first_treat == 0) | (p.first_treat == 2019)]
    d = d[~d.year.isin([2020, 2021])].copy()
    d = bal(d, Y, YM)
    d["did2"] = ((d.first_treat == 2019) & (d.year >= 2019)).astype(int)
    m = pf.feols(f"{Y} ~ did2 | country_id + year", data=d,
                 vcov={"CRV1": "country_id"})
    add("Exclude COVID years (2020-2021)", float(m.coef()["did2"]),
        float(m.se()["did2"]), int(d.country_id.nunique()), "2x2 TWFE")

b, s, n = cs(p[p.continent != "Europe"], Y, YM)
add("Exclude Europe", b, s, n)
b, s, n = cs(p[~p.target_reversed.astype(bool)], Y, YM)
add("Drop later-reversed targets", b, s, n)

pa = p.copy()
pa["first_treat"] = pa["adopt_year_any"].fillna(0).astype(int)
pa.loc[pa.first_treat > 2024, "first_treat"] = 0
b, s, n = cs(pa, Y, ymx(pa, Y))
add("Broad coding: any neutrality-type target", b, s, n)

b, s, n = cs(p, "ln_ghg_total", ymx(p, "ln_ghg_total"))
add("Total GHG (not per capita)", b, s, n)
b, s, n = cs(p, "ln_conspc", ymx(p, "ln_conspc"))
add("Consumption-based CO2 pc (leakage test)", b, s, n)

# corrected covariate-adjusted CS: covariates frozen at baseline 2012 values,
# complete cases only (no mean imputation), doubly robust
CS_COVS = ["ln_pop", "urban_pct", "trade_pct_gdp", "industry_pct_gdp",
           "ln_energy_int", "v2x_polyarchy", "v2x_rule"]
bl = p[p.year == YMIN].set_index("iso3")[CS_COVS].add_suffix("_b0")
pb = p.merge(bl, left_on="iso3", right_index=True, how="left")
B0 = [c + "_b0" for c in CS_COVS]
pb = pb.dropna(subset=B0)
b, s, n = cs(pb, Y, YM, xcovs=B0)
add("Covariate-adjusted CS (DR, baseline-2012 X)", b, s, n, "complete case")

pd.DataFrame(rows).to_csv("tables/robustness_extended.csv", index=False)

# ---------------------------------------------------------------------------
# (2) PERMUTATION INFERENCE
# ---------------------------------------------------------------------------
print("\n=== PERMUTATION INFERENCE (200 draws) ===")
d0 = bal(p, Y, YM)
obs, _, _ = cs(d0, Y, YM, bstrap=False)
assign = d0.groupby("country_id")["first_treat"].first()
draws = []
rng = np.random.default_rng(20260612)
for it in range(200):
    perm = pd.Series(rng.permutation(assign.values), index=assign.index)
    dd = d0.copy(); dd["first_treat"] = dd.country_id.map(perm)
    try:
        bb, _, _ = cs(dd, Y, YM, bstrap=False)
        draws.append(bb)
    except Exception:
        continue
draws = np.array(draws)
pval = float(np.mean(np.abs(draws) >= abs(obs)))
print(f"observed ATT {obs:+.4f}; permutation p = {pval:.3f} ({len(draws)} draws)")
pd.DataFrame({"draw_att": draws}).to_csv("tables/permutation_draws.csv", index=False)
json.dump({"observed_att": obs, "p_value": pval, "n_draws": int(len(draws))},
          open("tables/permutation_test.json", "w"), indent=1)

# ---------------------------------------------------------------------------
# (3) HONESTDID sensitivity on the 2019-cohort TWFE event study
# ---------------------------------------------------------------------------
print("\n=== HONESTDID (relative magnitudes) ===")
d2 = p[(p.first_treat == 0) | (p.first_treat == 2019)].copy()
d2 = bal(d2, Y, YM)
d2["treat"] = (d2.first_treat == 2019).astype(int)
d2["evt"] = np.where(d2.treat == 1, d2.year - 2019, -1000)
evs = sorted(e for e in set(d2.loc[d2.treat == 1, "evt"]) if e != -1)
names = []
for e in evs:
    nm = f"e_{e:+d}".replace("+", "p").replace("-", "m")
    d2[nm] = ((d2.treat == 1) & (d2.evt == e)).astype(int)
    names.append(nm)
m = pf.feols(f"{Y} ~ {' + '.join(names)} | country_id + year", data=d2,
             vcov={"CRV1": "country_id"})
beta = m.coef().loc[names].values
V = m._vcov  # full cluster-robust vcov, same order as coefficients
es = pd.DataFrame({"event_time": evs, "att": beta,
                   "se": m.se().loc[names].values})
es.to_csv("tables/eventstudy_2x2.csv", index=False)
npre = sum(1 for e in evs if e < -1); npost = len(evs) - npre
from honestdid import createSensitivityResults_relativeMagnitudes, constructOriginalCS
l_avg = np.ones(npost) / npost
orig = constructOriginalCS(betahat=beta, sigma=V, numPrePeriods=npre,
                           numPostPeriods=npost, l_vec=l_avg)
sens = createSensitivityResults_relativeMagnitudes(
    betahat=beta, sigma=V, numPrePeriods=npre, numPostPeriods=npost,
    l_vec=l_avg, Mbarvec=[0.5, 1.0, 1.5, 2.0])
out = pd.DataFrame(sens)
out.to_csv("tables/honestdid_sensitivity.csv", index=False)
print("original 95% CI for avg post effect:", orig)
print(out.to_string(index=False))

# ---------------------------------------------------------------------------
# (4) RAW TRENDS export
# ---------------------------------------------------------------------------
d0 = bal(p, Y, YM)
d0["group"] = np.where(d0.first_treat == 2019, "2019 adopters",
                np.where(d0.first_treat == 0, "Never treated", "Other cohorts"))
tr = (d0[d0.group != "Other cohorts"]
      .groupby(["group", "year"])[Y].mean().reset_index())
base = tr[tr.year == 2018].set_index("group")[Y]
tr["indexed"] = tr.apply(lambda r: r[Y] - base[r.group], axis=1)
tr.to_csv("tables/raw_trends.csv", index=False)
print("\nsaved tables/robustness_extended.csv, permutation_*, honestdid_sensitivity.csv, raw_trends.csv, eventstudy_2x2.csv")
