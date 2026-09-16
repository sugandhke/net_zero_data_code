# Data bundle — *Sustainable Development* submission

Inputs and results used by the scripts in `../sustain_code/`.

- `analysis_panel.csv` — the harmonised country-year panel (209 countries,
  2012–2024) that all analysis scripts read. This is the single analysis input.
- `tables/` — every result CSV/JSON produced by the pipeline (one consistent
  vintage). Tables 2–10 and Figures 2–8 in the manuscript are drawn from these:
    - `main_ghg_v2.csv` → Table 2 (GHG decomposition, CS + 2×2)
    - `regional_ghg.csv` → Table 3 (continent)
    - `impact_income.csv` → Table 4 (income terciles)
    - `impact_vdem.csv` → Table 5 (rule-of-law terciles)
    - `adoption_determinants.csv` → Table 6 (adoption determinants)
    - `robustness_ghg.csv`, `robustness_extended.csv`, `permutation_test.json`
      → Table 7 (robustness suite)
    - `honestdid_sensitivity.csv` → Table 8 (HonestDiD bounds)
    - `energy_mechanism.csv` → Table 9 (electricity mix)
    - `airquality_rq3.csv` → Table 10 (air quality)
    - `pretrends_cs.csv`, `eventstudy_2x2.csv`, `pretrends_summary.csv`,
      `raw_trends.csv`, `regional_eventstudy.csv`, `adoption_countries.csv`
      → Figures 2, 3, 5, 6
- `geo/` — Natural Earth country boundaries for the adoption map (Figure 5).

Raw upstream sources (Net Zero Tracker, OWID/Global Carbon Budget, V-Dem, World
Bank WDI) live in the project `../data/` folder and feed `01_build_panel.py`.
