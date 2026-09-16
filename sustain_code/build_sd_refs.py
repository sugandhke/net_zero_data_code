"""
build_sd_refs.py — build APA-6th references (author-date) and the in-text
citation map for the Sustainable Development submission, from verified Crossref
metadata (authors, journal, volume, pages, DOI) plus manuscript titles.
Two Crossref mismatches (#21 GCB, #32 Copeland&Taylor) overridden manually.
Non-article refs (17,20,22,23,24) hand-formatted.
Writes sustainable_submission/_refs.json and prints for verification.
"""
import json, re

CR = json.load(open("sustainable_submission/_crossref.json"))

# ---- manual overrides for the two Crossref mismatches ----
CR["21"] = {"DOI":"10.5194/essd-15-5301-2023",
            "authors":None,  # keep manuscript 'et al.' -> Friedlingstein, P., et al. handled below
            "title":"Global Carbon Budget 2023","container":"Earth System Science Data",
            "volume":"15","page":"5301-5369","year":2023}
CR["32"] = {"DOI":"10.1257/002205104773558047",
            "authors":[{"family":"Copeland","given":"Brian R."},{"family":"Taylor","given":"M. Scott"}],
            "title":"Trade, growth, and the environment","container":"Journal of Economic Literature",
            "volume":"42","page":"7-71","year":2004}

# manuscript titles (sentence case, correct proper nouns) keyed by ref number
TITLE = {
 1:"The Paris Agreement and the new logic of international climate politics",
 2:"Paris Agreement climate proposals need a boost to keep warming well below 2°C",
 3:"Wave of net zero emission targets opens window to meeting the Paris Agreement",
 4:"The meaning of net zero and how to get it right",
 5:"Net-zero emission targets for major emitting countries consistent with the Paris Agreement",
 6:"Assessing the rapidly-emerging landscape of net zero targets",
 7:"Net-zero emissions targets are vague: Three ways to fix",
 8:"Determining the credibility of commitments in international climate policy",
 9:"Reduction in greenhouse gas emissions from national climate legislation",
 10:"Carbon pricing efficacy: Cross-country evidence",
 11:"Does carbon pricing reduce emissions? A review of ex-post analyses",
 12:"Climate policies that achieved major emission reductions: Global evidence from two decades",
 13:"Difference-in-differences with variation in treatment timing",
 14:"Difference-in-differences with multiple time periods",
 15:"Estimating dynamic treatment effects in event studies with heterogeneous treatment effects",
 16:"Two-way fixed effects estimators with heterogeneous treatment effects",
 18:"How much should we trust differences-in-differences estimates?",
 19:"Temporary reduction in daily global CO₂ emissions during the COVID-19 forced confinement",
 21:"Global Carbon Budget 2023",
 25:"National institutions and global public goods: Are democracies more cooperative in climate change policy?",
 26:"The limits of democracy in tackling climate change",
 27:"Health co-benefits from air pollution and mitigation costs of the Paris Agreement: A modelling study",
 28:"Air quality co-benefits for human health and agriculture counterbalance costs to meet Paris Agreement pledges",
 29:"Winning coalitions for climate policy",
 30:"Economic growth and the environment",
 31:"Is free trade good for the environment?",
 32:"Trade, growth, and the environment",
 33:"A more credible approach to parallel trends",
}

# in-text short form + alpha sort key (first-author family, ascii)
INTEXT = {
 1:("Falkner, 2016","falkner"), 2:("Rogelj et al., 2016","rogelj 2016"),
 3:("Höhne et al., 2021","hohne"), 4:("Fankhauser et al., 2022","fankhauser"),
 5:("van Soest et al., 2021","van soest"), 6:("Hale et al., 2022","hale"),
 7:("Rogelj et al., 2021","rogelj 2021"), 8:("Victor et al., 2022","victor"),
 9:("Eskander & Fankhauser, 2020","eskander"), 10:("Best et al., 2020","best"),
 11:("Green, 2021","green"), 12:("Stechemesser et al., 2024","stechemesser"),
 13:("Goodman-Bacon, 2021","goodman-bacon"), 14:("Callaway & Sant’Anna, 2021","callaway"),
 15:("Sun & Abraham, 2021","sun"), 16:("de Chaisemartin & D’Haultfœuille, 2020","de chaisemartin"),
 17:("UNFCCC, 2023","unfccc"), 18:("Bertrand et al., 2004","bertrand"),
 19:("Le Quéré et al., 2020","le quere"), 20:("Van Coppenolle et al., 2022","van coppenolle"),
 21:("Friedlingstein et al., 2023","friedlingstein"), 22:("Ritchie & Roser, 2023","ritchie"),
 23:("Coppedge et al., 2025","coppedge"), 24:("World Bank, 2024","world bank"),
 25:("Bättig & Bernauer, 2009","battig"), 26:("Povitkina, 2018","povitkina"),
 27:("Markandya et al., 2018","markandya"), 28:("Vandyck et al., 2018","vandyck"),
 29:("Meckling et al., 2015","meckling"), 30:("Grossman & Krueger, 1995","grossman"),
 31:("Antweiler et al., 2001","antweiler"), 32:("Copeland & Taylor, 2004","copeland"),
 33:("Rambachan & Roth, 2023","rambachan"),
}

def initials(given):
    if not given: return ""
    out=[]
    for tok in given.replace(".", " ").split():
        parts=tok.split("-")
        out.append("-".join(p[0].upper()+"." for p in parts if p))
    return " ".join(out)

def fixfam(fam):
    return fam.capitalize() if (fam and fam.isupper() and len(fam) > 1) else fam

def apa_authors(authors):
    names=[f"{fixfam(a['family'])}, {initials(a.get('given',''))}".strip().rstrip(",")
           for a in authors]
    if len(names)==1: return names[0]
    if len(names)<=7:
        return ", ".join(names[:-1]) + ", & " + names[-1]
    return ", ".join(names[:6]) + ", … " + names[-1]   # APA6: first 6 … last

def endash(p):
    return p.replace("-", "–") if p else p

# hand-formatted non-article references (APA)
HAND = {
 17:"United Nations Framework Convention on Climate Change. (2023). Outcome of the first global stocktake (Decision 1/CMA.5). UNFCCC.",
 20:"Van Coppenolle, H., Van de Graaf, T., & Blondeel, M. (2022). National net zero (or adjacent) targets [Data set]. Zenodo. https://zenodo.org/records/19296074",
 22:"Ritchie, H., & Roser, M. (2023). CO₂ and greenhouse gas emissions. Our World in Data. https://ourworldindata.org/co2-and-greenhouse-gas-emissions",
 23:"Coppedge, M., Gerring, J., Knutsen, C. H., Lindberg, S. I., Teorell, J., … Ziblatt, D. (2025). V-Dem dataset v15 [Data set]. Varieties of Democracy (V-Dem) Project. https://www.v-dem.net   [AUTHORS: replace with V-Dem’s official full citation string and DOI before submission]",
 24:"World Bank. (2024). World Development Indicators [Data set]. World Bank. https://databank.worldbank.org/source/world-development-indicators",
}

records={}
for num in range(1,34):
    intext, sortkey = INTEXT[num]
    if num in HAND:
        apa = HAND[num]
    else:
        c = CR[str(num)]
        # authors: crossref, except #21 keep manuscript 'et al.'
        if num==21:
            au = "Friedlingstein, P., Jones, M. W., O’Sullivan, M., Andrew, R. M., Bakker, D. C. E., Hauck, J., … Zheng, B."
        else:
            au = apa_authors(c["authors"])
        ARTNO = {5:"2140", 28:"4939", 11:"043004"}   # article-number journals
        vol = c.get("volume") or ""
        pg = endash(c.get("page") or "")
        jr = c["container"]
        yr = {2:2016, 7:2021}.get(num, c.get("year"))
        doi = c.get("DOI")
        if num in ARTNO:
            pgpart = f", Article {ARTNO[num]}"
        else:
            pgpart = f", {pg}" if pg else ""
        volpart = f", {vol}" if vol else ""
        t = TITLE[num]
        tsep = "" if t[-1] in "?!" else "."     # no period after ? or !
        apa = f"{au} ({yr}). {t}{tsep} {jr}{volpart}{pgpart}."
        if doi: apa += f" https://doi.org/{doi}"
    records[num]={"intext":intext,"sortkey":sortkey,"apa":apa}

# alphabetical reference list
order = sorted(records, key=lambda n: records[n]["sortkey"])
reflist = [records[n]["apa"] for n in order]

json.dump({"records":records,"reflist":reflist,
           "intext":{str(n):records[n]["intext"] for n in records},
           "sortkey":{str(n):records[n]["sortkey"] for n in records}},
          open("sustainable_submission/_refs.json","w"),indent=1,ensure_ascii=False)

print("=== APA REFERENCE LIST (alphabetical, %d entries) ===\n" % len(reflist))
for r in reflist: print(r+"\n")
