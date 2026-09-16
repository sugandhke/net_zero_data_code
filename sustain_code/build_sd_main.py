"""
build_sd_main.py — produce the anonymised Main Text file for Sustainable
Development from NetZero_Manuscript_NCC_v32.docx:
  * numbered/superscript citations -> APA (Author, Year); multi-cites alphabetised
  * numbered reference list -> APA 6th, alphabetical
  * headings: Main -> Introduction; Methods -> Materials and Methods
  * section order -> Introduction, Materials and Methods, Results, Discussion,
    Conclusion, Data availability, Competing interests, References
  * Abstract cut to <=150 words (no citations); Keywords + Practitioner Points added
  * captions relabelled Fig.->Figure and "N |"->"N."; in-text "Fig."->"Figure"
  * AI-use / reproducibility statement added to Materials and Methods
Writes sustainable_submission/1_Main_Text.docx
"""
import json, re, copy
import docx
from docx.shared import Pt
from docx.oxml.ns import qn

R = json.load(open("sustainable_submission/_refs.json"))
INTEXT = {int(k):tuple(v) if isinstance(v,list) else v for k,v in R["intext"].items()}
SORT   = {int(k):v for k,v in R["sortkey"].items()}
REFLIST = R["reflist"]

d = docx.Document("NetZero_Manuscript_NCC_v32.docx")

# ---------- 1. citation replacement (superscript numbers -> APA parenthetical) ----------
def cite_text(token):
    nums=[int(x) for x in token.replace(" ","").split(",") if x]
    items=sorted(nums, key=lambda n: SORT[n])
    return "(" + "; ".join(INTEXT[n] for n in items) + ")"

for p in d.paragraphs:
    runs=p.runs
    for i,r in enumerate(runs):
        if r.font.superscript and re.fullmatch(r"[0-9,]+", r.text.strip() or ""):
            prev="".join(x.text for x in runs[:i])
            lead="" if (prev and prev[-1] in " ([") else " "
            r.text = lead + cite_text(r.text.strip())
            r.font.superscript = False

# ---------- 2. caption / figure-reference relabelling ----------
for p in d.paragraphs:
    for r in p.runs:
        if "Fig. " in r.text:
            r.text = r.text.replace("Fig. ", "Figure ")
    t=p.text
    if (t.startswith("Figure ") or t.startswith("Table ")) and " | " in t:
        for r in p.runs:
            if " | " in r.text:
                r.text = r.text.replace(" | ", ". ")

# ---------- 3. heading renames ----------
def set_para_text(p, text, bold=None):
    for r in list(p.runs)[1:]:
        r._r.getparent().remove(r._r)
    if p.runs:
        p.runs[0].text = text
        if bold is not None: p.runs[0].bold = bold
    else:
        r=p.add_run(text)
        if bold is not None: r.bold=bold

for p in d.paragraphs:
    if p.style and 'Heading 1' in (p.style.name or ''):
        if p.text.strip()=="Main": set_para_text(p,"Introduction")
        elif p.text.strip()=="Methods": set_para_text(p,"Materials and Methods")

# ---------- 4. Abstract -> <=150 words, no citations ----------
ABSTRACT=("More than 140 countries have adopted national net-zero targets, yet whether "
 "adoption is followed by measurable emission changes — and for whom — remains unclear. "
 "Using a country-year panel of 209 states from 2012 to 2024 and a staggered "
 "difference-in-differences design robust to two-way fixed-effects bias, we find that "
 "adoption is followed by an approximately 5 per cent reduction in greenhouse-gas "
 "emissions per capita, accumulating to roughly 9 per cent after five years. The "
 "response is sharply sectoral: coal and gas carbon dioxide fall while oil, methane and "
 "nitrous oxide are unchanged, mediated by a shift of electricity generation toward "
 "renewables. Effects are gated by state capacity — largest in high-income, "
 "strong-rule-of-law countries — yet survive excluding Europe, and consumption-based "
 "emissions fall equally, ruling out leakage. No air-quality co-benefit is detectable. "
 "Net-zero commitments deliver real but narrow reductions, concentrated where "
 "implementation capacity already exists.")
assert len(ABSTRACT.split())<=150, len(ABSTRACT.split())

paras=d.paragraphs
def h1_index(name):
    for i,p in enumerate(paras):
        if p.style and 'Heading 1' in (p.style.name or '') and p.text.strip()==name:
            return i
    return None
ab=h1_index("Abstract")
# replace first body paragraph after Abstract; delete any further body paras
j=ab+1; first=True
while j<len(paras) and not (paras[j].style and 'Heading 1' in (paras[j].style.name or '')):
    if paras[j].text.strip():
        if first:
            set_para_text(paras[j], ABSTRACT); first=False
        else:
            paras[j]._p.getparent().remove(paras[j]._p)
    j+=1

# ---------- 5. Data availability text improved (still anonymous) ----------
for p in d.paragraphs:
    if p.text.strip().startswith("All data are available in the study"):
        set_para_text(p,
          "All data underlying this study are from publicly available sources: the "
          "national net-zero targets register (Van Coppenolle et al., 2022), Our World "
          "in Data’s harmonisation of the Global Carbon Budget and energy statistics "
          "(Friedlingstein et al., 2023; Ritchie & Roser, 2023), the V-Dem v15 dataset "
          "(Coppedge et al., 2025) and the World Bank World Development Indicators "
          "(World Bank, 2024). The assembled country-year panel and the analysis code "
          "will be deposited in a public repository [DOI to be added on acceptance].")

# ===================================================================
# 6. STRUCTURAL: build new element and reorder body
# ===================================================================
body = d.element.body
pmap = {p._p: p for p in d.paragraphs}

def para_el(text, style=None, bold=False, italic=False, size=None, space_after=6):
    p = d.add_paragraph()
    if style: p.style = style
    run = p.add_run(text)
    run.bold=bold; run.italic=italic
    if size: run.font.size=Pt(size)
    p.paragraph_format.space_after=Pt(space_after)
    return p._p

def label_para(label, body_text):
    p=d.add_paragraph()
    r=p.add_run(label); r.bold=True
    p.add_run(body_text)
    return p._p

# anchors (elements)
def h1_el(name):
    for p in d.paragraphs:
        if p.style and 'Heading 1' in (p.style.name or '') and p.text.strip()==name:
            return p._p
    return None
def h2_el(name):
    for p in d.paragraphs:
        if p.style and 'Heading 2' in (p.style.name or '') and p.text.strip()==name:
            return p._p
    return None

el_abstract=h1_el("Abstract")
el_intro=h1_el("Introduction")
el_results=h1_el("Results")
el_discussion=h1_el("Discussion")
el_refs=h1_el("References")
el_methods=h1_el("Materials and Methods")
el_dataavail=h2_el("Data availability")
el_competing=h2_el("Competing interests")

# collect contiguous segment [start_el .. next boundary) as list of elements
allchildren=[c for c in body.iterchildren() if c.tag in (qn('w:p'),qn('w:tbl'))]
def seg(start_el, stop_els):
    out=[]; started=False
    for c in allchildren:
        if c is start_el: started=True
        elif started and c in stop_els: break
        if started: out.append(c)
    return out

methods_core = seg(el_methods, {el_dataavail, el_competing, el_refs})
seg_dataavail = seg(el_dataavail, {el_competing, el_refs})
seg_competing = seg(el_competing, {el_refs})
# capture the ORIGINAL numbered reference paragraphs now (before any moves),
# so the later rebuild deletes exactly these and not the relocated Methods block
orig_ref_paras = seg(el_refs, {el_methods})[1:]

# --- move Materials and Methods (core) to before Results ---
for el in methods_core:
    el_results.addprevious(el)   # moves each element; order preserved

# --- add Conclusion after Discussion (before References) ---
CONCLUSION=("National net-zero targets, the central commitment device of contemporary "
 "climate governance, are followed by measurable emission reductions: adoption lowers "
 "greenhouse-gas emissions per capita by about 5 per cent, accumulating over five years, "
 "with flat pre-adoption trends and robustness to permutation inference, placebo timing "
 "and three treatments of the pandemic. The reduction is real but narrow — concentrated "
 "in coal and gas combustion, mediated by a cleaner electricity mix, and confined to "
 "high-income, high-capacity adopters, with no detectable air-quality co-benefit and no "
 "evidence of carbon leakage. For the sustainable-development agenda these findings "
 "describe conditional rather than automatic synergies: climate action delivers where "
 "institutional capacity and economic structure already permit. Realising the promise of "
 "net-zero pledges will require sector-specific instruments beyond electricity, "
 "implementation support for lower-capacity states, and review mechanisms — including "
 "the Global Stocktake — that measure delivery rather than count commitments.")
concl_h=para_el("Conclusion", style="Heading 1")
concl_b=para_el(CONCLUSION)
# place Conclusion, then Data availability + Competing interests, all before References
el_refs.addprevious(concl_h)
el_refs.addprevious(concl_b)
for el in seg_dataavail: el_refs.addprevious(el)
for el in seg_competing: el_refs.addprevious(el)

# ---------- 7. AI-use / reproducibility statement into Materials and Methods ----------
# append after the last methods-core element that is a paragraph
ai_stmt=para_el(
 "Software and reproducibility. Analyses were implemented in Python (pandas, "
 "csdid/drdid, pyfixest and geopandas); all tables and figures were generated "
 "programmatically from the estimation output. A large-language-model coding assistant "
 "was used to help write, refactor and document the analysis and figure-production "
 "scripts and to format tables, under the authors’ direction; all results, their "
 "interpretation and the final text are the authors’ own, and every reported number was "
 "verified against the estimation output.", italic=False)
# insert just before Data availability's new location (i.e., before References block start = concl_h)
concl_h.addprevious(ai_stmt)

# ---------- 8. Keywords + Practitioner Points after Abstract, before Introduction ----------
kw = label_para("Keywords: ",
     "net-zero targets; climate policy; greenhouse-gas emissions; "
     "difference-in-differences; sustainable development goals; state capacity")
pp_head = para_el("Practitioner Points", style="Heading 2")
def bullet(text):
    p=d.add_paragraph()
    p.paragraph_format.left_indent=Pt(18)
    p.paragraph_format.first_line_indent=Pt(-12)
    p.paragraph_format.space_after=Pt(4)
    p.add_run("•  "+text)
    return p._p
pp1=bullet("National net-zero pledges are, on average, followed by measurable emission "
    "reductions (about 5 per cent per capita), but only where administrative capacity is strong.")
pp2=bullet("The response runs almost entirely through the power sector (coal and gas); transport, "
    "agriculture and local air quality are untouched, so pledges need sector-specific instruments to broaden.")
pp3=bullet("Review mechanisms such as the Global Stocktake should track implementation indicators, "
    "not merely count commitments, since legally-equivalent pledges differ in measured effect.")
# order: Abstract(+text) -> Keywords -> Practitioner Points(head+3 bullets) -> Introduction
el_intro.addprevious(kw)
el_intro.addprevious(pp_head)
for e in (pp1, pp2, pp3): el_intro.addprevious(e)

# ---------- 9. rebuild References (APA alphabetical) ----------
for c in orig_ref_paras:                       # delete exactly the old numbered refs
    if c.getparent() is not None:
        c.getparent().remove(c)
anchor=el_refs
for ref in REFLIST:
    p=d.add_paragraph()
    p.paragraph_format.space_after=Pt(6)
    p.paragraph_format.left_indent=Pt(18)
    p.paragraph_format.first_line_indent=Pt(-18)   # hanging indent
    p.add_run(ref)
    anchor.addnext(p._p); anchor=p._p

# ---------- 10. promote/retitle end statements to Wiley house style ----------
RENAME={"Data availability":"Data Availability Statement","Competing interests":"Conflict of Interest"}
for p in d.paragraphs:
    t=p.text.strip()
    if t in RENAME and p.style and 'Heading 2' in (p.style.name or ''):
        p.style=d.styles['Heading 1']
        set_para_text(p, RENAME[t])

d.save("sustainable_submission/1_Main_Text.docx")
print("saved sustainable_submission/1_Main_Text.docx")
print("abstract words:", len(ABSTRACT.split()))
