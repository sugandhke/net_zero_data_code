"""extended_robustness_part2.py — HonestDiD sensitivity, raw trends, and a
precise 2x2 version of the COVID-year exclusion (the unbalanced-CS version is
too imprecise to be informative)."""
import warnings
import numpy as np, pandas as pd
import pyfixest as pf
warnings.filterwarnings("ignore"); np.random.seed(20260612)

YMIN = 2012; Y = "ln_ghgpc"
p = pd.read_csv("out/analysis_panel.csv")
p = p[(p.year >= YMIN) & (~p.self_achieved)].copy()
p.loc[p.first_treat > 2024, "first_treat"] = 0

def bal(df, y, ymax):
    cols = ["country_id", "iso3", "year", "first_treat", y]
    d = df.loc[df.year.between(YMIN, ymax), cols].dropna(subset=[y]).copy()
    d.loc[d.first_treat > ymax, "first_treat"] = 0
    c = d.groupby("country_id")["year"].count()
    return d[d.country_id.isin(c[c == d.year.nunique()].index)]

ok = p.groupby("year")[Y].count(); YM = int(min(ok[ok >= 55].index.max(), 2024))

# --- precise COVID exclusion: 2x2 (2019 cohort vs never), drop 2020-21 ------
d = p[(p.first_treat == 0) | (p.first_treat == 2019)]
d = d[~d.year.isin([2020, 2021])].copy()
d = bal(d, Y, YM)
d["did2"] = ((d.first_treat == 2019) & (d.year >= 2019)).astype(int)
m = pf.feols(f"{Y} ~ did2 | country_id + year", data=d, vcov={"CRV1": "country_id"})
b, s = float(m.coef()["did2"]), float(m.se()["did2"])
z = abs(b / s); sig = "***" if z > 2.576 else "**" if z > 1.96 else "*" if z > 1.645 else ""
pctb = 100 * (np.exp(b) - 1)
print(f"2x2 excl. 2020-21: {pctb:+.1f}%{sig} (se {s:.4f}, {d.country_id.nunique()} countries)")
rob = pd.read_csv("tables/robustness_extended.csv")
new = {"spec": "Exclude COVID years (2020-2021), 2x2", "att": round(b, 4),
       "se": round(s, 4), "effect_pct": round(pctb, 1), "sig": sig,
       "cell": f"{pctb:+.1f}%{sig}", "n_countries": d.country_id.nunique(),
       "note": "2x2 TWFE, 2019 cohort vs never-treated"}
rob = pd.concat([rob, pd.DataFrame([new])], ignore_index=True)
rob.to_csv("tables/robustness_extended.csv", index=False)

# --- HonestDiD on the 2019-cohort TWFE event study --------------------------
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
V = np.asarray(m._vcov)
pd.DataFrame({"event_time": evs, "att": beta, "se": m.se().loc[names].values}
             ).to_csv("tables/eventstudy_2x2.csv", index=False)
npre = sum(1 for e in evs if e < -1); npost = len(evs) - npre
from honestdid import createSensitivityResults_relativeMagnitudes, constructOriginalCS
l_avg = np.ones(npost) / npost
orig = constructOriginalCS(betahat=beta, sigma=V, numPrePeriods=npre,
                           numPostPeriods=npost, l_vec=l_avg)
sens = createSensitivityResults_relativeMagnitudes(
    betahat=beta, sigma=V, numPrePeriods=npre, numPostPeriods=npost,
    l_vec=l_avg, Mbarvec=[0.5, 1.0, 1.5, 2.0])
out = pd.DataFrame(sens)
try:
    orig_df = pd.DataFrame(orig)
except Exception:
    orig_df = pd.DataFrame([{"lb": orig[0], "ub": orig[1], "method": "Original", "Mbar": 0.0}])
res = pd.concat([orig_df, out], ignore_index=True)
res.to_csv("tables/honestdid_sensitivity.csv", index=False)
print(res.to_string(index=False))

# --- raw trends --------------------------------------------------------------
d0 = bal(p, Y, YM)
d0["group"] = np.where(d0.first_treat == 2019, "2019 adopters",
               np.where(d0.first_treat == 0, "Never treated", "Other cohorts"))
tr = (d0[d0.group != "Other cohorts"].groupby(["group", "year"])[Y]
      .agg(["mean", "count"]).reset_index().rename(columns={"mean": Y}))
base = tr[tr.year == 2018].set_index("group")[Y]
tr["indexed"] = tr.apply(lambda r: r[Y] - base[r.group], axis=1)
tr.to_csv("tables/raw_trends.csv", index=False)
print("saved raw_trends.csv; groups:", tr.group.unique(), "years", tr.year.min(), tr.year.max())
