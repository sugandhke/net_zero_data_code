"""
fix_citation_superscripts.py — repair reference numbers that lost their
superscript formatting when their citation numbers were corrected.

Replacing text inside an existing run inherits that run's formatting, so a
citation number written into a body run renders as plain text next to properly
superscripted neighbours. This splits the run and re-marks the number.
"""
import copy
import docx
from docx.text.run import Run

# (anchor text immediately before the number, the number itself)
CITES = [("near-null", "18"),
         ("Fankhauser et al.", "4"),
         ("Rogelj et al.", "7"),
         ("energy systems", "17"),
         ("integrated assessments assume", "27,28")]

def fix_par(par, anchor, num):
    target = anchor + num
    for r in list(par.runs):
        if target not in r.text:
            continue
        if r.font.superscript:            # already fine
            return "ok"
        pre, post = r.text.split(target, 1)
        r.text = pre + anchor             # keep anchor in the body run
        # superscript run for the number
        sup_el = copy.deepcopy(r._r)
        r._r.addnext(sup_el)
        sup = Run(sup_el, par)
        sup.text = num
        sup.font.superscript = True
        sup.font.highlight_color = None
        if post:                          # remainder in body formatting
            post_el = copy.deepcopy(r._r)
            sup_el.addnext(post_el)
            tail = Run(post_el, par)
            tail.text = post
            tail.font.superscript = False
            tail.font.highlight_color = None
        return "fixed"
    return None

for path in ["NetZero_manuscript_submission.docx",
             "revised_manuscript.docx",
             "raghu_sir_manuscript.docx"]:
    d = docx.Document(path)
    results = []
    for anchor, num in CITES:
        done = None
        for p in d.paragraphs:
            if anchor + num in p.text:
                done = fix_par(p, anchor, num)
                if done:
                    break
        results.append(f"{anchor+num}:{done or 'NOT-FOUND'}")
    d.save(path)
    print(f"{path}\n   " + "  ".join(results))
