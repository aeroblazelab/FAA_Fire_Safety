#!/usr/bin/env python3
"""Build the browsable report index: dedupe, infer year, assign topics,
emit site/reports/browse.html (table UI styled like the rest of the site)."""
import json, re, html, os, pathlib, collections
FILE_BASE = os.environ.get("FILE_BASE", "/files")

REPO = pathlib.Path(__file__).resolve().parent.parent
SITE = REPO / "site"
data = json.load(open(SITE / "data" / "reports.json", encoding="utf-8"))

# ---- dedupe by pdf basename (same report captured under path variants) ----
def tnorm(t): return re.sub(r"\W+", "", t.lower())[:40]
groups = collections.defaultdict(list)
for r in data:
    groups[r["pdf"].lower().rsplit("/", 1)[-1]].append(r)
merged = []
for base, rs in groups.items():
    rs.sort(key=len, reverse=True)
    kept = []
    for r in rs:
        match = next((k for k in kept if tnorm(k["title"]) == tnorm(r["title"])), None)
        if match:
            for k, v in r.items():
                match.setdefault(k, v)
        else:
            kept.append(dict(r))
    merged.extend(kept)

# ---- year inference ----
def year_from(r):
    for src in (r.get("report", ""), r["pdf"].rsplit("/", 1)[-1]):
        # patterns: AR-04/27, CT-94/74, 99/73, TC-12/53, TN03-52, tc24-24, 03-58, hilites97, TM78-431
        for m in re.finditer(r"(?<!\d)(\d{2})(?=[/\-._ ]|$)", src):
            yy = int(m.group(1))
            yr = 1900 + yy if yy >= 60 else 2000 + yy
            if 1960 <= yr <= 2026:
                return yr
        m = re.search(r"(19[6-9]\d|20[0-2]\d)", src)
        if m:
            return int(m.group(1))
    return None

# ---- topic rules (first two matches win; order = priority) ----
TOPICS = [
    ("Lithium Batteries", r"lithium|li-ion|battery|batteries|state of charge|thermal runaway"),
    ("Fuel Tank & Inerting", r"fuel tank|inert|ullage|OBIGGS|nitrogen[- ]enriched|flammability assessment"),
    ("Cargo Compartment", r"cargo"),
    ("Halon & Suppression Agents", r"halon|suppression agent|extinguishing agent|HFC|streaming agent|minimum performance standard"),
    ("Handheld Extinguishers", r"handheld|hand-held|portable (fire )?extinguisher"),
    ("Engine & Powerplant", r"nacelle|engine|powerplant|APU|turbine"),
    ("Seats & Cushions", r"seat|cushion"),
    ("Thermal Acoustic Insulation", r"thermal[/ -]?acoustic|insulation blanket|burnthrough|burn-through"),
    ("Materials & Test Methods", r"flammability test|test method|bunsen|radiant panel|OSU|heat release|cone calorimeter|microscale|micro-scale|fire test handbook|vertical flame"),
    ("Composites & Structures", r"composite|structural|fuselage material|geopolymer"),
    ("Electrical & Wiring", r"wiring|wire |arc fault|electrical"),
    ("Fire Detection", r"detection|detector|smoke alarm"),
    ("Smoke & Toxicity", r"toxic|smoke|combustion gas|off-gas"),
    ("Evacuation & Cabin Safety", r"evacuation|egress|slide|cabin safety|passenger|survivab"),
    ("Hidden & Inaccessible Areas", r"hidden area|inaccessible"),
    ("Polymers & Chemistry", r"polymer|flame retardant|resin|char|pyrolysis|molecular"),
]
def topics_for(r):
    blob = (r.get("title", "") + " " + r.get("abstract", "")).lower()
    hits = [name for name, pat in TOPICS if re.search(pat, blob)]
    return hits[:2] if hits else ["General Fire Safety"]

# fallback year: the year a PDF was FIRST captured by the Wayback Machine
# (reports were typically crawled within a year or two of posting) -- shown as approximate
first_seen = {}
cap_file = pathlib.Path("G:/My Drive/FAA_Fire_Safety_Archive/_manifests/all_captures.txt")
if cap_file.exists():
    with open(cap_file, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3 and "/pdf/" in parts[1].lower():
                base = parts[1].rsplit("/", 1)[-1].lower()
                yr = int(parts[2][:4])
                if base not in first_seen or yr < first_seen[base]:
                    first_seen[base] = yr

rows = []
for r in merged:
    y = year_from(r)
    approx = False
    if not y:
        y = first_seen.get(r["pdf"].lower().rsplit("/", 1)[-1])
        approx = y is not None
    rows.append({
        "y": y,
        "yx": approx,
        "k": "Report",
        "n": r.get("report", ""),
        "t": r.get("title", ""),
        "a": r.get("author", ""),
        "p": FILE_BASE + r["pdf"] if r["pdf"].startswith("/") else FILE_BASE + "/" + r["pdf"],
        "c": topics_for(r),
        "ab": (r.get("abstract", "") or "")[:300],
    })

# ---- unindexed report PDFs: metadata recovered from the PDF files themselves ----
pdfmeta_file = SITE / "data" / "reports_pdfmeta.json"
if pdfmeta_file.exists():
    have = {r["p"].lower().rsplit("/", 1)[-1] for r in rows}
    JUNK_TITLE = re.compile(r"^(of Transportation|U\.?S\.? Depa|[\W\d]*$)", re.I)
    JUNK_AUTHOR = re.compile(r"^(unknown|user|owner|admin|faa$)", re.I)
    added = 0
    for r in json.load(open(pdfmeta_file, encoding="utf-8")):
        base = r["pdf"].lower().rsplit("/", 1)[-1]
        if base in have:
            continue
        title = (r.get("title") or "").strip()
        if not title or JUNK_TITLE.match(title):
            title = re.sub(r"[-_]+", " ", base.rsplit(".", 1)[0]).strip()
        author = (r.get("author") or "").strip()
        if JUNK_AUTHOR.match(author) or author.lower() == title.lower():
            author = ""
        y = year_from({"report": "", "pdf": r["pdf"]})
        approx = False
        if not y:
            y = first_seen.get(base)
            approx = y is not None
        rows.append({
            "y": y, "yx": approx, "k": "Report", "n": "",
            "t": title[:220], "a": author,
            "p": FILE_BASE + r["pdf"],
            "c": topics_for({"title": title, "abstract": ""}),
            "ab": "",
        })
        added += 1
    print("pdf-metadata entries added:", added)

# ---- meeting presentations ----
pres = json.load(open(SITE / "data" / "presentations.json", encoding="utf-8"))
for r in pres:
    rows.append({
        "y": r["year"],
        "k": "Presentation",
        "n": r["group"].replace(" Working Group", " WG") + " &middot; " + r["date"],
        "t": r["title"],
        "a": r.get("presenter", ""),
        "p": FILE_BASE + r["files"][0],
        "c": topics_for({"title": r["title"], "abstract": ""}),
        "ab": "",
    })
rows.sort(key=lambda x: (-(x["y"] or 0), x["t"]))
all_topics = sorted({c for r in rows for c in r["c"]})
print("rows:", len(rows), " topics:", len(all_topics), " with year:", sum(1 for r in rows if r["y"]))

# ---- page template: reuse the site's own header/nav/footer ----
shell = (SITE / "directions.html").read_text(encoding="utf-8")
m = re.search(r"(<main[^>]*>)(.*)(</main>)", shell, re.S)
head, tail = shell[:m.end(1)], shell[m.start(3):]
head = re.sub(r"<title>[^<]*</title>", "<title>Report Index : FAA Fire Safety</title>", head, 1)

CONTENT = """
<a name="content"></a>
<div class="container-fluid">
<h2>Reports &amp; Presentations Index</h2>
<p>All __COUNT__ technical reports and meeting presentations recovered from the original site, browsable by topic and
sortable by year. Topics are assigned automatically from titles and abstracts. Click a title to open the file.</p>
<div style="margin:10px 0;">
  <input id="idx-q" type="text" placeholder="Search title, author, abstract, report number&hellip;"
         style="width:60%;max-width:480px;padding:6px 10px;" />
  <select id="kind" style="padding:6px;">
    <option value="">Reports + Presentations</option><option>Report</option><option>Presentation</option>
  </select>
  <select id="topic" style="padding:6px;"><option value="">All topics</option>__TOPICOPTS__</select>
  <select id="sort" style="padding:6px;">
    <option value="yd">Newest first</option><option value="ya">Oldest first</option><option value="t">Title A&ndash;Z</option>
  </select>
  <span id="count" style="margin-left:10px;color:#555;"></span>
</div>
<table class="table table-striped" style="font-size:14px;">
<thead><tr><th style="width:60px;">Year</th><th style="width:100px;">Type</th><th style="width:180px;">Report No. / Meeting</th><th>Title</th><th style="width:190px;">Author / Presenter</th><th style="width:170px;">Topics</th></tr></thead>
<tbody id="rows"></tbody>
</table>
<div style="margin:14px 0;text-align:center;">
  <button type="button" id="pg-prev" class="btn btn-default" style="padding:6px 16px;">&larr; Previous</button>
  <span id="pg-info" style="margin:0 14px;color:#555;"></span>
  <button type="button" id="pg-next" class="btn btn-default" style="padding:6px 16px;">Next &rarr;</button>
</div>
</div>
<script>
var DATA = __DATA__;
var tbody = document.getElementById("rows"), q = document.getElementById("idx-q"),
    topic = document.getElementById("topic"), sortSel = document.getElementById("sort"),
    count = document.getElementById("count"), PAGE = 50, page = 0,
    pgPrev = document.getElementById("pg-prev"), pgNext = document.getElementById("pg-next"),
    pgInfo = document.getElementById("pg-info");
function esc(s){ var d=document.createElement("div"); d.textContent=s||""; return d.innerHTML; }
function render(){
  var term = q.value.toLowerCase(), top = topic.value, mode = sortSel.value,
      kind = document.getElementById("kind").value;
  var rows = DATA.filter(function(r){
    if (kind && r.k !== kind) return false;
    if (top && r.c.indexOf(top) < 0) return false;
    if (!term) return true;
    return (r.t+" "+r.a+" "+r.n+" "+r.ab).toLowerCase().indexOf(term) >= 0;
  });
  rows.sort(function(a,b){
    if (mode==="t") return a.t.localeCompare(b.t);
    var ya=a.y||0, yb=b.y||0;
    return mode==="ya" ? ya-yb || a.t.localeCompare(b.t) : yb-ya || a.t.localeCompare(b.t);
  });
  count.textContent = rows.length + " items";
  var pages = Math.max(1, Math.ceil(rows.length / PAGE));
  if (page >= pages) page = pages - 1;
  if (page < 0) page = 0;
  pgInfo.textContent = "Page " + (page + 1) + " of " + pages;
  pgPrev.disabled = page === 0;
  pgNext.disabled = page >= pages - 1;
  rows = rows.slice(page * PAGE, (page + 1) * PAGE);
  tbody.innerHTML = rows.map(function(r){
    return "<tr><td>"+(r.y ? (r.yx ? "~"+r.y : r.y) : "&mdash;")+"</td><td>"+r.k+"</td><td>"+r.n+"</td><td><a href=\\""+r.p+
      "\\" title=\\""+esc(r.ab)+"\\">"+esc(r.t)+"</a></td><td>"+esc(r.a)+"</td><td>"+r.c.map(esc).join("<br/>")+"</td></tr>";
  }).join("");
}
try { var usp = new URLSearchParams(location.search); if (usp.get("q")) q.value = usp.get("q"); } catch (e) {}
q.addEventListener("input", function(){ page = 0; render(); });
topic.addEventListener("change", function(){ page = 0; render(); });
pgPrev.addEventListener("click", function(){ page--; render(); window.scrollTo(0, 0); });
pgNext.addEventListener("click", function(){ page++; render(); window.scrollTo(0, 0); });
document.getElementById("kind").addEventListener("change", render);
sortSel.addEventListener("change", function(){ page = 0; render(); }); render();
</script>
"""
content = (CONTENT
           .replace("__COUNT__", str(len(rows)))
           .replace("__TOPICOPTS__", "".join(f'<option>{html.escape(t)}</option>' for t in all_topics))
           .replace("__DATA__", json.dumps(rows, separators=(",", ":"))))
out = SITE / "reports" / "browse.html"
out.write_text(head + content + tail, encoding="utf-8")
print("wrote", out)
