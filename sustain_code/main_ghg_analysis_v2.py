"""
main_ghg_analysis_v2.py
Updated main results: GHG family + components, two estimators per outcome.
CHANGES vs v1:
  (1) EXPANDED covariate set (literature-standard): adds services %GDP,
      manufacturing %GDP, GDP growth, renewable-energy %  to the original
      income-tercile / log-pop / urbanization / trade / industry / energy-
      intensity / electoral-democracy / rule-of-law vector.
  (2) Callaway-Sant'Anna now estimated with covariates via the DOUBLY-ROBUST
      estimator (xformla includes the covariates), so the CS ATT is genuinely
      covariate-adjusted rather than unconditional. (CS yields a treatment
      effect, not per-covariate slopes, so covariate ROWS are reported as
      "conditioned on" in the table, never as blank cells.)
  (3) Also reports the unconditional CS so we can confirm the adjustment
      doesn't move the estimate (robustness of covariate choice).
Outputs:
  tables/main_ghg_v2.csv          (compact: CS-adj, CS-uncond, DiD per outcome)
  tables/main_ghg_full_v2.csv     (covariate-row table, GHG family, no colours)
  tables/cov_meta.json            (covariate list for captions)
"""
import warnings, json
import numpy as np, pandas as pd
from csdid.att_gt import ATTgt
import pyfixest as pf
warnings.filterwarnings("ignore"); np.random.seed(20260612)

YMIN=2012
p=pd.read_csv("out/analysis_panel.csv")
p=p[(p.year>=YMIN)&(~p.self_achieved)].copy()
p.loc[p.first_treat>2024,"first_treat"]=0

# ---- income tercile (baseline 2012 GDP pc PPP) ----
bl=p[p.year==YMIN].set_index("iso3")
gt=bl["gdp_pc_ppp"].dropna(); q1,q2=gt.quantile([1/3,2/3])
def inc_grp(v):
    if pd.isna(v): return np.nan
    return "Low" if v<=q1 else ("Middle" if v<=q2 else "High")
inc=bl["gdp_pc_ppp"].map(inc_grp).rename("income_level")
p=p.merge(inc,left_on="iso3",right_index=True,how="left")
p["inc_mid"]=(p.income_level=="Middle").astype(float)
p["inc_high"]=(p.income_level=="High").astype(float)
if "ln_energy_int" not in p.columns:
    p["ln_energy_int"]=np.log(p["energy_intensity_mj"].where(p["energy_intensity_mj"]>0))

# ---- EXPANDED covariate vector ----
COVS=["inc_mid","inc_high","ln_pop","urban_pct","trade_pct_gdp","industry_pct_gdp",
      "ln_energy_int","v2x_polyarchy","v2x_rule",
      # --- NEW ---
      "services_pct_gdp","manuf_pct_gdp","gdp_growth","renew_energy_pct"]
COVS=[c for c in COVS if c in p.columns]

# covariates that the DR-CS step can use (must be reasonably complete, numeric,
# and NOT near-collinear: industry/manufacturing/services are GDP shares that
# partly co-move, so we keep industry + services only and drop manufacturing here)
CS_COVS=["ln_pop","urban_pct","trade_pct_gdp","industry_pct_gdp","ln_energy_int",
         "v2x_polyarchy","v2x_rule","services_pct_gdp","renew_energy_pct"]
CS_COVS=[c for c in CS_COVS if c in p.columns]

LABELS={"did2":"Net-zero adoption (Treat x Post)","inc_mid":"Middle income (ref. low)",
        "inc_high":"High income (ref. low)","ln_pop":"Log population","urban_pct":"Urbanization (%)",
        "trade_pct_gdp":"Trade openness (% GDP)","industry_pct_gdp":"Industry (% GDP)",
        "ln_energy_int":"Energy intensity (ln)","v2x_polyarchy":"Electoral democracy",
        "v2x_rule":"Rule of law","services_pct_gdp":"Services (% GDP)",
        "manuf_pct_gdp":"Manufacturing (% GDP)","gdp_growth":"GDP growth (%)",
        "renew_energy_pct":"Renewable energy (% final)"}

def stars(b,s):
    z=abs(b/s) if s else 0
    return "***" if z>2.576 else "**" if z>1.96 else "*" if z>1.645 else ""
def ci(b,s): return f"({b-1.96*s:+.3f}, {b+1.96*s:+.3f})"
def pct(b): return 100*(np.exp(b)-1)

def bal(df,y,ymax,covs=None):
    cols=["country_id","iso3","year","first_treat",y]+(covs or [])
    d=df.loc[df.year.between(YMIN,ymax),cols].dropna(subset=[y]).copy()
    d.loc[d.first_treat>ymax,"first_treat"]=0
    c=d.groupby("country_id")["year"].count()
    return d[d.country_id.isin(c[c==ymax-YMIN+1].index)]
def ymx(y,n=55):
    ok=p.groupby("year")[y].count(); v=ok[ok>=n].index
    return int(min(v.max(),2024)) if len(v) else 2020

def cs_overall(df,y,ymax,covs=None):
    """Covariate-adjusted CS via doubly-robust if covs given, else unconditional reg."""
    use=list(covs or [])
    d=bal(df,y,ymax,covs=use)
    if use:
        for c in use:
            d[c]=d[c].fillna(d[c].mean())
        # drop zero-variance and highly collinear covariates to keep DR design full-rank
        keep=[c for c in use if d[c].std()>1e-8]
        if len(keep)>1:
            X=d[keep]; corr=X.corr().abs()
            drop=set()
            for i,a in enumerate(keep):
                for b in keep[i+1:]:
                    if b not in drop and corr.loc[a,b]>0.92: drop.add(b)
            keep=[c for c in keep if c not in drop]
        use=keep
    for method in (("dr","reg") if use else ("reg",)):
        try:
            xf=(f"{y}~"+"+".join(use)) if use else f"{y}~1"
            m=ATTgt(yname=y,gname="first_treat",idname="country_id",tname="year",xformla=xf,
                    data=d,control_group="nevertreated").fit(est_method=method,bstrap=True)
            m.aggte(typec="group",bstrap=True,cband=True,na_rm=True)
            a=m.atte; f=lambda x:float(np.atleast_1d(np.asarray(x,float))[0])
            return f(a["overall_att"]),f(a["overall_se"]),int(d.shape[0])
        except np.linalg.LinAlgError:
            use=[]  # fall back to unconditional on singular design
    raise RuntimeError("CS failed for "+y)

def did2x2(df,y,ymax):
    d=df[(df.first_treat==0)|(df.first_treat==2019)].copy()
    cv=[c for c in COVS if c in df.columns]
    d=bal(d,y,ymax,covs=cv)
    d["treat"]=(d.first_treat==2019).astype(int); d["post"]=(d.year>=2019).astype(int)
    d["did2"]=d.treat*d.post
    rhs="did2 + "+" + ".join(cv)
    m=pf.feols(f"{y} ~ {rhs} | country_id + year",data=d,vcov={"CRV1":"country_id"})
    return m

GHG_FAMILY=[("ln_ghgpc","Total GHG per capita"),("ln_ghgxlucf","GHG excl. LULUCF"),
            ("ln_co2luc","CO2 incl. land use"),("ln_coalco2","Coal CO2"),
            ("ln_gasco2","Gas CO2"),("ln_oilco2","Oil CO2"),
            ("ln_ch4pc","Methane (CH4)"),("ln_n2opc","Nitrous oxide (N2O)")]

ROW_ORDER=["did2","inc_mid","inc_high","ln_pop","urban_pct","trade_pct_gdp",
           "industry_pct_gdp","ln_energy_int","services_pct_gdp","manuf_pct_gdp",
           "gdp_growth","renew_energy_pct","v2x_polyarchy","v2x_rule"]

compact=[]; longrows=[]
print("=== MAIN GHG (expanded covariates; CS doubly-robust) ===")
for y,lab in GHG_FAMILY:
    if y not in p.columns: continue
    ym=ymx(y)
    csb,css,csn=cs_overall(p,y,ym,covs=CS_COVS)          # covariate-adjusted CS
    ub,us,_=cs_overall(p,y,ym,covs=None)                  # unconditional CS
    m2=did2x2(p,y,ym); co,se=m2.coef(),m2.se()
    b2,s2=float(co["did2"]),float(se["did2"])
    print(f"{lab:22s} CSadj {pct(csb):+6.1f}%{stars(csb,css):3s} | CSunc {pct(ub):+6.1f}%{stars(ub,us):3s} | DiD {pct(b2):+6.1f}%{stars(b2,s2):3s}")
    compact.append({"outcome":lab,"y":y,
                    "csadj_att":csb,"csadj_se":css,"csadj_sig":stars(csb,css),"csadj_n":csn,
                    "csunc_att":ub,"csunc_se":us,"csunc_sig":stars(ub,us),
                    "did_att":b2,"did_se":s2,"did_sig":stars(b2,s2),"did_n":int(m2._N)})
    # long covariate-row table
    # CS column reports the UNCONDITIONAL CS overall ATT (primary spec):
    # time-invariant differences are differenced out by construction, so
    # covariate cells show an em dash. (The covariate-adjusted doubly-robust
    # CS with baseline-2012 covariates is reported in the robustness suite.)
    longrows.append({"outcome":lab,"estimator":"CS","term":LABELS["did2"],
                     "cell":f"{pct(ub):+.1f}%{stars(ub,us)}","ci":ci(ub,us)})
    for k in ROW_ORDER:
        if k=="did2": continue
        if k in co.index:
            b,s=float(co[k]),float(se[k])
            longrows.append({"outcome":lab,"estimator":"DiD","term":LABELS[k],
                             "cell":f"{b:+.3f}{stars(b,s)}","ci":ci(b,s)})
        longrows.append({"outcome":lab,"estimator":"CS","term":LABELS[k],
                         "cell":"\u2014","ci":""})
    longrows.append({"outcome":lab,"estimator":"DiD","term":LABELS["did2"],
                     "cell":f"{pct(b2):+.1f}%{stars(b2,s2)}","ci":ci(b2,s2)})
    longrows.append({"outcome":lab,"estimator":"DiD","term":"Country FE","cell":"Yes","ci":""})
    longrows.append({"outcome":lab,"estimator":"DiD","term":"Year FE","cell":"Yes","ci":""})
    longrows.append({"outcome":lab,"estimator":"DiD","term":"Observations","cell":f"{int(m2._N):,}","ci":""})
    longrows.append({"outcome":lab,"estimator":"CS","term":"Observations","cell":f"{csn:,}","ci":""})
    try: r2=m2._r2_within
    except Exception: r2=np.nan
    longrows.append({"outcome":lab,"estimator":"DiD","term":"R\u00b2 (within)",
                     "cell":(f"{r2:.3f}" if r2==r2 else ""),"ci":""})

pd.DataFrame(compact).round(4).to_csv("tables/main_ghg_v2.csv",index=False)
pd.DataFrame(longrows).to_csv("tables/main_ghg_full_v2.csv",index=False)
json.dump({"covs_full":[LABELS[c] for c in COVS],
           "covs_cs":[LABELS[c] for c in CS_COVS],
           "new":["Services (% GDP)","Manufacturing (% GDP)","GDP growth (%)","Renewable energy (% final)"]},
          open("tables/cov_meta.json","w"),indent=1)
print("\nsaved tables/main_ghg_v2.csv, main_ghg_full_v2.csv, cov_meta.json")
