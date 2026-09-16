"""
subgroup_ghg.py — heterogeneity by income level and by institutional quality (V-Dem),
in the style of the published Table 7/8: outcomes as ROWS, subgroups as COLUMNS, each cell
a within-subgroup CS overall ATT (coef in log points; 95% CI in parentheses).
Outputs: tables/impact_income.csv, tables/impact_vdem.csv
"""
import warnings, numpy as np, pandas as pd
from csdid.att_gt import ATTgt
import pycountry_convert as pc
warnings.filterwarnings("ignore"); np.random.seed(20260612)

YMIN=2012
p=pd.read_csv("out/analysis_panel.csv")
p=p[(p.year>=YMIN)&(~p.self_achieved)].copy(); p.loc[p.first_treat>2024,"first_treat"]=0

# income terciles (baseline 2012 GDP pc PPP)
bl=p[p.year==YMIN].set_index("iso3")
gt=bl["gdp_pc_ppp"].dropna(); q1,q2=gt.quantile([1/3,2/3])
inc=bl["gdp_pc_ppp"].map(lambda v: np.nan if pd.isna(v) else ("Low" if v<=q1 else ("Middle" if v<=q2 else "High"))).rename("income_level")
p=p.merge(inc,left_on="iso3",right_index=True,how="left")

# V-Dem groups (baseline 2012 rule of law tercile -> Weak / Moderate / Strong institutions)
rl=bl["v2x_rule"].dropna(); r1,r2=rl.quantile([1/3,2/3])
vd=bl["v2x_rule"].map(lambda v: np.nan if pd.isna(v) else ("Weak" if v<=r1 else ("Moderate" if v<=r2 else "Strong"))).rename("vdem_group")
p=p.merge(vd,left_on="iso3",right_index=True,how="left")

def stars(b,s):
    z=abs(b/s) if s else 0
    return "***" if z>2.576 else "**" if z>1.96 else "*" if z>1.645 else ""
def cell(b,s):
    return f"{b:+.3f}{stars(b,s)} ({b-1.96*s:+.3f}, {b+1.96*s:+.3f})"
def bal(df,y,ymax):
    d=df.loc[df.year.between(YMIN,ymax),["country_id","iso3","year","first_treat",y]].dropna(subset=[y]).copy()
    d.loc[d.first_treat>ymax,"first_treat"]=0
    c=d.groupby("country_id")["year"].count(); return d[d.country_id.isin(c[c==ymax-YMIN+1].index)]
def ymx(y,n=45):
    ok=p.groupby("year")[y].count(); v=ok[ok>=n].index
    return int(min(v.max(),2024)) if len(v) else 2020
def cs(df,y,ymax):
    d=bal(df,y,ymax)
    nt=d.loc[d.first_treat>0,"country_id"].nunique(); nc0=d.loc[d.first_treat==0,"country_id"].nunique()
    if nt<3 or nc0<4: return None
    try:
        m=ATTgt(yname=y,gname="first_treat",idname="country_id",tname="year",xformla=f"{y}~1",
                data=d,control_group="nevertreated").fit(est_method="reg",bstrap=True)
        m.aggte(typec="dynamic",min_e=-7,max_e=5,bstrap=True,cband=True,na_rm=True)
        a=m.atte;f=lambda x:float(np.atleast_1d(np.asarray(x,float))[0])
        return f(a["overall_att"]),f(a["overall_se"]),int(d.shape[0]),nt
    except Exception:
        return None

OUTCOMES=[("ln_ghgpc","Total GHG"),("ln_ghgxlucf","GHG excl. LULUCF"),
          ("ln_co2luc","CO2 incl. land use"),("ln_coalco2","Coal CO2"),
          ("ln_gasco2","Gas CO2"),("ln_oilco2","Oil CO2"),
          ("ln_co2gdp","CO2 intensity of GDP")]

def build(groupcol, groups, control_pool_all=True):
    rows=[]
    obs={g:0 for g in groups}
    for y,lab in OUTCOMES:
        if y not in p.columns: continue
        ym=ymx(y)
        row={"Outcome":lab}
        for g in groups:
            # treated come from group g; never-treated controls drawn from the SAME group
            sub=p[(p[groupcol]==g)]
            r=cs(sub,y,ym)
            row[g]=cell(r[0],r[1]) if r else "\u2014"
            if r: obs[g]=max(obs[g],r[2])
        rows.append(row)
    obsrow={"Outcome":"Observations (max)"}; 
    for g in groups: obsrow[g]=f"{obs[g]:,}"
    rows.append(obsrow)
    return pd.DataFrame(rows)

print("=== Impact by INCOME level ===")
inc_tbl=build("income_level",["Low","Middle","High"])
print(inc_tbl.to_string(index=False))
inc_tbl.to_csv("tables/impact_income.csv",index=False)

print("\n=== Impact by V-DEM (rule of law) ===")
vd_tbl=build("vdem_group",["Weak","Moderate","Strong"])
print(vd_tbl.to_string(index=False))
vd_tbl.to_csv("tables/impact_vdem.csv",index=False)
print("\ndone")
