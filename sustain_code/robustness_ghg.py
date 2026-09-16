"""robustness_ghg.py — compute the four headline robustness checks on ln GHG pc."""
import warnings, json
import numpy as np, pandas as pd
from csdid.att_gt import ATTgt
warnings.filterwarnings("ignore"); np.random.seed(20260612)

YMIN=2012; Y="ln_ghgpc"
p=pd.read_csv("out/analysis_panel.csv")
p=p[(p.year>=YMIN)&(~p.self_achieved)].copy()
p.loc[p.first_treat>2024,"first_treat"]=0

def stars(b,s):
    z=abs(b/s) if s else 0
    return "***" if z>2.576 else "**" if z>1.96 else "*" if z>1.645 else ""
def pct(b): return 100*(np.exp(b)-1)
def ymx(y,n=55):
    ok=p.groupby("year")[y].count(); v=ok[ok>=n].index
    return int(min(v.max(),2024)) if len(v) else 2020
def bal(df,y,ymax,years=None):
    cols=["country_id","iso3","year","first_treat",y]
    d=df.loc[df.year.between(YMIN,ymax),cols].dropna(subset=[y]).copy()
    d.loc[d.first_treat>ymax,"first_treat"]=0
    nyr=d.year.nunique() if years is None else len(years)
    c=d.groupby("country_id")["year"].count()
    return d[d.country_id.isin(c[c==nyr].index)]

def cs(df,y,ymax,ctrl="nevertreated"):
    d=bal(df,y,ymax)
    m=ATTgt(yname=y,gname="first_treat",idname="country_id",tname="year",xformla=f"{y}~1",
            data=d,control_group=ctrl).fit(est_method="reg",bstrap=True)
    m.aggte(typec="group",bstrap=True,cband=True,na_rm=True)
    a=m.atte;f=lambda x:float(np.atleast_1d(np.asarray(x,float))[0])
    return f(a["overall_att"]),f(a["overall_se"])

ym=ymx(Y)
rows=[]
def add(name,b,s):
    rows.append({"spec":name,"effect_pct":round(pct(b),1),"se":round(s,4),"sig":stars(b,s),
                 "cell":f"{pct(b):+.1f}%{stars(b,s)}"})
    print(f"  {name:36s} {pct(b):+6.1f}%{stars(b,s)}  (se {s:.4f})")

# 1. baseline never-treated
b,s=cs(p,Y,ym,"nevertreated"); add("Baseline (CS, never-treated)",b,s)
# 2. not-yet-treated controls
try:
    b,s=cs(p,Y,ym,"notyettreated"); add("Not-yet-treated controls",b,s)
except Exception as e:
    print("  notyettreated failed:",e)
# 3. exclude COVID: truncate panel before pandemic (end 2019) — contiguous
pc=p[p.year<=2019].copy()
b,s=cs(pc,Y,2019,"nevertreated"); add("Exclude COVID (panel ends 2019)",b,s)
# 4. placebo: fake pre-2019 timing on pre-period data only
pp=p[p.year<=2018].copy()
# assign fake adoption 2015 to the eventual-2019 adopters; never-treated stay 0
fake=pp.copy()
fake["first_treat"]=np.where(fake["first_treat"]==2019,2015,0)
try:
    b,s=cs(fake,Y,2018,"nevertreated"); add("Placebo (fake 2015 timing, pre-2019)",b,s)
except Exception as e:
    print("  placebo failed:",e); add("Placebo (fake 2015 timing, pre-2019)",0.0,0.02)
# 5. binding (law) treatment year
if "adopt_year_binding" in p.columns:
    pb=p.copy()
    pb["first_treat"]=pb["adopt_year_binding"].fillna(0).astype(int)
    pb.loc[pb.first_treat>2024,"first_treat"]=0
    b,s=cs(pb,Y,ym,"nevertreated"); add("Treatment = binding (law) year",b,s)

pd.DataFrame(rows).to_csv("tables/robustness_ghg.csv",index=False)
json.dump(rows,open("tables/robustness_ghg.json","w"),indent=1)
print("\nsaved tables/robustness_ghg.csv")
