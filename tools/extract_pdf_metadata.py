#!/usr/bin/env python3
"""Extract title/author metadata from unindexed top-level report PDFs
(PDF document properties, falling back to first-page text heuristics)
into site/data/reports_pdfmeta.json for merging into the index."""
import json, pathlib, re, sys
from pypdf import PdfReader

REPO = pathlib.Path(__file__).resolve().parent.parent
PDFDIR = pathlib.Path(r"G:\My Drive\FAA_Fire_Safety_Archive\files\pdf")
OUT = REPO / "site" / "data" / "reports_pdfmeta.json"

data = json.load(open(REPO / "site" / "data" / "reports.json", encoding="utf-8"))
indexed = {r["pdf"].lower().rsplit("/", 1)[-1] for r in data}

def clean(s):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s

def plausible_title(s):
    if not s: return False
    if len(s) < 8 or len(s) > 250: return False
    low = s.lower()
    bad = ("microsoft word", ".doc", ".qxd", ".indd", ".pdf", "untitled",
           "slide 1", "powerpoint", "print", "cover", "layout", "template")
    return not any(b in low for b in bad)

def first_page_title(reader):
    try:
        text = reader.pages[0].extract_text() or ""
    except Exception:
        return ""
    # first run of substantial lines, skipping boilerplate
    lines = [clean(l) for l in text.splitlines()]
    skip = re.compile(r"^(dot/faa|faa|federal aviation|office of|final report|technical note|"
                      r"u\.?s\.? department|washington|atlantic city|note|tc-?\d|ar-?\d|"
                      r"this document|available|january|february|march|april|may|june|july|"
                      r"august|september|october|november|december|\d|$)", re.I)
    picked = []
    for l in lines[:40]:
        if not l or skip.match(l):
            if picked: break
            continue
        picked.append(l)
        if sum(len(p) for p in picked) > 120: break
    return clean(" ".join(picked))[:220]

results = []
errors = 0
for p in sorted(PDFDIR.iterdir()):
    if not (p.is_file() and p.suffix.lower() == ".pdf"): continue
    if p.name.lower() in indexed: continue
    rec = {"pdf": "/pdf/" + p.name}
    try:
        reader = PdfReader(str(p))
        meta = reader.metadata or {}
        t = clean(meta.get("/Title", ""))
        a = clean(meta.get("/Author", ""))
        if not plausible_title(t):
            t = first_page_title(reader)
        if plausible_title(t):
            rec["title"] = t
        if a and len(a) > 3 and "microsoft" not in a.lower():
            rec["author"] = a[:120]
    except Exception:
        errors += 1
    if "title" not in rec:
        # derive something readable from the filename
        stem = re.sub(r"[-_]+", " ", p.stem)
        rec["title"] = stem.strip()[:120]
        rec["weak"] = True
    results.append(rec)

OUT.write_text(json.dumps(results, indent=1), encoding="utf-8")
good = sum(1 for r in results if not r.get("weak"))
print(f"unindexed pdfs processed: {len(results)}  real titles: {good}  filename-only: {len(results)-good}  read errors: {errors}")
