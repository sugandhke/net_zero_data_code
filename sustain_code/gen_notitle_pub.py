"""
make_pub_figures.py — publication-quality figures for the net-zero GHG paper.
One consistent style system across all figures; validated CVD-safe palette.
Writes PNG (300 dpi) + PDF (vector, for journal submission) into figures/.
Run from the project root: .venv/bin/python code/make_pub_figures.py
"""
import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# ---------------------------------------------------------------- style system
C = {"blue": "#2a78d6", "aqua": "#1baf7a", "yellow": "#eda100", "green": "#008300",
     "violet": "#4a3aa7", "red": "#e34948", "magenta": "#e87ba4", "orange": "#eb6834",
     "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#8a8984",
     "grid": "#e8e7e3", "spine": "#c8c7c2", "zero": "#a5a49f", "na": "#e3e2de"}
SEQ = {"2022+": "#86b6ef", "2020-2021": "#3987e5", "2019": "#1c5cab", "pre2019": "#0d366b"}

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9, "axes.titlesize": 10.5, "axes.labelsize": 9,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 8.5,
    "axes.edgecolor": C["spine"], "axes.linewidth": 0.7,
    "xtick.color": C["spine"], "ytick.color": C["spine"],
    "xtick.labelcolor": C["ink2"], "ytick.labelcolor": C["ink2"],
    "axes.labelcolor": C["ink2"], "text.color": C["ink"],
    "figure.dpi": 120, "savefig.dpi": 300, "figure.facecolor": "white",
    "axes.facecolor": "white", "pdf.fonttype": 42})

def style_ax(ax, grid="y"):
    ax.spines[["top", "right"]].set_visible(False)
    if grid == "y":
        ax.grid(axis="y", color=C["grid"], lw=0.6, zorder=0)
    elif grid == "x":
        ax.grid(axis="x", color=C["grid"], lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=3, width=0.7)

def title(ax, main, sub=None, x=0.0):
    # titles/subtitles suppressed — described in the manuscript caption instead
    return

def save(fig, name):
    fig.savefig(f"out/figs_notitle/{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"out/figs_notitle/{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"saved out/figs_notitle/{name}.png/.pdf")

pct = lambda b: 100 * (np.exp(b) - 1)

# ============================================================ FIG: raw trends
tr = pd.read_csv("tables/raw_trends.csv")
fig, ax = plt.subplots(figsize=(6.8, 3.6))
cols = {"2019 adopters": C["blue"], "Never treated": C["ink2"]}
for g, sub in tr.groupby("group"):
    sub = sub.sort_values("year")
    ax.plot(sub.year, 100 * sub.indexed, color=cols[g], lw=1.8,
            marker="o", ms=4, mfc=cols[g], mec="white", mew=0.8, zorder=3)
    last = sub.iloc[-1]
    n = int(sub["count"].iloc[-1])
    ax.annotate(f"{g}\n(n = {n})", (last.year, 100 * last.indexed),
                xytext=(8, 0), textcoords="offset points",
                color=cols[g], fontsize=8.5, fontweight="bold", va="center")
ax.axvline(2018.5, color=C["zero"], lw=0.9, ls=(0, (4, 3)), zorder=1)
ax.text(2018.42, ax.get_ylim()[1], "2019 adoption wave ", ha="right", va="top",
        fontsize=8, color=C["ink2"], rotation=90)
ax.axhline(0, color=C["zero"], lw=0.8, zorder=1)
ax.set_xlim(tr.year.min() - 0.3, tr.year.max() + 2.6)
ax.set_ylabel("Mean ln GHG per capita,\nchange vs 2018 (log points × 100)")
ax.set_xticks(range(int(tr.year.min()), int(tr.year.max()) + 1, 2))
title(ax, "Raw emission trajectories: common trends before 2019, divergence after",
      "Balanced estimation sample; group means of ln GHG per capita indexed to 2018 = 0")
style_ax(ax)
save(fig, "fig_raw_trends")

# ============================================================ FIG: event study
es = pd.read_csv("tables/pretrends_cs.csv").sort_values("event_time")
e2 = pd.read_csv("tables/eventstudy_2x2.csv").sort_values("event_time")
ps = pd.read_csv("tables/pretrends_summary.csv")
fig, ax = plt.subplots(figsize=(6.8, 3.9))
ax.axhline(0, color=C["zero"], lw=0.8, zorder=1)
ax.axvline(-0.5, color=C["zero"], lw=0.9, ls=(0, (4, 3)), zorder=1)
# CS primary: band + connected markers
lo, hi = 100 * (es.att - 1.96 * es.se), 100 * (es.att + 1.96 * es.se)
ax.fill_between(es.event_time, lo, hi, color=C["blue"], alpha=0.13, lw=0, zorder=2)
ax.plot(es.event_time, 100 * es.att, color=C["blue"], lw=1.8, zorder=4,
        marker="o", ms=5.5, mfc=C["blue"], mec="white", mew=0.9)
# 2x2 TWFE secondary: open markers, slight offset
e2p = e2[e2.event_time.between(es.event_time.min(), es.event_time.max())]
ax.errorbar(e2p.event_time + 0.13, 100 * e2p.att, yerr=196 * e2p.se, fmt="o",
            ms=4.4, mfc="white", mec=C["ink2"], mew=1.1, ecolor=C["ink2"],
            elinewidth=0.9, capsize=0, ls="none", zorder=3)
ax.set_xticks(range(int(es.event_time.min()), int(es.event_time.max()) + 1))
ax.set_xlabel("Years since net-zero adoption")
ax.set_ylabel("Effect on ln GHG per capita\n(log points × 100)")
p_cs = ps.iloc[0]["p"]
ax.text(0.02, 0.055, f"Joint pre-trends test (CS): {ps.iloc[0]['stat']}, p = {p_cs:.2f}\n"
        f"Joint pre-trends test (2×2): {ps.iloc[1]['stat']}, p = {ps.iloc[1]['p']:.2f}",
        transform=ax.transAxes, fontsize=8, color=C["ink2"],
        bbox=dict(boxstyle="round,pad=0.45", fc="white", ec=C["grid"]))
leg = [Line2D([], [], color=C["blue"], lw=1.8, marker="o", ms=5.5, mec="white",
              label="Callaway–Sant'Anna (95% simultaneous band)"),
       Line2D([], [], color=C["ink2"], lw=0, marker="o", ms=4.4, mfc="white",
              mew=1.1, label="TWFE, 2019 cohort vs never-treated (95% CI)")]
ax.legend(handles=leg, loc="upper right", frameon=False, handletextpad=0.6)
title(ax, "Flat pre-trends, then a growing post-adoption decline",
      "Dynamic ATT on ln GHG per capita; never-treated controls; TWFE base period e = −1")
style_ax(ax)
save(fig, "fig_eventstudy")

# ============================================================ FIG: adoption map
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
counts = (adopt.assign(b=adopt.first_treat.map(bucket)).groupby("b")["iso3"].count())
cmap = {"Adopted pre-2019": SEQ["pre2019"], "2019 (COP25 wave)": SEQ["2019"],
        "2020–2021": SEQ["2020-2021"], "2022 or later": SEQ["2022+"],
        "Never adopted": C["na"]}
world = world.to_crs("+proj=robin")
fig, ax = plt.subplots(figsize=(8.6, 4.4))
ax.set_aspect("equal")
world.plot(ax=ax, color=C["na"], edgecolor="white", linewidth=0.35)
for cat, col in cmap.items():
    sub = world[world.cohort == cat]
    if len(sub): sub.plot(ax=ax, color=col, edgecolor="white", linewidth=0.35)
ax.set_axis_off()
ax.set_title("National net-zero target adoption, by first-commitment cohort",
             loc="left", fontweight="bold", fontsize=10.5, color=C["ink"], y=0.98)
ax.text(0.0, 0.955, "Net Zero Tracker register (Oct 2025 vintage); darker = earlier commitment; Robinson projection",
        transform=ax.transAxes, fontsize=8.5, color=C["ink2"])
handles = [Patch(fc=cmap[c], ec="none",
                 label=f"{c}  ({int(counts.get(c, 0))})") for c in cmap]
ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=8.2,
          title="Adoption cohort (countries)", title_fontsize=8.6,
          alignment="left", bbox_to_anchor=(0.0, 0.02))
save(fig, "fig_adoption_map")

# ====================================================== FIG: RQ1 decomposition
d = pd.read_csv("tables/main_ghg_v2.csv")
order = ["Total GHG per capita", "GHG excl. LULUCF", "CO2 incl. land use",
         "Coal CO2", "Gas CO2", "Oil CO2", "Methane (CH4)", "Nitrous oxide (N2O)"]
lab = {"Total GHG per capita": "Total GHG", "GHG excl. LULUCF": "GHG excl. LULUCF",
       "CO2 incl. land use": "CO₂ incl. land use", "Coal CO2": "Coal CO₂",
       "Gas CO2": "Gas CO₂", "Oil CO2": "Oil CO₂",
       "Methane (CH4)": "Methane (CH₄)", "Nitrous oxide (N2O)": "N₂O"}
d = d.set_index("outcome").loc[order].reset_index()
d["eff"] = pct(d.csunc_att)
d["lo"] = pct(d.csunc_att - 1.96 * d.csunc_se)
d["hi"] = pct(d.csunc_att + 1.96 * d.csunc_se)
d["sig"] = d.csunc_sig.fillna("")
fig, ax = plt.subplots(figsize=(6.4, 3.9))
y = np.arange(len(d))[::-1]
ax.axvline(0, color=C["zero"], lw=0.9, zorder=1)
for i, (_, r) in enumerate(d.iterrows()):
    is_sig = r.sig != ""
    col = C["blue"] if is_sig else C["muted"]
    ax.plot([r.lo, r.hi], [y[i], y[i]], color=col, lw=1.8, zorder=3,
            solid_capstyle="round")
    ax.plot([r.eff], [y[i]], "o", ms=6.5, mfc=col, mec="white", mew=1, zorder=4)
    ax.annotate(f"{r.eff:+.1f}%{r.sig}", (max(r.hi, 0), y[i]),
                xytext=(7, 0), textcoords="offset points",
                fontsize=8, color=C["ink2"], va="center", ha="left")
ax.set_yticks(y)
ax.set_yticklabels([lab[o] for o in d.outcome], fontsize=9, color=C["ink"])
ax.set_xlabel("Effect of net-zero adoption (%), CS overall ATT with 95% CI")
leg = [Line2D([], [], color=C["blue"], lw=1.8, marker="o", ms=6, mec="white",
              label="Significant (p < 0.10)"),
       Line2D([], [], color=C["muted"], lw=1.8, marker="o", ms=6, mec="white",
              label="Not significant")]
ax.legend(handles=leg, loc="lower left", frameon=False)
title(ax, "The GHG response is concentrated in coal and gas combustion",
      "Callaway–Sant'Anna, never-treated controls; outcomes in ln per-capita terms", x=-0.18)
style_ax(ax, grid="x")
save(fig, "fig_decomposition")

# ============================================== FIG: RQ3 regional event studies
ev = pd.read_csv("tables/regional_eventstudy.csv")
conts = [c for c in ["Europe", "Asia", "Africa", "North America", "South America"]
         if c in ev.continent.unique()]
ccol = dict(zip(conts, [C["blue"], C["aqua"], C["yellow"], C["green"], C["violet"]]))
fig, axes = plt.subplots(2, 3, figsize=(8.6, 4.9), sharex=True, sharey=True)
axes = axes.ravel()
allv = np.concatenate([(ev.att - 1.96 * ev.se).values, (ev.att + 1.96 * ev.se).values]) * 100
ylo, yhi = np.nanmin(allv) * 1.06, np.nanmax(allv) * 1.06
for i, cn in enumerate(conts):
    ax = axes[i]; s = ev[ev.continent == cn].sort_values("event_time")
    ax.axhline(0, color=C["zero"], lw=0.8, zorder=1)
    ax.axvline(-0.5, color=C["zero"], lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.fill_between(s.event_time, 100 * (s.att - 1.96 * s.se),
                    100 * (s.att + 1.96 * s.se), color=ccol[cn], alpha=0.14, lw=0)
    ax.plot(s.event_time, 100 * s.att, color=ccol[cn], lw=1.7, marker="o",
            ms=3.6, mfc=ccol[cn], mec="white", mew=0.7, zorder=3)
    ax.set_title(cn, loc="left", fontsize=9.5, color=C["ink"], fontweight="bold")
    ax.set_ylim(ylo, yhi)
    style_ax(ax)
    if i % 3 == 0: ax.set_ylabel("Effect on ln GHG pc\n(log points × 100)")
    if i >= 2: ax.set_xlabel("Years since adoption")
for j in range(len(conts), len(axes)):
    axes[j].set_visible(False)
axes[2].set_xlabel("Years since adoption")
# figure title/subtitle suppressed — described in the manuscript caption instead
fig.tight_layout()
save(fig, "fig_regional_eventstudy")

# ================================================== FIG: RQ4 electricity mix
em = pd.read_csv("tables/energy_mechanism.csv")
em = em[em.unit == "pp"].copy()
om = {"Renewables share of electricity": "Renewables",
      "Low-carbon share of electricity": "Low-carbon (incl. nuclear)",
      "Solar share of electricity": "Solar", "Wind share of electricity": "Wind",
      "Fossil share of electricity": "Fossil", "Coal share of electricity": "Coal"}
em["lab"] = em.outcome.map(om)
em["lo"] = em.att - 1.96 * em.se; em["hi"] = em.att + 1.96 * em.se
order2 = ["Renewables", "Low-carbon (incl. nuclear)", "Solar", "Wind", "Fossil", "Coal"]
em = em.set_index("lab").loc[order2].reset_index()
em["sig"] = em.sig.fillna("")
fig, ax = plt.subplots(figsize=(6.4, 3.3))
y = np.arange(len(em))[::-1]
ax.axvline(0, color=C["zero"], lw=0.9, zorder=1)
for i, (_, r) in enumerate(em.iterrows()):
    if r.sig == "": col = C["muted"]
    else: col = C["blue"] if r.att > 0 else C["red"]
    ax.plot([r.lo, r.hi], [y[i], y[i]], color=col, lw=1.8, zorder=3,
            solid_capstyle="round")
    ax.plot([r.att], [y[i]], "o", ms=6.5, mfc=col, mec="white", mew=1, zorder=4)
    ax.annotate(f"{r.att:+.1f} pp{r.sig}", (r.hi, y[i]), xytext=(7, 0),
                textcoords="offset points", fontsize=8, color=C["ink2"], va="center")
ax.set_yticks(y); ax.set_yticklabels(em.lab, fontsize=9, color=C["ink"])
ax.set_xlabel("Effect on share of electricity generation (percentage points), CS ATT with 95% CI")
leg = [Line2D([], [], color=C["blue"], lw=1.8, marker="o", ms=6, mec="white",
              label="Clean share rises"),
       Line2D([], [], color=C["red"], lw=1.8, marker="o", ms=6, mec="white",
              label="Fossil share falls"),
       Line2D([], [], color=C["muted"], lw=1.8, marker="o", ms=6, mec="white",
              label="Not significant")]
ax.legend(handles=leg, loc="lower right", frameon=False)
title(ax, "Mechanism: the electricity mix shifts toward low-carbon sources",
      "Callaway–Sant'Anna, never-treated controls", x=-0.28)
style_ax(ax, grid="x")
save(fig, "fig_energy_mechanism")

# ==================================================== FIG: robustness spec chart
r1 = pd.read_csv("tables/robustness_ghg.csv")
r2 = pd.read_csv("tables/robustness_extended.csv")
perm = json.load(open("tables/permutation_test.json"))
draws = pd.read_csv("tables/permutation_draws.csv")

rows = []
def take(df, spec, label, group, note=""):
    m = df[df.spec == spec]
    if not len(m): return
    r = m.iloc[0]
    b = r.att if "att" in m.columns and pd.notna(r.get("att")) else np.log(1 + r.effect_pct / 100)
    se = r.se
    rows.append({"label": label, "group": group, "eff": pct(b),
                 "lo": pct(b - 1.96 * se), "hi": pct(b + 1.96 * se),
                 "sig": (r.sig if isinstance(r.sig, str) else "")})
take(r2, "Baseline (CS, never-treated)", "Baseline (CS, never-treated)", "Baseline")
take(r1, "Not-yet-treated controls", "Not-yet-treated control group", "Design")
take(r2, "Anticipation: 1 year", "Allow 1-year anticipation", "Design")
take(r2, "Covariate-adjusted CS (DR, baseline-2012 X)", "Doubly robust, baseline-2012 covariates", "Design")
take(r1, "Exclude COVID (panel ends 2019)", "Panel ends 2019 (pre-COVID)", "Sample")
take(r2, "Exclude COVID years (2020-2021), 2x2", "Drop 2020–21 (2×2 estimator)", "Sample")
take(r2, "Exclude Europe", "Exclude Europe", "Sample")
take(r2, "Drop later-reversed targets", "Drop later-reversed targets", "Sample")
take(r1, "Treatment = binding (law) year", "Treatment = in-law year only", "Treatment coding")
take(r2, "Broad coding: any neutrality-type target", "Any neutrality-type target", "Treatment coding")
take(r2, "Total GHG (not per capita)", "Total (not per-capita) GHG", "Outcome")
take(r2, "Consumption-based CO2 pc (leakage test)", "Consumption-based CO₂ (leakage test)", "Outcome")
take(r1, "Placebo (fake 2015 timing, pre-2019)", "Placebo: fake 2015 timing, pre-2019 data", "Placebo")
rr = pd.DataFrame(rows)

fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.6, 4.6), width_ratios=[2.05, 1],
                               constrained_layout=True)
y = np.arange(len(rr))[::-1]
axL.axvline(0, color=C["zero"], lw=0.9, zorder=1)
base_eff = rr.iloc[0].eff
axL.axvline(base_eff, color=C["blue"], lw=0.8, ls=(0, (2, 2)), alpha=0.55, zorder=1)
for i, (_, r) in enumerate(rr.iterrows()):
    if r.group == "Placebo": col = C["orange"]
    elif r.group == "Baseline": col = C["blue"]
    elif r.sig == "": col = C["muted"]
    else: col = C["blue"]
    axL.plot([r.lo, r.hi], [y[i], y[i]], color=col, lw=1.7, zorder=3,
             solid_capstyle="round")
    axL.plot([r.eff], [y[i]], "o", ms=6, mfc=col, mec="white", mew=1, zorder=4)
axL.set_yticks(y)
axL.set_yticklabels(rr.label, fontsize=8.6, color=C["ink"])
# group separators
grp = rr.group.values
for i in range(1, len(grp)):
    if grp[i] != grp[i - 1]:
        axL.axhline(y[i] + 0.5, color=C["grid"], lw=0.7)
axL.set_xlabel("Effect on GHG per capita (%), 95% CI")
title(axL, "The headline result is stable across design, sample,\ncoding and outcome variations",
      x=-0.62)
style_ax(axL, grid="x")

axR.hist(100 * (np.exp(draws.draw_att) - 1), bins=24, color=C["na"],
         edgecolor="white", lw=0.6, zorder=2)
obs = pct(perm["observed_att"])
axR.axvline(obs, color=C["blue"], lw=1.8, zorder=3)
axR.annotate(f"observed\n{obs:+.1f}%", (obs, axR.get_ylim()[1] * 0.86),
             xytext=(6, 0), textcoords="offset points", color=C["blue"],
             fontsize=8.4, fontweight="bold")
axR.set_xlabel("Placebo ATT (%)")
axR.set_ylabel("Placebo draws")
axR.set_xlim(min(obs * 1.25, axR.get_xlim()[0]), axR.get_xlim()[1])
pv = perm["p_value"]; nd = perm["n_draws"]
title(axR, "Permutation test",
      f"{nd} draws; p {'<' if pv == 0 else '='} {max(pv, 1/nd):.3f}", x=-0.2)
style_ax(axR)
save(fig, "fig_robustness")
print("done")
