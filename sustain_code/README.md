# Reproducibility bundle — *Sustainable Development* submission

This folder holds the code that produces every number, table and figure in the
submission. Run everything from the **project root** with the project venv
(`.venv/bin/python`, Python 3.13). Inputs live in `../sustain_data/`.

## Run order

```
# 1. (optional) rebuild the panel from raw sources in ../data/
#    the analysis input analysis_panel.csv is already provided in ../sustain_data/
.venv/bin/python sustain_code/01_build_panel.py          # -> out/analysis_panel.csv

# 2. core analysis (reads out/analysis_panel.csv -> tables/*.csv)
.venv/bin/python sustain_code/main_ghg_analysis_v2.py    # Table 2, event study, pre-trends
.venv/bin/python sustain_code/subgroup_ghg.py            # Table 4 (income), Table 5 (institutions)
.venv/bin/python sustain_code/regional_ghg.py            # Table 3 (continent), regional event studies
.venv/bin/python sustain_code/energy_mechanism.py        # Table 9 (electricity mix)
.venv/bin/python sustain_code/extended_robustness.py     # Table 7 suite, permutation, HonestDiD, raw trends
.venv/bin/python sustain_code/extended_robustness_part2.py
.venv/bin/python sustain_code/robustness_ghg.py          # Table 7 (headline robustness)
.venv/bin/python sustain_code/rq3_and_appendix.py        # Table 6 (determinants), Table 10 (air quality)
.venv/bin/python sustain_code/build_table_inputs.py      # MDE / manuscript_table_inputs.csv

# 3. figures WITHOUT titles (titles live in the manuscript captions instead)
.venv/bin/python sustain_code/gen_notitle_pub.py         # Fig 2,3,6,7 -> out/figs_notitle/
.venv/bin/python sustain_code/gen_notitle_raghu.py       # Fig 4,5,8 -> out/figs_notitle/
```

## Notes
- All analysis is seeded (`np.random.seed`), so re-runs are deterministic.
- Figures 2–8 are drawn directly from the `tables/*.csv` result files; Figure 1
  (study design) is a hand-built schematic, not script-generated.
- The `build_sd_*.py`, `apply_emdash.py`, `fix_refs_emdash.py`,
  `fix_four_issues.py`, `fix_citation_superscripts.py` scripts assemble/format
  the submission `.docx` (APA refs, renumbering, em-dash removal, formatting fixes).
- Manuscript figure ↔ script output map:
  Fig2=fig_raw_trends, Fig3=fig_eventstudy, Fig4=fig2_composite, Fig5=fig3_map,
  Fig6=fig_regional_eventstudy, Fig7=fig_robustness, Fig8=fig4_composite.
