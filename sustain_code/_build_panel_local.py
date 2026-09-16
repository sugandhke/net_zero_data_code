"""
=============================================================================
01_build_panel.py — Construct country-year panel for net-zero DiD analysis
=============================================================================
Inputs
------
1. Net Zero Tracker country commitments CSV (2025-10-30 vintage)
2. OWID CO2 dataset  (primary source: Global Carbon Budget, Friedlingstein
   et al. 2025; GHG/CH4/N2O from Jones et al. 2024, PRIMAP)
3. OWID Energy dataset (primary sources: Energy Institute Statistical
   Review; Ember electricity data)
4. V-Dem Country-Year v15 (governance covariates)
5. OPTIONAL: wdi_panel.csv (World Bank WDI) — extra covariates (urban share,
   trade openness, PM2.5, etc.). Merged automatically if present.

Output
------
analysis_panel.csv — one row per country-year, 2000-2024
=============================================================================
"""

import os
import numpy as np
import pandas as pd

UPLOADS = "uploads"
DATA    = "data"
OUT     = "out"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. TREATMENT: Net Zero Tracker commitments
# ---------------------------------------------------------------------------
nz = pd.read_csv(f"{UPLOADS}/2025-10-30_Net-Zero_commitments.csv")

# Normalise target labels (same harmonisation as emission_did2.ipynb)
nz["end_target"] = (
    nz["end_target"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
      .replace({"Net zero": "Net Zero",
                "Carbon neutral(ity)": "Carbon Neutral",
                "Climate neutral": "Carbon Neutral",
                "Zero carbon": "Carbon Neutral"})
)
nz["status_year"] = pd.to_datetime(nz["status_date"], errors="coerce",
                                   format="mixed").dt.year

# --- main treatment: explicit *net zero* target (any status) --------------
is_nz = nz["end_target"].eq("Net Zero")

first_treat = (nz.loc[is_nz].groupby("country")["status_year"].min()
                 .rename("adopt_year_netzero"))

# --- stricter treatment: target enshrined in law / policy document --------
binding = nz["end_target_status"].isin(["In law", "In policy document"])
first_binding = (nz.loc[is_nz & binding].groupby("country")["status_year"].min()
                   .rename("adopt_year_binding"))

# --- broader treatment: any neutrality-type target -------------------------
is_any = nz["end_target"].isin(["Net Zero", "Carbon Neutral"])
first_any = (nz.loc[is_any].groupby("country")["status_year"].min()
               .rename("adopt_year_any"))

# --- flags: reversal (later 'No Net Zero' record) & pre-achieved -----------
last_record = (nz.sort_values("status_year").groupby("country").tail(1)
                 .set_index("country"))
reversed_flag = (last_record["end_target"].eq("No Net Zero")
                 .rename("target_reversed"))
achieved_flag = (nz.assign(a=nz["end_target_status"]
                             .eq("Achieved (self-declared)"))
                   .groupby("country")["a"].max().rename("self_achieved"))

treat = (pd.concat([first_treat, first_binding, first_any,
                    reversed_flag, achieved_flag], axis=1)
           .reset_index().rename(columns={"country": "iso3"}))
# countries appearing in tracker but never with a net-zero-type target keep NaN

# ---------------------------------------------------------------------------
# 2. OUTCOMES: OWID CO2 (Global Carbon Budget) + OWID Energy
# ---------------------------------------------------------------------------
co2_cols = ["iso_code", "country", "year",
            "co2_per_capita",            # t CO2 / person   (GCB, excl. LUC)
            "co2", "co2_per_gdp",        # Mt; kg per intl-$ GDP
            "consumption_co2_per_capita",# consumption-based (leakage check)
            "ghg_per_capita",            # t CO2e / person (all GHG incl LUCF)
            "ghg_excluding_lucf_per_capita",  # all GHG excl land use (decomp)
            "co2_including_luc_per_capita",   # CO2 incl land-use change
            "methane_per_capita", "nitrous_oxide_per_capita",
            "coal_co2_per_capita", "oil_co2_per_capita",
            "gas_co2_per_capita", "cement_co2_per_capita",
            "land_use_change_co2_per_capita",
            "energy_per_capita",         # kWh primary energy / person
            "energy_per_gdp",
            "gdp", "population"]
co2 = pd.read_csv(f"{DATA}/owid-co2-data.csv", usecols=co2_cols)

en_cols = ["iso_code", "year",
           "renewables_share_energy",    # % primary energy
           "fossil_share_elec", "low_carbon_share_elec",
           "coal_share_elec",            # guide priority: coal phase-out signal
           "renewables_share_elec", "solar_share_elec", "wind_share_elec"]
en = pd.read_csv(f"{DATA}/owid-energy-data.csv", usecols=en_cols)

# keep sovereign countries only (drop OWID regional aggregates)
co2 = co2[co2["iso_code"].notna()
          & (co2["iso_code"].str.len() == 3)
          & (co2["year"] >= 2000)]
panel = co2.merge(en, on=["iso_code", "year"], how="left")
panel = panel.rename(columns={"iso_code": "iso3"})

# ---------------------------------------------------------------------------
# 3. COVARIATES: V-Dem v15
# ---------------------------------------------------------------------------
try:
    import pyreadstat
    vdem, _ = pyreadstat.read_dta(
        f"{UPLOADS}/V-Dem-CY-Full_Others-v15.dta",
        usecols=["country_text_id", "year", "v2x_polyarchy",
                 "v2x_libdem", "v2x_corr", "v2x_rule"])
except Exception:                                    # fallback
    vdem = pd.read_stata(f"{UPLOADS}/V-Dem-CY-Full_Others-v15.dta",
                         columns=["country_text_id", "year", "v2x_polyarchy",
                                  "v2x_libdem", "v2x_corr", "v2x_rule"],
                         convert_categoricals=False)
vdem = vdem[vdem["year"] >= 2000].rename(columns={"country_text_id": "iso3"})
panel = panel.merge(vdem, on=["iso3", "year"], how="left")

# ---------------------------------------------------------------------------
# 4. WDI covariates & health outcomes (from wdi_data.csv, World Bank WDI)
#    Extracts: urbanisation, trade openness, PM2.5, renewable-energy share,
#    manufacturing share, energy intensity, R&D, GDP pc PPP, forest cover.
# ---------------------------------------------------------------------------
def build_wdi():
    w = pd.read_csv(f"{UPLOADS}/wdi_data.csv")
    want = {"SP.URB.TOTL.IN.ZS":"urban_pct","NE.TRD.GNFS.ZS":"trade_pct_gdp",
            "EN.ATM.PM25.MC.M3":"pm25","SH.STA.AIRP.P5":"mortality_airpoll",
            "GB.XPD.RSDV.GD.ZS":"rd_pct_gdp","EG.FEC.RNEW.ZS":"renew_energy_pct",
            "NV.IND.MANF.ZS":"manuf_pct_gdp","NV.IND.TOTL.ZS":"industry_pct_gdp",
            "EG.EGY.PRIM.PP.KD":"energy_intensity_mj","SI.POV.GINI":"gini",
            "NY.GDP.PCAP.PP.KD":"gdp_pc_ppp","SP.POP.TOTL":"pop_wdi",
            "AG.LND.FRST.ZS":"forest_pct","EG.ELC.ACCS.ZS":"elec_access_pct",
            # --- health & air-quality co-benefit outcomes (RQ2) ---
            "EN.ATM.PM25.MC.ZS":"pm25_pop_exceed","EG.CFT.ACCS.ZS":"clean_cook_pct",
            "SP.DYN.LE00.IN":"life_exp","SP.DYN.IMRT.IN":"infant_mort",
            "SH.DYN.NCOM.ZS":"ncd_mort","NY.ADJ.DPEM.GN.ZS":"pm_damage_gni",
            # --- energy security & economic structure (RQ2) ---
            "EG.IMP.CONS.ZS":"energy_imports_pct","EG.ELC.RNEW.ZS":"renew_elec_out_pct",
            "EG.ELC.NUCL.ZS":"nuclear_elec_pct","NV.SRV.TOTL.ZS":"services_pct_gdp",
            "TX.VAL.TECH.MF.ZS":"hitech_exp_pct","EG.USE.ELEC.KH.PC":"elec_cons_pc"}
    w = w[w["Indicator Code"].isin(want)].copy()
    yc = [c for c in w.columns if c.isdigit()]
    long = w.melt(id_vars=["Country Code","Indicator Code"], value_vars=yc,
                  var_name="year", value_name="val")
    long["year"] = long["year"].astype(int)
    long["var"]  = long["Indicator Code"].map(want)
    wp = (long.pivot_table(index=["Country Code","year"], columns="var",
                           values="val", aggfunc="first").reset_index()
              .rename(columns={"Country Code":"iso3"}))
    return wp

wdi_raw = f"{UPLOADS}/wdi_data.csv"
if os.path.exists(wdi_raw):
    wdi = build_wdi()
    panel = panel.merge(wdi, on=["iso3", "year"], how="left")
    print("WDI covariates merged:", [c for c in wdi.columns if c not in ("iso3","year")])
else:
    print("NOTE: wdi_data.csv not found — proceeding without WDI covariates.")

# ---------------------------------------------------------------------------
# 5. TREATMENT VARIABLES ON THE PANEL
# ---------------------------------------------------------------------------
panel = panel.merge(treat, on="iso3", how="left")
panel["target_reversed"] = panel["target_reversed"].fillna(False)
panel["self_achieved"]   = panel["self_achieved"].fillna(False)

# first_treat = 0 for never-treated (convention used by did / csdid)
panel["first_treat"] = panel["adopt_year_netzero"].fillna(0).astype(int)
panel["treated"]     = (panel["first_treat"] > 0).astype(int)
panel["post"]        = (panel["year"] >= panel["first_treat"]) \
                         .where(panel["treated"].eq(1), 0).astype(int)
panel["did_term"]    = panel["treated"] * panel["post"]
panel["rel_year"]    = np.where(panel["treated"].eq(1),
                                panel["year"] - panel["first_treat"], np.nan)

# transformed outcomes / covariates
panel["ln_co2pc"]    = np.log(panel["co2_per_capita"].where(panel["co2_per_capita"] > 0))
panel["ln_ghgpc"]    = np.log(panel["ghg_per_capita"].where(panel["ghg_per_capita"] > 0))
panel["ln_ch4pc"]    = np.log(panel["methane_per_capita"].where(panel["methane_per_capita"] > 0))
panel["ln_energypc"] = np.log(panel["energy_per_capita"].where(panel["energy_per_capita"] > 0))
panel["ln_co2gdp"]   = np.log(panel["co2_per_gdp"].where(panel["co2_per_gdp"] > 0))
panel["ln_conspc"]   = np.log(panel["consumption_co2_per_capita"]
                              .where(panel["consumption_co2_per_capita"] > 0))
panel["ln_n2opc"]    = np.log(panel["nitrous_oxide_per_capita"]
                              .where(panel["nitrous_oxide_per_capita"] > 0))
panel["ln_energygdp"] = np.log(panel["energy_per_gdp"].where(panel["energy_per_gdp"] > 0))
panel["gdp_pc"]      = panel["gdp"] / panel["population"]
panel["ln_gdppc"]    = np.log(panel["gdp_pc"])
panel["ln_pop"]      = np.log(panel["population"])
panel["ln_pm25"]     = np.log(panel["pm25"].where(panel.get("pm25", pd.Series(index=panel.index)) > 0)) if "pm25" in panel else np.nan
panel["ln_lifeexp"]  = np.log(panel["life_exp"].where(panel["life_exp"] > 0)) if "life_exp" in panel else np.nan
panel["ln_infmort"]  = np.log(panel["infant_mort"].where(panel["infant_mort"] > 0)) if "infant_mort" in panel else np.nan
# energy imports can be negative (net exporters); keep level, not log
panel["energy_imp"]  = panel["energy_imports_pct"] if "energy_imports_pct" in panel else np.nan
# gas-decomposition outcomes (reviewer request)
for src_col,nm in [("ghg_excluding_lucf_per_capita","ln_ghgxlucf"),
                   ("co2_including_luc_per_capita","ln_co2luc"),
                   ("nitrous_oxide_per_capita","ln_n2o2"),
                   ("coal_co2_per_capita","ln_coalco2"),
                   ("oil_co2_per_capita","ln_oilco2"),
                   ("gas_co2_per_capita","ln_gasco2")]:
    if src_col in panel.columns:
        panel[nm]=np.log(panel[src_col].where(panel[src_col]>0))
# LULUCF share of GHG (to test if land use drives GHG effect)
if "ghg_per_capita" in panel and "ghg_excluding_lucf_per_capita" in panel:
    panel["lucf_ghg_pc"]=panel["ghg_per_capita"]-panel["ghg_excluding_lucf_per_capita"]
# macro control: GDP growth (for demand robustness)
panel=panel.sort_values(["iso3","year"])
panel["gdp_growth"]=panel.groupby("iso3")["gdp"].pct_change()*100
# continent for region-year FE
import pycountry_convert as pc
def _cont(i):
    try:
        c=pc.country_alpha2_to_continent_code(pc.country_alpha3_to_country_alpha2(i))
        return pc.convert_continent_code_to_continent_name(c)
    except Exception: return "Other"
panel["continent"]=panel["iso3"].map({i:_cont(i) for i in panel["iso3"].unique()})
panel["region_year"]=panel["continent"].astype(str)+"_"+panel["year"].astype(str)
panel["ln_energy_int"]= np.log(panel["energy_intensity_mj"].where(panel["energy_intensity_mj"] > 0)) if "energy_intensity_mj" in panel else np.nan
panel["urban_pct_z"] = panel["urban_pct"] if "urban_pct" in panel else np.nan
panel["country_id"]  = pd.factorize(panel["iso3"])[0] + 1

panel.to_csv(f"{OUT}/analysis_panel.csv", index=False)

# ---------------------------------------------------------------------------
# 6. DIAGNOSTICS
# ---------------------------------------------------------------------------
adopters = panel.loc[panel.treated.eq(1)].groupby("iso3")["first_treat"].first()
print(f"\nPanel: {panel.iso3.nunique()} countries x {panel.year.min()}-{panel.year.max()}")
print(f"Treated countries: {adopters.size} | never-treated: "
      f"{panel.iso3.nunique() - adopters.size}")
print("\nAdoption cohorts:\n", adopters.value_counts().sort_index())
print("\nReversals among treated:",
      panel.loc[panel.treated.eq(1)].groupby('iso3')['target_reversed'].first().sum())
print("Self-achieved:", panel.groupby('iso3')['self_achieved'].first().sum())
