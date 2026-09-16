"""
build_table_inputs.py — assemble a tidy, provenance-checked results file for
every number that appears in a manuscript table, and attach a minimum
detectable effect (MDE = 2.8 x SE, 80% power at the 5% level) to every
estimate so that nulls are reported as bounds rather than absences.

Output: tables/manuscript_table_inputs.csv  (one row per reported estimate)
        tables/mde_summary.json             (nulls + their bounds, for prose)
"""
import json, re
import numpy as np, pandas as pd

T = "tables"
rows = []
pct = lambda b: 100 * (np.exp(b) - 1)

def stars(att, se):
    if se in (None, 0) or pd.isna(se):
        return ""
    z = abs(att / se)
    return "***" if z > 2.576 else "**" if z > 1.96 else "*" if z > 1.645 else ""

def add(table, outcome, column, att, se, unit, n=None, note=""):
    """unit: 'log' (report % effect) or 'pp' / 'level'."""
    if att is None or (isinstance(att, float) and pd.isna(att)):
        rows.append({"table": table, "outcome": outcome, "column": column,
                     "att": np.nan, "se": np.nan, "effect": "—", "se_str": "",
                     "sig": "", "mde": np.nan, "mde_str": "", "n": n, "note": note})
        return
    s = stars(att, se)
    mde_log = 2.8 * se if se == se else np.nan
    if unit == "log":
        eff = f"{pct(att):+.1f}%"
        se_s = f"({100*se:.1f})"                 # SE in log points x100
        mde_s = f"{pct(mde_log):.1f}%"
    else:
        eff = f"{att:+.2f}"
        se_s = f"({se:.2f})"
        mde_s = f"{mde_log:.2f}"
    rows.append({"table": table, "outcome": outcome, "column": column,
                 "att": att, "se": se, "effect": eff, "se_str": se_s, "sig": s,
                 "mde": mde_log, "mde_str": mde_s, "n": n, "note": note})

# ---------------- Table 1: main GHG family, CS + 2x2 ----------------
mc = pd.read_csv(f"{T}/main_ghg_v2.csv")
LAB = {"Total GHG per capita": "Total GHG", "GHG excl. LULUCF": "GHG excl. LULUCF",
       "CO2 incl. land use": "CO₂ incl. land use", "Coal CO2": "Coal CO₂",
       "Gas CO2": "Gas CO₂", "Oil CO2": "Oil CO₂",
       "Methane (CH4)": "Methane (CH₄)", "Nitrous oxide (N2O)": "N₂O"}
for _, r in mc.iterrows():
    lab = LAB[r.outcome]
    add("T1", lab, "CS", r.csunc_att, r.csunc_se, "log", int(r.csadj_n))
    add("T1", lab, "DiD", r.did_att, r.did_se, "log", int(r.did_n))

# ---------------- Table 2: robustness suite ----------------
rb = pd.read_csv(f"{T}/robustness_ghg.csv").set_index("spec")
ex = pd.read_csv(f"{T}/robustness_extended.csv").set_index("spec")
def att_of(row):
    if "att" in row.index and pd.notna(row.get("att")):
        return float(row["att"])
    return float(np.log1p(row["effect_pct"] / 100))
SPECS = [
    ("Baseline (CS, never-treated)", ex.loc["Baseline (CS, never-treated)"], "n_countries"),
    ("Not-yet-treated controls", rb.loc["Not-yet-treated controls"], None),
    ("Allow 1-year anticipation", ex.loc["Anticipation: 1 year"], "n_countries"),
    ("Doubly robust, baseline-2012 covariates",
     ex.loc["Covariate-adjusted CS (DR, baseline-2012 X)"], "n_countries"),
    ("Panel ends 2019 (pre-COVID)", rb.loc["Exclude COVID (panel ends 2019)"], None),
    ("Exclude 2020–21, keep 2022–24 (2×2)",
     ex.loc["Exclude COVID years (2020-2021), 2x2"], "n_countries"),
    ("Exclude Europe", ex.loc["Exclude Europe"], "n_countries"),
    ("Drop later-reversed targets", ex.loc["Drop later-reversed targets"], "n_countries"),
    ("Broad coding: any neutrality-type target",
     ex.loc["Broad coding: any neutrality-type target"], "n_countries"),
    ("Total (not per-capita) GHG", ex.loc["Total GHG (not per capita)"], "n_countries"),
    ("Consumption-based CO₂ (leakage test)",
     ex.loc["Consumption-based CO2 pc (leakage test)"], "n_countries"),
    ("Placebo: counterfactual 2015 timing", rb.loc["Placebo (fake 2015 timing, pre-2019)"], None),
    ("Treatment = legally enshrined year", rb.loc["Treatment = binding (law) year"], None),
]
for label, r, ncol in SPECS:
    n = int(r[ncol]) if ncol and pd.notna(r.get(ncol)) else None
    add("T2", label, "CS", att_of(r), float(r["se"]), "log", n)

# ---------------- ED Table 4: electricity mix & energy ----------------
em = pd.read_csv(f"{T}/energy_mechanism.csv")
for _, r in em.iterrows():
    unit = "pp" if r.unit == "pp" else "log"
    add("EDT4", r.outcome, "CS", r.att, r.se, unit, int(r.n))

# ---------------- ED Table 7: air quality ----------------
aq = pd.read_csv(f"{T}/airquality_rq3.csv")
for _, r in aq.iterrows():
    unit = "log" if "ln" in str(r.outcome) else "pp"
    add("EDT7", r.outcome, "CS", r.att, r.se, unit, int(r.n_countries),
        note=str(r.window))

# ---------------- ED Table 1: continent ----------------
rg = pd.read_csv(f"{T}/regional_ghg.csv")
for _, r in rg.iterrows():
    lab = f"{r.continent} — {'CO₂' if r.outcome=='CO2' else 'GHG'}"
    add("EDT1", lab, "CS", r.cs_att, r.cs_se, "log", int(r.treated_n))
    add("EDT1", lab, "DiD", r.did_att, r.did_se, "log", int(r.treated_n))

df = pd.DataFrame(rows)
df.to_csv(f"{T}/manuscript_table_inputs.csv", index=False)

# ---------------- MDE summary for the nulls ----------------
nulls = df[(df.sig == "") & df.att.notna()].copy()
summary = {}
for key in ["Oil CO₂", "Methane (CH₄)", "N₂O"]:
    r = df[(df.table == "T1") & (df.outcome == key) & (df.column == "CS")].iloc[0]
    summary[key] = {"effect_pct": round(pct(r.att), 2),
                    "mde_pct": round(pct(r.mde), 1)}
for _, r in df[df.table == "EDT7"].iterrows():
    summary[r.outcome] = {"effect": r.effect, "mde": r.mde_str}
json.dump(summary, open(f"{T}/mde_summary.json", "w"), indent=1)

print(f"wrote {T}/manuscript_table_inputs.csv  ({len(df)} estimates)")
print(f"nulls with MDE bounds: {len(nulls)}")
print("\nKey nulls (CS, main outcomes) — effect vs detection bound:")
for k, v in summary.items():
    if "effect_pct" in v:
        print(f"  {k:18s} {v['effect_pct']:+.2f}%   MDE ±{v['mde_pct']:.1f}%")
    else:
        print(f"  {k[:38]:40s} {v['effect']:>9s}   MDE ±{v['mde']}")
