#!/usr/bin/env python3
"""Extract report metadata from captured listresults.asp pages (all generations)
into site/data/reports.json. Dedupes across overlapping captures by PDF path/title."""
import re, json, glob, html, pathlib, collections

RAW = pathlib.Path(r"G:/Shared drives/Software & Apps/FAA Fire Safety Site/FAA_Fire_Safety_Archive\raw_html\reports")
OUT = pathlib.Path(__file__).resolve().parent.parent / "site" / "data"

TAG = re.compile(r"<[^>]+>")
def clean(s):
    return html.unescape(TAG.sub(" ", s)).replace("\ufffd", "'").split()

def cleantext(s, limit=None):
    t = " ".join(clean(s))
    return t[:limit] if limit else t

HREF = re.compile(r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.S)

def parse_old(text):
    """<table class="report"> generations (2000s-2010s): th or td.header label cells"""
    out = []
    for tbl in re.findall(r'<table class="report"[^>]*>(.*?)</table>', text, re.S):
        rec = {}
        for label, val in re.findall(
                r'<(?:th|td class="header")>([^<:]+):</t[hd]>\s*<td[^>]*>(.*?)</td>', tbl, re.S):
            key = label.strip().lower()
            if key == "title":
                m = HREF.search(val)
                if m:
                    rec["pdf"] = m.group(1)
                    rec["title"] = cleantext(m.group(2))
                else:
                    rec["title"] = cleantext(val)
            else:
                rec[key] = cleantext(val, 1200 if key == "abstract" else None)
        if rec.get("title"):
            out.append(rec)
    return out

def parse_new(text):
    """bootstrap row generation (2020s)"""
    out = []
    chunks = re.split(r'(?=<div class="col-sm-1 report-headings"><strong>Title:)', text)
    for ch in chunks[1:]:
        rec = {}
        for label, val in re.findall(
                r'report-headings"><strong>([^<:]+):</strong></div>\s*<div class="col-sm-11[^"]*">(.*?)</div>',
                ch, re.S):
            key = label.strip().lower()
            if key == "title":
                m = HREF.search(val)
                if m:
                    rec["pdf"] = m.group(1)
                    rec["title"] = cleantext(m.group(2))
                else:
                    rec["title"] = cleantext(val)
            else:
                rec[key] = cleantext(val, 1200 if key == "abstract" else None)
        if rec.get("title"):
            out.append(rec)
    return out

HIST = pathlib.Path(r"G:/Shared drives/Software & Apps/FAA Fire Safety Site/FAA_Fire_Safety_Archive\raw_html_history\listresults")

records = {}
label_stats = collections.Counter()
HIST2 = pathlib.Path("G:/Shared drives/Software & Apps/FAA Fire Safety Site/FAA_Fire_Safety_Archive/raw_html_history/searchresults")
files = (sorted(RAW.glob("listresults.asp__Q_*.html")) + sorted(RAW.glob("searchresults.asp__Q_*.html"))
         + sorted(HIST.glob("*.html")) + sorted(HIST2.glob("*.html")))
for f in files:
    text = f.read_text(encoding="utf-8", errors="replace")
    recs = parse_new(text) if "report-headings" in text else parse_old(text)
    for r in recs:
        key = (r.get("pdf") or r["title"]).lower().strip()
        # prefer the record with more fields (newer captures carry more metadata)
        if key not in records or len(r) > len(records[key]):
            records[key] = r
        for k in r: label_stats[k] += 1

OUT.mkdir(parents=True, exist_ok=True)
data = sorted(records.values(), key=lambda r: r.get("title", ""))
(OUT / "reports.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
print("files parsed:", len(files))
print("unique reports:", len(data))
print("fields seen:", dict(label_stats))
with_pdf = sum(1 for r in data if r.get("pdf"))
print("with pdf link:", with_pdf, " without:", len(data) - with_pdf)
