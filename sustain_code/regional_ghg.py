"""
regional_ghg.py — RQ2 continent heterogeneity (CS + DiD) and regional event studies.
Outputs:
  tables/regional_ghg.csv      (per-continent CS & DiD on CO2 pc and GHG pc)
  tables/regional_eventstudy.csv (CS dynamic ATT by continent, for Figure 3)
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

def stars(b,s):
    z=abs(b/s) if s else 0
    return "***" if z>2.576 else "**" if z>1.96 else "*" if z>1.645 else ""
def bal(df,y,ymax):
    cols=["country_id","iso3","year","first_treat",y,"continent"]
    d=df.loc[df.year.between(YMIN,ymax),cols].dropna(subset=[y]).copy()
    d.loc[d.first_treat>ymax,"first_treat"]=0
    c=d.groupby("country_id")["year"].count()
    return d[d.country_id.isin(c[c==ymax-YMIN+1].index)]
def ymx(y,n=55):
    ok=p.groupby("year")[y].count(); v=ok[ok>=n].index
    return int(min(v.max(),2024)) if len(v) else 2020

def cs_region(d,y):
    d=d.copy()
    # need both treated and never-treated within region
    if d.first_treat.gt(0).sum()==0 or d.first_treat.eq(0).sum()==0: return None
    try:
        m=ATTgt(yname=y,gname="first_treat",idname="country_id",tname="year",xformla=f"{y}~1",
                data=d,control_group="nevertreated").fit(est_method="reg",bstrap=True)
        m.aggte(typec="group",bstrap=True,cband=True,na_rm=True)
        a=m.atte; f=lambda x:float(np.atleast_1d(np.asarray(x,float))[0])
        return f(a["overall_att"]),f(a["overall_se"])
    except Exception: return None

def cs_region_dyn(d,y):
    d=d.copy()
    if d.first_treat.gt(0).sum()==0 or d.first_treat.eq(0).sum()==0: return None
    try:
        m=ATTgt(yname=y,gname="first_treat",idname="country_id",tname="year",xformla=f"{y}~1",
                data=d,control_group="nevertreated").fit(est_method="reg",bstrap=True)
        m.aggte(typec="dynamic",min_e=-5,max_e=5,bstrap=True,cband=True,na_rm=True)
        a=m.atte
        fl=lambda x:np.asarray(x,float).ravel()
        e,att,se=fl(a["egt"]),fl(a["att_egt"]),fl(a["se_egt"])
        n=min(len(e),len(att),len(se))
        return pd.DataFrame({"event_time":e[:n].astype(int),"att":att[:n],"se":se[:n]})
    except Exception: return None

def did_region(d,y):
    d=d[(d.first_treat==0)|(d.first_treat==2019)].copy()
    if d.first_treat.eq(2019).sum()==0: return None
    d["treat"]=(d.first_treat==2019).astype(int); d["post"]=(d.year>=2019).astype(int)
    d["did2"]=d.treat*d.post
    try:
        m=pf.feols(f"{y} ~ did2 | country_id + year",data=d,vcov={"CRV1":"country_id"})
        return float(m.coef()["did2"]),float(m.se()["did2"])
    except Exception: return None

CONTS=["Europe","Asia","Africa","North America","South America","Oceania"]
rows=[]; dyn=[]
for y,short in [("ln_co2pc","CO2"),("ln_ghgpc","GHG")]:
    ym=ymx(y); base=bal(p,y,ym)
    for cont in CONTS:
        d=base[base.continent==cont]
        nt=d.first_treat.gt(0).groupby(d.country_id).max().sum()
        cs=cs_region(d,y); di=did_region(d,y)
        rows.append({"outcome":short,"continent":cont,"treated_n":int(nt),
                     "cs_att":(cs[0] if cs else np.nan),"cs_se":(cs[1] if cs else np.nan),
                     "cs_sig":(stars(*cs) if cs else ""),
                     "did_att":(di[0] if di else np.nan),"did_se":(di[1] if di else np.nan),
                     "did_sig":(stars(*di) if di else "")})
    if y=="ln_ghgpc":
        for cont in CONTS:
            d=base[base.continent==cont]
            ev=cs_region_dyn(d,y)
            if ev is not None:
                ev["continent"]=cont; dyn.append(ev)

reg=pd.DataFrame(rows)
reg.to_csv("tables/regional_ghg.csv",index=False)
if dyn: pd.concat(dyn).to_csv("tables/regional_eventstudy.csv",index=False)
print(reg.to_string(index=False))
print("\nsaved tables/regional_ghg.csv, regional_eventstudy.csv")
