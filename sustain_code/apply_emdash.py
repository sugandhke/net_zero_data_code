"""apply_emdash.py — remove em dashes (U+2014) from the SD main-text copies.
Prose: short same-sentence asides '— X —' -> '(X)'; all other em dashes -> comma.
Tables: standalone placeholder '—' -> 'n/a'. En dashes (ranges) are untouched.
Runs are edited in place so subscripts/formatting/highlights survive.
"""
import re, docx

EM="—"
def transform(t):
    if EM not in t: return t
    # paired short aside (no sentence break, no nested em dash) -> parentheses
    prev=None
    while prev!=t:
        prev=t
        t=re.sub(r" — ([^—.;:]{1,120}?) — ", r" (\1) ", t, count=1)
    t=t.replace(" "+EM+" ", ", ")   # remaining spaced em dash -> comma
    t=t.replace(EM, ", ")            # any leftover
    t=re.sub(r",\s*,", ", ", t)
    t=re.sub(r"\s+,", ",", t)
    return t

for path in ["sustainable_submission/1_Main_Text_revised_highlighted.docx",
             "sustainable_submission/1_Main_Text_revised_clean.docx"]:
    d=docx.Document(path)
    for p in d.paragraphs:
        for r in p.runs:
            if EM in r.text: r.text=transform(r.text)
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        if r.text.strip()==EM: r.text="n/a"
                        elif EM in r.text: r.text=transform(r.text)
    d.save(path)
    # verify
    d2=docx.Document(path)
    body_em=sum(pp.text.count(EM) for pp in d2.paragraphs)
    tbl_em=sum(c.text.count(EM) for t in d2.tables for row in t.rows for c in row.cells)
    full="\n".join(pp.text for pp in d2.paragraphs)
    op=full.count("(") ; cp=full.count(")")
    print(f"{path.split('/')[-1]}: em-left(body/tbl)={body_em}/{tbl_em} parens open/close={op}/{cp}")
