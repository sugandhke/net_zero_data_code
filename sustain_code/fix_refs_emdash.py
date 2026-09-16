"""fix_refs_emdash.py — XML-level pass reaching ALL paragraphs (incl. content
controls python-docx misses): (1) correct stale figure/table references left
by the earlier renumbering; (2) remove every em dash. Operates on both copies;
stale-ref corrections are highlighted in the *_highlighted copy only."""
import re, copy, docx
from docx.oxml.ns import qn
from docx.enum.text import WD_COLOR_INDEX

EM="—"
def em_transform(t):
    if EM not in t: return t
    prev=None
    while prev!=t:
        prev=t
        t=re.sub(r" — ([^—.;:]{1,120}?) — ", r" (\1) ", t, count=1)
    t=t.replace(" "+EM+" ", ", ").replace(EM, ", ")
    t=re.sub(r",\s*,", ", ", t); t=re.sub(r"\s+,", ",", t)
    return t

# stale (old -> new) reference corrections; each unique within one run
FIXES=[
 ("pandemic dip and rebound (Figure 1). Figure 2 disciplines",
  "pandemic dip and rebound (Figure 2). Figure 3 disciplines"),
 ("act first on the electricity system (Figure 3)",
  "act first on the electricity system (Figure 4)"),
 ("(Figure 6; Figure 7c)", "(Figure 6; Figure 8c)"),
 ("By income (Table 3)", "By income (Table 5)"),
 ("By institutional quality (Table 4)", "By institutional quality (Table 6)"),
 ("P < 0.05; Figure 7b)", "P < 0.05; Figure 8b)"),
 ("significant reduction of 3.9 per cent (P < 0.05; Table 6)",
  "significant reduction of 3.9 per cent (P < 0.05; Table 8)"),
 ("adoption determinants (Table 5)", "adoption determinants (Table 7)"),
 ("Table 6 collects the robustness suite", "Table 8 collects the robustness suite"),
 ("randomisation P < 0.005; Figure 6)", "randomisation P < 0.005; Figure 7)"),
 ("insignificant estimate (Figure 7a)", "insignificant estimate (Figure 8a)"),
 ("(Figure 3a and Table 10)", "(Figure 4a and Table 10)"),
 ("distinguishable from zero (Table 9)", "distinguishable from zero (Table 11)"),
]

def set_run_text(r_el, s):
    for c in list(r_el):
        if c.tag==qn('w:t'): r_el.remove(c)
    te=r_el.makeelement(qn('w:t'),{qn('xml:space'):'preserve'}); te.text=s
    r_el.append(te); return r_el

def mkrun(template, s, hl):
    nr=copy.deepcopy(template); set_run_text(nr,s)
    if hl:
        rp=nr.find(qn('w:rPr'))
        if rp is None:
            rp=nr.makeelement(qn('w:rPr'),{}); nr.insert(0,rp)
        for h in rp.findall(qn('w:highlight')): rp.remove(h)
        rp.append(rp.makeelement(qn('w:highlight'),{qn('w:val'):'yellow'}))
    return nr

def para_replace(par_el, old, new, highlight):
    """replace `old` with `new` across runs of one paragraph, preserving
    formatting of the unaffected prefix/suffix; highlight the new text."""
    runs=par_el.findall(qn('w:r'))
    chars=[]  # (char, r_el)
    for r_el in runs:
        te=r_el.find(qn('w:t'))
        for ch in (te.text or "" if te is not None else ""): chars.append((ch,r_el))
    full="".join(c for c,_ in chars)
    i=full.find(old)
    if i<0: return False
    end=i+len(old)
    rs=chars[i][1]; re_=chars[end-1][1]
    # text kept in the boundary runs
    def run_text(r_el):
        te=r_el.find(qn('w:t')); return te.text or "" if te is not None else ""
    # offset of match start within rs
    # compute by counting chars up to i that belong to rs
    start_off=0
    for j in range(i):
        if chars[j][1] is rs: start_off+=1
    pre=run_text(rs)[:start_off]
    end_off=0
    for j in range(end,len(chars)):
        if chars[j][1] is re_: break
    # suffix = chars after match that are in re_
    suf=""
    cnt_in_re=sum(1 for c,r in chars if r is re_)
    used_in_re=sum(1 for j in range(end) if chars[j][1] is re_)
    suf=run_text(re_)[used_in_re:]
    # remove runs strictly between rs and re_ (and the span runs, we rebuild)
    order=list(par_el)
    ir=order.index(rs); jr=order.index(re_)
    between=[order[k] for k in range(ir,jr+1)]  # rs..re_
    insert_at=ir
    # build replacement runs
    newruns=[]
    if pre: newruns.append(mkrun(rs,pre,False))
    newruns.append(mkrun(rs,new,highlight))
    if suf: newruns.append(mkrun(re_,suf,False))
    for b in between: par_el.remove(b)
    for k,nr in enumerate(newruns): par_el.insert(insert_at+k,nr)
    return True

for path,do_hl in [("sustainable_submission/1_Main_Text_revised_clean.docx",False),
                   ("sustainable_submission/1_Main_Text_revised_highlighted.docx",True)]:
    d=docx.Document(path)
    body=d.element.body
    # 1) em dashes across all <w:t>
    for te in body.iter(qn('w:t')):
        if te.text and EM in te.text: te.text=em_transform(te.text)
    # 2) stale-ref fixes across all paragraphs, via text-node redistribution
    #    (reaches nested runs; preserves node/formatting structure)
    def replace_wt(pel, old, new):
        nodes=list(pel.iter(qn('w:t')))
        texts=[n.text or "" for n in nodes]
        full="".join(texts); i=full.find(old)
        if i<0: return False
        end=i+len(old); pos=0
        for n,t in zip(nodes,texts):
            s,e=pos,pos+len(t); pos=e
            if e<=i or s>=end:      # node fully outside match
                continue
            # node overlaps [i,end)
            keep_pre=t[:max(0,i-s)]
            keep_post=t[max(0,end-s):] if e>end else ""
            ins=new if (s<=i<e) else ""    # insert new where match starts
            n.text=keep_pre+ins+keep_post
        return True
    results={o:0 for o,_ in FIXES}
    for old,new in FIXES:
        for pel in body.iter(qn('w:p')):
            txt="".join((te.text or "") for te in pel.iter(qn('w:t')))
            if old in txt:
                if replace_wt(pel,old,new): results[old]+=1
                break
    d.save(path)
    em_left=sum((te.text or "").count(EM) for te in docx.Document(path).element.body.iter(qn('w:t')))
    miss=[o[:40] for o,c in results.items() if c==0]
    print(f"{path.split('/')[-1]}: em-left={em_left} | fixes applied={sum(results.values())}/{len(FIXES)}"
          + (f" | MISSED: {miss}" if miss else " | all applied"))
