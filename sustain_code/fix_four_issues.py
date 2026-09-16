"""fix_four_issues.py — fix the four flagged issues in both SD copies:
 A. normalise stray fonts (Caudex/Gungsuh/Cardo) -> Times New Roman
 B. Figure 3 caption: move the title runs before the description (fixes glue/order)
 C. Table 8 (robustness): remove the prose 'Reading' interpretation column
 D. heading numbering: 1 Introduction / 2 Materials and Methods / 3 Results,
    and '5. Conclusion' -> '5 Conclusion' (consistent with '4 Discussion')
Operates at XML level so it reaches content-control (nested) runs.
"""
import docx
from docx.oxml.ns import qn

STRAY={"Caudex","Gungsuh","Cardo"}
TNR="Times New Roman"
HEAD={"Introduction":"1 Introduction",
      "Materials and Methods":"2 Materials and Methods",
      "Results":"3 Results",
      "5. Conclusion":"5 Conclusion"}

def norm_fonts(body):
    n=0
    for rf in body.iter(qn('w:rFonts')):
        asc=rf.get(qn('w:ascii'))
        if asc in STRAY:
            for a in ('w:ascii','w:hAnsi','w:cs','w:eastAsia'):
                if rf.get(qn(a)) is not None: rf.set(qn(a),TNR)
            n+=1
    return n

def fix_caption(body):
    for pel in body.iter(qn('w:p')):
        txt="".join(t.text or "" for t in pel.iter(qn('w:t')))
        if "Figure 3. Event-study estimates" in txt and "e = +3" in txt:
            children=list(pel)
            # title runs are the direct <w:r> children after the <w:sdt> description
            sdt=pel.find(qn('w:sdt'))
            if sdt is None: return False
            title_runs=[c for c in children if c.tag==qn('w:r')]
            if not title_runs: return False
            pPr=pel.find(qn('w:pPr'))
            anchor=pPr if pPr is not None else None
            # move title runs to front (after pPr, before sdt)
            for r in title_runs: pel.remove(r)
            insert_idx=(list(pel).index(pPr)+1) if pPr is not None else 0
            for k,r in enumerate(title_runs): pel.insert(insert_idx+k,r)
            return True
    return False

def remove_reading_col(body):
    for tbl in body.iter(qn('w:tbl')):
        rows=tbl.findall(qn('w:tr'))
        if not rows: continue
        hdr="".join(t.text or "" for t in rows[0].iter(qn('w:t')))
        if "Specification" in hdr and "Reading" in hdr and "GHG effect" in hdr:
            # remove 3rd gridCol
            grid=tbl.find(qn('w:tblGrid'))
            if grid is not None:
                cols=grid.findall(qn('w:gridCol'))
                if len(cols)>=3: grid.remove(cols[2])
            # remove 3rd cell in each row
            for tr in rows:
                tcs=tr.findall(qn('w:tc'))
                if len(tcs)>=3: tr.remove(tcs[2])
            return True
    return False

def fix_headings(body):
    done=0
    for pel in body.iter(qn('w:p')):
        txt="".join(t.text or "" for t in pel.iter(qn('w:t'))).strip()
        if txt in HEAD:
            new=HEAD[txt]
            # redistribute into text nodes (reach nested runs), preserve fmt
            nodes=list(pel.iter(qn('w:t')))
            if not nodes: continue
            nodes[0].text=new
            for nd in nodes[1:]: nd.text=""
            done+=1
    return done

for path in ["sustainable_submission/1_Main_Text_revised_clean.docx",
             "sustainable_submission/1_Main_Text_revised_highlighted.docx"]:
    d=docx.Document(path); body=d.element.body
    a=norm_fonts(body); b=fix_caption(body); c=remove_reading_col(body); e=fix_headings(body)
    d.save(path)
    print(f"{path.split('/')[-1]}: fonts_normalised={a} caption_fixed={b} reading_col_removed={c} headings_fixed={e}")
