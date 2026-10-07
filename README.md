# National Net-Zero Target Adoption and Emissions Panel, 2000–2024: Replication Data and Code

Data and code for the article **"Do national net-zero pledges reduce emissions? A longitudinal cross-country analysis."**

The repository contains the harmonised country-year panel that links each country's adoption of a national net-zero target to its greenhouse-gas emissions, energy mix, institutions and socioeconomic structure. It also contains the scripts that produce every number, table and figure in the article.

- **Archived version (DOI):** [10.5281/zenodo.22794288](https://doi.org/10.5281/zenodo.22794288)
- **Repository:** https://github.com/sugandhke/net_zero_data_code

## Contents

```
net_zero_data_code/
├── README.md                  this file
├── sustain_data/
│   ├── analysis_panel.csv     harmonised country-year panel (the single analysis input)
│   ├── tables/                result files behind Tables 2–10 and Figures 2–8
│   ├── geo/                   Natural Earth country boundaries (adoption map)
│   └── README.md              map of result files to manuscript tables and figures
└── sustain_code/
    ├── 01_build_panel.py      builds the panel from the raw sources
    ├── main_ghg_analysis_v2.py, subgroup_ghg.py, regional_ghg.py, energy_mechanism.py,
    │   extended_robustness*.py, robustness_ghg.py, rq3_and_appendix.py, build_table_inputs.py
    │                          analysis (estimators, heterogeneity, robustness, air quality)
    ├── gen_notitle_*.py       figures
    ├── build_sd_*.py, fix_*.py, apply_emdash.py
    │                          manuscript-assembly helpers (not needed to reproduce results)
    └── README.md              run order
```

## The dataset: `sustain_data/analysis_panel.csv`

- **Unit:** country-year. One row per country (ISO 3166-1 alpha-3 code) and calendar year.
- **Coverage:** 218 countries and territories, 2000–2024, with 5,450 rows and 96 variables. The article's estimation sample is 2012–2024, restricted for each outcome to the largest balanced sub-panel (209 country units, 2,717 country-years for the headline outcome).
- **Format:** comma-separated values, UTF-8, one header row; missing values are empty cells.

### Variable groups

| Group | Variables (examples) | Source |
|---|---|---|
| Identifiers | `country`, `iso3`, `year`, `continent`, `country_id` | — |
| Net-zero adoption and treatment | `adopt_year_any`, `adopt_year_netzero`, `adopt_year_binding`, `target_reversed`, `self_achieved`, `first_treat`, `treated`, `post`, `rel_year` | Net Zero Tracker national targets register (30 Oct 2025 vintage) |
| Emissions (per capita) | `ghg_per_capita`, `ghg_excluding_lucf_per_capita`, `co2_per_capita`, `co2_including_luc_per_capita`, `coal_co2_per_capita`, `oil_co2_per_capita`, `gas_co2_per_capita`, `methane_per_capita`, `nitrous_oxide_per_capita`, `consumption_co2_per_capita` | Our World in Data / Global Carbon Budget |
| Energy and electricity mix | `renewables_share_elec`, `low_carbon_share_elec`, `fossil_share_elec`, `coal_share_elec`, `solar_share_elec`, `wind_share_elec`, `energy_per_capita`, `energy_per_gdp` | Our World in Data energy dataset |
| Institutions | `v2x_polyarchy`, `v2x_libdem`, `v2x_rule`, `v2x_corr` | V-Dem v15 |
| Socioeconomic structure and air quality | `gdp_pc_ppp`, `urban_pct`, `trade_pct_gdp`, `industry_pct_gdp`, `energy_intensity_mj`, `pm25`, `pm_damage_gni`, `clean_cook_pct` | World Bank World Development Indicators |
| Analysis transforms | `ln_ghgpc`, `ln_co2pc`, `ln_coalco2`, `ln_gasco2`, `ln_ch4pc`, `ln_n2opc`, `ln_conspc`, … | Natural logs of the per-capita series, computed in `01_build_panel.py` |

Treatment timing (`first_treat`) is the first calendar year in which an explicit net-zero target appears in any status category; it is `0` for countries that never adopt. `adopt_year_binding` records the year a target was enshrined in law, which is used for the conservative robustness check.

## Reproducing the results

Requirements: Python 3.13 with pandas, numpy, matplotlib, pyfixest, csdid (Callaway–Sant'Anna estimator), honestdid (Rambachan–Roth sensitivity), geopandas and pycountry-convert. The manuscript-assembly helpers additionally use python-docx.

1. **(Optional)** Rebuild the panel from the raw sources with `sustain_code/01_build_panel.py`. The raw downloads are not redistributed here; obtain them from the sources below.
2. **Run the analysis** from the repository root in the order given in [`sustain_code/README.md`](sustain_code/README.md), starting from the provided `sustain_data/analysis_panel.csv`.
3. **Check the outputs.** Results are written as CSV/JSON tables. [`sustain_data/README.md`](sustain_data/README.md) maps each file to the corresponding table or figure.

All stochastic steps (bootstrap, permutation tests) are seeded, so re-runs are deterministic. Figure 1 (study design) is a hand-drawn schematic and is not script-generated.

## Data sources

- Van Coppenolle, H., Van de Graaf, T., & Blondeel, M. (2022). National net zero (or adjacent) targets [Data set]. Zenodo. https://zenodo.org/records/19296074
- Friedlingstein, P., et al. (2023). Global Carbon Budget 2023. *Earth System Science Data*, 15, 5301–5369. https://doi.org/10.5194/essd-15-5301-2023
- Ritchie, H., & Roser, M. (2023). CO₂ and greenhouse gas emissions. Our World in Data. https://ourworldindata.org/co2-and-greenhouse-gas-emissions
- Coppedge, M., et al. (2025). V-Dem dataset v15. Varieties of Democracy (V-Dem) Project. https://www.v-dem.net
- World Bank. (2024). World Development Indicators. https://databank.worldbank.org/source/world-development-indicators

The derived panel is shared for replication. Reuse of the underlying series is subject to each source's own terms of use.

## How to cite

If you use these data or code, please cite the article and the archived dataset:

> National Net-Zero Target Adoption and Emissions Panel, 2000–2024: Replication Data and Code. Zenodo. https://doi.org/10.5281/zenodo.22794288
