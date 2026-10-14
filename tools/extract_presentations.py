#!/usr/bin/env python3
"""Extract meeting presentations/minutes from captured meeting pages
(materials/systems/cabin, all meetID variants) into site/data/presentations.json."""
import re, json, html, pathlib, collections

RAW = pathlib.Path(r"G:/Shared drives/Software & Apps/FAA Fire Safety Site/FAA_Fire_Safety_Archive\raw_html")
OUT = pathlib.Path(__file__).resolve().parent.parent / "site" / "data"

TAG = re.compile(r"<[^>]+>")
def cleantext(s):
    return " ".join(html.unescape(TAG.sub(" ", s)).split())

GROUPS = {
    "materials": "Materials Working Group",
    "systems": "Systems Working Group",
    "cabin": "Cabin Safety",
}

ROW_RE = re.compile(r"<tr>\s*<td>(\d{1,2}/\d{1,2}/\d{4})</td>(.*?)</tr>", re.S)
LI_RE = re.compile(r"<li>(.*?)</li>", re.S)
FILE_RE = re.compile(r'<a href="(/(?:pdf|ppt|zip|video|xls|doc)[^"]+)"', re.I)

records = {}
pages = (list(RAW.glob("materials.asp*.html")) + list(RAW.glob("systems.asp*.html"))
         + list(RAW.glob("cabin*.html")) + list(RAW.glob("Cabin*.html")))
for page in pages:
    group = next((g for k, g in GROUPS.items() if page.name.lower().startswith(k)), "Other")
    text = page.read_text(encoding="utf-8", errors="replace")
    for m in ROW_RE.finditer(text):
        date, body = m.group(1), m.group(2)
        mm, dd, yyyy = date.split("/")
        iso = f"{yyyy}-{int(mm):02d}-{int(dd):02d}"
        for li in LI_RE.finditer(body):
            item = li.group(1)
            files = FILE_RE.findall(item)
            if not files:
                continue
            title = cleantext(item.split("<br")[0])
            if not title:
                continue
            f0 = files[0]
            # presenter is encoded in the filename: Marker-1023-Shorttakes.pdf
            base = f0.rsplit("/", 1)[-1]
            pm = re.match(r"([A-Za-z&' ]{3,25})-\d", base)
            presenter = pm.group(1) if pm else ""
            key = f0.lower()
            if key not in records:
                records[key] = {
                    "title": title[:220], "date": iso, "year": int(yyyy),
                    "group": group, "presenter": presenter,
                    "files": files[:4],
                }

OUT.mkdir(parents=True, exist_ok=True)
data = sorted(records.values(), key=lambda r: r["date"], reverse=True)
(OUT / "presentations.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
by_group = collections.Counter(r["group"] for r in data)
by_year = collections.Counter(r["year"] for r in data)
print("presentations:", len(data), dict(by_group))
print("year span:", min(by_year), "-", max(by_year))
