"""
make_raghu_figures_v2.py — Fig 2, Fig 3 (map) and Fig 4 for
raghu_sir_manuscript.docx in the SAME visual style as his originals
(Okabe-Ito palette, horizontal bars with value labels, DejaVu Sans),
updated to the current pipeline numbers.
Fig 3: subtitle ("Net Zero Tracker register ...") removed.
Outputs into out/raghu_figs/.
"""
import os, re
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

os.makedirs("out/figs_notitle", exist_ok=True)
OI = {"blue": "#0072B2", "verm": "#D55E00", "green": "#009E73", "grey": "#999999",
      "black": "#000000"}
plt.rcParams.update({"font.size": 11, "figure.facecolor": "white",
                     "savefig.dpi": 200, "pdf.fonttype": 42})
pct = lambda b: 100 * (np.exp(b) - 1)

def style(ax):
    ax.spines[["top", "right"]].set_visible(False)

# ============================ FIG 2 (his style) ============================
em = pd.read_csv("tables/energy_mechanism.csv")
em = em[em.unit == "pp"].copy()
om = {"Renewables share of electricity": "Renewables",
      "Low-carbon share of electricity": "Low-carbon",
      "Solar share of electricity": "Solar", "Wind share of electricity": "Wind",
      "Coal share of electricity": "Coal share",
      "Fossil share of electricity": "Fossil"}
em["lab"] = em.outcome.map(om)
order_a = ["Renewables", "Low-carbon", "Solar", "Wind", "Coal share", "Fossil"]
em = em.set_index("lab").loc[order_a].reset_index()
em["sig"] = em.sig.fillna("")

mc = pd.read_csv("tables/main_ghg_v2.csv").set_index("outcome")
order_b = ["Coal CO2", "Gas CO2", "CO2 incl. land use", "Total GHG per capita",
           "GHG excl. LULUCF", "Nitrous oxide (N2O)", "Oil CO2", "Methane (CH4)"]
lab_b = {"Coal CO2": "Coal CO₂", "Gas CO2": "Gas CO₂",
         "CO2 incl. land use": "CO₂ incl. land use",
         "Total GHG per capita": "Total GHG", "GHG excl. LULUCF": "GHG excl. LULUCF",
         "Nitrous oxide (N2O)": "N₂O", "Oil CO2": "Oil CO₂", "Methane (CH4)": "Methane"}

fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.8, 4.95))
# --- panel a: bars, green up / orange down / grey n.s.
y = np.arange(len(em))[::-1]
for i, (_, r) in enumerate(em.iterrows()):
    sig = r.sig != ""
    col = OI["grey"] if not sig else (OI["green"] if r.att > 0 else OI["verm"])
    a1.barh(y[i], r.att, color=col, height=0.62, zorder=3)
    lab = f"{r.att:+.1f}{r.sig}" if r.att > 0 else f"{r.att:.1f}{r.sig}"
    if r.att >= 0:
        a1.annotate(lab, (r.att, y[i]), xytext=(5, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=12)
    else:
        a1.annotate(lab, (r.att, y[i]), xytext=(-5, 0), textcoords="offset points",
                    va="center", ha="right", fontsize=12)
a1.axvline(0, color="0.3", lw=1.2)
a1.set_yticks(y); a1.set_yticklabels(em.lab, fontsize=13)
a1.set_xlabel("Change in generation share (pp)", fontsize=12)
a1.set_xlim(-3.4, 3.4)
a1.set_title("a", loc="left", fontsize=14, fontweight="bold")
style(a1)
# --- panel b: bars, orange significant / grey n.s.
y2 = np.arange(len(order_b))[::-1]
for i, o in enumerate(order_b):
    r = mc.loc[o]
    sig = r.csunc_sig if isinstance(r.csunc_sig, str) else ""
    eff = pct(r.csunc_att)
    col = OI["verm"] if sig else OI["grey"]
    a2.barh(y2[i], eff, color=col, height=0.62, zorder=3)
    lab = f"{eff:+.1f}%{sig}" if eff > 0 else f"{eff:.1f}%{sig}"
    if o == "Coal CO2":
        a2.annotate(lab, (eff, y2[i]), xytext=(6, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=13, fontweight="bold",
                    color="white")
    elif eff <= 0:
        a2.annotate(lab, (eff, y2[i]), xytext=(-5, 0), textcoords="offset points",
                    va="center", ha="right", fontsize=12)
    else:
        a2.annotate(lab, (eff, y2[i]), xytext=(5, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=12)
a2.axvline(0, color="0.3", lw=1.2)
a2.set_yticks(y2); a2.set_yticklabels([lab_b[o] for o in order_b], fontsize=13)
a2.set_xlabel("Effect on emissions per capita (%)", fontsize=12)
a2.set_xlim(-22.5, 3.5)
a2.set_title("b", loc="left", fontsize=14, fontweight="bold")
style(a2)
fig.tight_layout()
fig.savefig("out/figs_notitle/fig2_composite.png", dpi=200, bbox_inches="tight")
fig.savefig("out/figs_notitle/fig2_composite.pdf", bbox_inches="tight")
plt.close(fig)

# ============================ FIG 3: map, no subtitle ============================
import geopandas as gpd
adopt = pd.read_csv("tables/adoption_countries.csv")
world = gpd.read_file("geo/ne_110m_admin_0_countries.geojson")
iso_col = "ISO_A3_EH" if "ISO_A3_EH" in world.columns else "ISO_A3"
world = world[world[iso_col] != "ATA"].merge(adopt, left_on=iso_col,
                                             right_on="iso3", how="left")
def bucket(ft):
    if pd.isna(ft) or ft == 0: return "Never adopted"
    ft = int(ft)
    if ft <= 2018: return "Adopted pre-2019"
    if ft == 2019: return "2019 (COP25 wave)"
    if ft <= 2021: return "2020–2021"
    return "2022 or later"
world["cohort"] = world["first_treat"].map(bucket)
counts = adopt.assign(b=adopt.first_treat.map(bucket)).groupby("b")["iso3"].count()
SEQ = {"Adopted pre-2019": "#0d366b", "2019 (COP25 wave)": "#1c5cab",
       "2020–2021": "#3987e5", "2022 or later": "#86b6ef",
       "Never adopted": "#e3e2de"}
world = world.to_crs("+proj=robin")
fig, ax = plt.subplots(figsize=(10.8, 5.4))
ax.set_aspect("equal")
world.plot(ax=ax, color=SEQ["Never adopted"], edgecolor="white", linewidth=0.35)
for cat, col in SEQ.items():
    sub = world[world.cohort == cat]
    if len(sub): sub.plot(ax=ax, color=col, edgecolor="white", linewidth=0.35)
ax.set_axis_off()

handles = [mpatches.Patch(fc=SEQ[c], ec="none",
                          label=f"{c}  ({int(counts.get(c, 0))})") for c in SEQ]
ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=10,
          title="Adoption cohort (countries)", title_fontsize=10.5,
          alignment="left")
fig.tight_layout()
fig.savefig("out/figs_notitle/fig3_map.png", dpi=200, bbox_inches="tight")
fig.savefig("out/figs_notitle/fig3_map.pdf", bbox_inches="tight")
plt.close(fig)

# ============================ FIG 4 (his style) ============================
rb = pd.read_csv("tables/robustness_ghg.csv").set_index("spec")
ext = pd.read_csv("tables/robustness_extended.csv").set_index("spec")
b0 = ext.loc["Baseline (CS, never-treated)"]
plc = rb.loc["Placebo (fake 2015 timing, pre-2019)"]
law = rb.loc["Treatment = binding (law) year"]

vd = pd.read_csv("tables/impact_vdem.csv").set_index("Outcome")
def parse_cell(s):
    m = re.match(r"([+-]\d+\.\d+)(\**)\s*\(([+-]\d+\.\d+),\s*([+-]\d+\.\d+)\)", str(s))
    return float(m.group(1)), m.group(2), float(m.group(3)), float(m.group(4))
terc = {g: parse_cell(vd.loc["Total GHG", g]) for g in ["Weak", "Moderate", "Strong"]}

rg = pd.read_csv("tables/regional_ghg.csv")
co2 = rg[(rg.outcome == "CO2") & rg.cs_att.notna()].set_index("continent")

fig, (a, b, c) = plt.subplots(1, 3, figsize=(10.8, 4.35))
# --- a: coding of commitment, horizontal bars
rows_a = [("Any commitment\n(baseline)", b0.effect_pct, "***", OI["blue"]),
          ("Placebo\n(fake 2015 timing)", plc.effect_pct, "", OI["grey"]),
          ("Legally enshrined\nonly", law.effect_pct, "", OI["grey"])]
ya = np.arange(len(rows_a))[::-1]
for i, (labl, eff, sig, col) in enumerate(rows_a):
    a.barh(ya[i], eff, color=col, height=0.6, zorder=3)
    lab = f"{eff:.1f}%{sig}"
    if i == 0:
        a.annotate(lab, (eff, ya[i]), xytext=(6, 0), textcoords="offset points",
                   va="center", ha="left", fontsize=12.5, fontweight="bold",
                   color="white")
    else:
        a.annotate(lab, (eff, ya[i]), xytext=(-5, 0), textcoords="offset points",
                   va="center", ha="right", fontsize=12)
a.axvline(0, color="0.3", lw=1.2)
a.set_yticks(ya); a.set_yticklabels([r[0] for r in rows_a], fontsize=11.5)
a.set_xlabel("Effect on GHG per capita (%)", fontsize=11.5)
a.set_xlim(-7.2, 1.6)
a.set_title("a", loc="left", fontsize=14, fontweight="bold")
style(a)
# --- b: rule-of-law terciles, points + CI
xb = np.arange(3)
b.axhline(0, color="0.3", lw=1.2)
side = {"Weak": (-11, "right"), "Moderate": (11, "left"), "Strong": (11, "left")}
for i, g in enumerate(["Weak", "Moderate", "Strong"]):
    att, sig, lo, hi = terc[g]
    b.errorbar([xb[i]], [pct(att)], yerr=[[pct(att) - pct(lo)], [pct(hi) - pct(att)]],
               fmt="o", color=OI["blue"], ecolor=OI["blue"], elinewidth=2.2,
               capsize=5, ms=9, zorder=3)
    dx, ha = side[g]
    b.annotate(f"{pct(att):.1f}%{sig}", (xb[i], pct(att)), xytext=(dx, 0),
               textcoords="offset points", va="center", ha=ha, fontsize=11.5)
b.set_xticks(xb)
b.set_xticklabels(["Weak", "Moderate", "Strong"], fontsize=9)
b.set_xlim(-0.75, 3.0)
b.set_xlabel("Rule-of-law tercile (V-Dem)", fontsize=11.5)
b.set_ylabel("Effect on GHG per capita (%)", fontsize=11.5)
b.set_title("b", loc="left", fontsize=14, fontweight="bold")
style(b)
# --- c: geography, horizontal bars (estimable continents only)
cont_order = ["Europe", "Asia", "North America", "Africa"]
disp = {"North America": "N. America"}
yc = np.arange(len(cont_order))[::-1]
for i, cn in enumerate(cont_order):
    r = co2.loc[cn]
    sig = r.cs_sig if isinstance(r.cs_sig, str) else ""
    eff = pct(r.cs_att)
    col = OI["verm"] if cn == "Europe" else OI["grey"]
    c.barh(yc[i], eff, color=col, height=0.6, zorder=3)
    lab = f"{eff:+.1f}%{sig}" if eff > 0 else f"{eff:.1f}%{sig}"
    if cn == "Europe":
        c.annotate(lab, (eff / 2, yc[i]), va="center", ha="center",
                   fontsize=11.5, fontweight="bold", color="white")
    elif eff > 0:
        c.annotate(lab, (eff, yc[i]), xytext=(5, 0), textcoords="offset points",
                   va="center", ha="left", fontsize=12)
    else:
        c.annotate(lab, (eff, yc[i]), xytext=(-5, 0), textcoords="offset points",
                   va="center", ha="right", fontsize=12)
c.axvline(0, color="0.3", lw=1.2)
c.set_yticks(yc)
c.set_yticklabels([disp.get(x, x) for x in cont_order], fontsize=12)
c.set_xlabel("Effect on CO₂ per capita (%)", fontsize=11.5)
c.set_xlim(-13.5, 10.5)
c.set_title("c", loc="left", fontsize=14, fontweight="bold")
style(c)
fig.tight_layout()
fig.savefig("out/figs_notitle/fig4_composite.png", dpi=200, bbox_inches="tight")
fig.savefig("out/figs_notitle/fig4_composite.pdf", bbox_inches="tight")
plt.close(fig)
print("saved fig2_composite, fig3_map, fig4_composite (his style, current numbers)")
