"""
build_sd_v2.py — apply to 1_Main_Text_revised.docx:
  (1) renumber figures & tables to physical/appearance order (study design = Fig 1)
  (2) insert 20 new, Crossref-verified references as in-text citations at relevant points
  (3) merge them into the APA reference list, re-sorted alphabetically
Produces a HIGHLIGHTED copy (all changes yellow) and a CLEAN copy.
"""
import json, re, unicodedata, copy
import docx
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.ns import qn

SRC="sustainable_submission/1_Main_Text_revised.docx"
HL ="sustainable_submission/1_Main_Text_revised_highlighted.docx"
CLEAN="sustainable_submission/1_Main_Text_revised_clean.docx"

newrefs=json.load(open("sustainable_submission/_build/_newrefs.json"))
# fix Sognnæs spelling to match in-text
newrefs["sognnaes21"]["apa"]=newrefs["sognnaes21"]["apa"].replace("Sognnaes, I.","Sognnæs, I.")

d=docx.Document(SRC)

# ---------- segment engine: edit runs while preserving & marking formatting ----------
def runs_to_segs(p):
    segs=[]
    for r in p.runs:
        segs.append({"text":r.text,"src":r,"hl":False})
    return segs

def copy_fmt(dst_run, src_run):
    f=src_run.font
    df=dst_run.font
    dst_run.bold=src_run.bold; dst_run.italic=src_run.italic
    df.name=f.name; df.size=f.size; df.superscript=f.superscript
    try:
        if f.color and f.color.rgb is not None: df.color.rgb=f.color.rgb
    except Exception: pass

def rebuild(p, segs):
    # remove existing runs
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    for s in segs:
        if s["text"]=="":
            continue
        run=p.add_run(s["text"])
        if s["src"] is not None: copy_fmt(run, s["src"])
        if s["hl"]: run.font.highlight_color=WD_COLOR_INDEX.YELLOW

def edit_exact(p, old, new):
    """replace exact substring `old` (within OR across runs) with highlighted `new`,
    preserving surrounding formatting via a char->run map."""
    chars=[]  # (char, source_run)
    for r in p.runs:
        for ch in r.text: chars.append((ch, r))
    full="".join(c for c,_ in chars)
    idx=full.find(old)
    if idx<0: return False
    end=idx+len(old)
    def group(span):
        segs=[]
        for ch,src in span:
            h=(src is not None and src.font.highlight_color==WD_COLOR_INDEX.YELLOW)
            if segs and segs[-1]["src"] is src and segs[-1]["hl"]==h:
                segs[-1]["text"]+=ch
            else:
                segs.append({"text":ch,"src":src,"hl":h})
        return segs
    src_at=chars[idx][1] if idx<len(chars) else (p.runs[0] if p.runs else None)
    segs=group(chars[:idx])+[{"text":new,"src":src_at,"hl":True}]+group(chars[end:])
    rebuild(p,segs)
    return True

FIG={8:1,1:2,2:3,3:4,4:5,5:6,6:7,7:8}
TAB={10:1,11:2,1:3,2:4,3:5,4:6,5:7,6:8,7:9,8:10,9:11}
rx=re.compile(r'\b(Figure|Table) (\d+)\b')
def renumber(p):
    """split runs at Figure/Table N tokens; highlight tokens whose number changed."""
    segs=runs_to_segs(p); out=[]
    for s in segs:
        t=s["text"]; last=0
        for m in rx.finditer(t):
            kind=m.group(1); n=int(m.group(2))
            mp=FIG if kind=="Figure" else TAB
            newn=mp.get(n,n)
            if last<m.start(): out.append({"text":t[last:m.start()],"src":s["src"],"hl":False})
            out.append({"text":f"{kind} {newn}","src":s["src"],"hl":(newn!=n)})
            last=m.end()
        out.append({"text":t[last:],"src":s["src"],"hl":False})
    if any(seg["hl"] for seg in out):
        rebuild(p,out); return True
    return False

# ---------- 1. plural "Tables 2 and 4" special case (before regex renumber) ----------
for p in d.paragraphs:
    if "Tables 2 and 4" in p.text:
        edit_exact(p,"Tables 2 and 4","Tables 4 and 6")

# ---------- 2. renumber all paragraphs ----------
for p in d.paragraphs:
    renumber(p)

# ---------- 3. citation insertions ----------
EDITS=[
 ("(Fankhauser et al., 2022; Höhne et al., 2021; Rogelj et al., 2016; van Soest et al., 2021)",
  "(Fankhauser et al., 2022; Höhne et al., 2021; Meinshausen et al., 2022; Riahi et al., 2021; Rogelj et al., 2016; Sognnæs et al., 2021; van Soest et al., 2021)"),
 ("only a minority meet basic robustness criteria (Fankhauser et al., 2022; Hale et al., 2022; Rogelj et al., 2021)",
  "only a minority meet basic robustness criteria (Fankhauser et al., 2022; Hale et al., 2022; Rogelj et al., 2021, 2023)"),
 ("carbon pricing has real but moderate effects (Best et al., 2020; Green, 2021)",
  "carbon pricing has real but moderate effects (Bayer & Aklin, 2020; Best et al., 2020; Colmer et al., 2025; Green, 2021; Leroutier, 2022)"),
 ("(Callaway & Sant’Anna, 2021; de Chaisemartin & D’Haultfœuille, 2020; Goodman-Bacon, 2021; Sun & Abraham, 2021)",
  "(Borusyak et al., 2024; Callaway & Sant’Anna, 2021; de Chaisemartin & D’Haultfœuille, 2020, 2023; Goodman-Bacon, 2021; Roth et al., 2023; Sun & Abraham, 2021)"),
 ("proximate determinants: income level",
  "proximate determinants (Lamb et al., 2021): income level"),
 ("(de Chaisemartin & D’Haultfœuille, 2020; Goodman-Bacon, 2021; Sun & Abraham, 2021)",
  "(Borusyak et al., 2024; de Chaisemartin & D’Haultfœuille, 2020, 2023; Goodman-Bacon, 2021; Roth et al., 2023; Sun & Abraham, 2021)"),
 ("We emphasise the limit of this evidence:",
  "We emphasise the limit of this evidence (Roth, 2022):"),
 ("national climate laws (Eskander & Fankhauser, 2020) and carbon pricing (Best et al., 2020; Green, 2021).",
  "national climate laws (Eskander & Fankhauser, 2020) and carbon pricing (Best et al., 2020; Colmer et al., 2025; Green, 2021)."),
 ("not yet at the required speed (Fankhauser et al., 2022).",
  "not yet at the required speed (Fankhauser et al., 2022; Jewell & Cherp, 2020)."),
 ("coalition formation in the electricity sector (Meckling et al., 2015)",
  "coalition formation in the electricity sector (Cherp et al., 2021; Meckling et al., 2015)"),
 ("that integrated assessments assume (Markandya et al., 2018; Vandyck et al., 2018)",
  "that integrated assessments assume (Markandya et al., 2018; Rauner et al., 2020; Sampedro et al., 2020; Vandyck et al., 2018)"),
 ("The findings describe conditional rather than automatic SDG synergies.",
  "The findings describe conditional rather than automatic SDG synergies (Warchold et al., 2021)."),
 ("an asymmetry at the centre of the climate-finance negotiations.",
  "an asymmetry at the centre of the climate-finance negotiations (Roberts et al., 2021)."),
]
applied=[]
for old,new in EDITS:
    done=False
    for p in d.paragraphs:
        if old in p.text:
            done=edit_exact(p,old,new); break
    applied.append((old[:45],done))

# ---------- 4. merge references, re-sort, highlight new ----------
def sortkey(apa):
    lead=apa.split(",")[0] if "," in apa[:60] else apa.split(" (")[0]
    s=unicodedata.normalize("NFKD",lead).encode("ascii","ignore").decode().lower()
    s=s.replace("æ","ae")
    return s
paras=d.paragraphs
ri=next(i for i,p in enumerate(paras) if p.style and 'Heading 1' in (p.style.name or '') and p.text.strip()=="References")
old_ref_paras=[paras[i] for i in range(ri+1,len(paras)) if paras[i].text.strip()]
existing=[p.text.strip() for p in old_ref_paras]
new_apas=[newrefs[k]["apa"] for k in newrefs]
combined=[(sortkey(a),a,False) for a in existing]+[(sortkey(a),a,True) for a in new_apas]
combined.sort(key=lambda x:x[0])
# delete old ref paragraphs
for p in old_ref_paras:
    p._p.getparent().remove(p._p)
# insert sorted after References H1
anchor=paras[ri]._p
for _,apa,is_new in combined:
    np=d.add_paragraph()
    np.paragraph_format.left_indent=docx.shared.Pt(18)
    np.paragraph_format.first_line_indent=docx.shared.Pt(-18)
    np.paragraph_format.space_after=docx.shared.Pt(6)
    r=np.add_run(apa)
    if is_new: r.font.highlight_color=WD_COLOR_INDEX.YELLOW
    anchor.addnext(np._p); anchor=np._p

d.save(HL)
print("citation edits applied:")
for o,ok in applied: print(f"   {'OK ' if ok else 'MISS'} {o}")
print(f"references now: {len(combined)} (was {len(existing)}, +{len(new_apas)})")
print("saved", HL)

# ---------- 5. clean copy (strip highlights) ----------
d2=docx.Document(HL)
n=0
for p in d2.paragraphs:
    for r in p.runs:
        if r.font.highlight_color is not None:
            r.font.highlight_color=None; n+=1
for t in d2.tables:
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    if r.font.highlight_color is not None:
                        r.font.highlight_color=None; n+=1
d2.save(CLEAN)
print(f"clean copy: cleared {n} highlights -> {CLEAN}")
