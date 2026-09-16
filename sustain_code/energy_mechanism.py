"""
energy_mechanism.py — RQ4: electricity-mix and energy mechanism (CS overall ATT).
Outputs: tables/energy_mechanism.csv
"""
import warnings
import numpy as np, pandas as pd
from csdid.att_gt import ATTgt
warnings.filterwarnings("ignore"); np.random.seed(20260612)

YMIN=2012
p=pd.read_csv("out/analysis_panel.csv")
p=p[(p.year>=YMIN)&(~p.self_achieved)].copy()
p.loc[p.first_treat>2024,"first_treat"]=0
# log energy outcomes
for src,nm in [("energy_per_capita","ln_energypc2"),("energy_intensity_mj","ln_enint2")]:
    if src in p.columns: p[nm]=np.log(p[src].where(p[src]>0))

def stars(b,s):
    z=abs(b/s) if s else 0
    return "***" if z>2.576 else "**" if z>1.96 else "*" if z>1.645 else ""
def bal(df,y,ymax):
    cols=["country_id","iso3","year","first_treat",y]
    d=df.loc[df.year.between(YMIN,ymax),cols].dropna(subset=[y]).copy()
    d.loc[d.first_treat>ymax,"first_treat"]=0
    c=d.groupby("country_id")["year"].count()
    return d[d.country_id.isin(c[c==ymax-YMIN+1].index)]
def ymx(y,n=55):
    ok=p.groupby("year")[y].count(); v=ok[ok>=n].index
    return int(min(v.max(),2024)) if len(v) else 2020
def cs(y):
    ym=ymx(y); d=bal(p,y,ym)
    m=ATTgt(yname=y,gname="first_treat",idname="country_id",tname="year",xformla=f"{y}~1",
            data=d,control_group="nevertreated").fit(est_method="reg",bstrap=True)
    m.aggte(typec="group",bstrap=True,cband=True,na_rm=True)
    a=m.atte; f=lambda x:float(np.atleast_1d(np.asarray(x,float))[0])
    return f(a["overall_att"]),f(a["overall_se"]),int(d.shape[0])

# share outcomes are in percentage points (level), energy outcomes in logs
SHARE=[("renewables_share_elec","Renewables share of electricity"),
       ("low_carbon_share_elec","Low-carbon share of electricity"),
       ("solar_share_elec","Solar share of electricity"),
       ("wind_share_elec","Wind share of electricity"),
       ("fossil_share_elec","Fossil share of electricity"),
       ("coal_share_elec","Coal share of electricity")]
LOGV=[("ln_enint2","Energy intensity of GDP (ln)"),
      ("ln_energypc2","Primary energy per capita (ln)")]

rows=[]
for y,lab in SHARE:
    if y not in p.columns: continue
    b,s,n=cs(y)
    rows.append({"outcome":lab,"att":b,"se":s,"sig":stars(b,s),"unit":"pp",
                 "effect":f"{b:+.1f} pp","n":n})
    print(f"{lab:36s} {b:+5.2f} pp {stars(b,s)}")
for y,lab in LOGV:
    if y not in p.columns: continue
    b,s,n=cs(y)
    rows.append({"outcome":lab,"att":b,"se":s,"sig":stars(b,s),"unit":"ln",
                 "effect":f"{100*(np.exp(b)-1):+.1f}%","n":n})
    print(f"{lab:36s} {100*(np.exp(b)-1):+5.1f}% {stars(b,s)}")
pd.DataFrame(rows).to_csv("tables/energy_mechanism.csv",index=False)
print("\nsaved tables/energy_mechanism.csv")
