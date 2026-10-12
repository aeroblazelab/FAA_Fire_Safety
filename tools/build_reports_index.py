#!/usr/bin/env python3
"""Build the browsable report index: dedupe, infer year, assign topics,
emit site/reports/browse.html (table UI styled like the rest of the site)."""
import json, re, html, pathlib, collections

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

rows = []
for r in merged:
    rows.append({
        "y": year_from(r),
        "k": "Report",
        "n": r.get("report", ""),
        "t": r.get("title", ""),
        "a": r.get("author", ""),
        "p": "/files" + r["pdf"] if r["pdf"].startswith("/") else "/files/" + r["pdf"],
        "c": topics_for(r),
        "ab": (r.get("abstract", "") or "")[:300],
    })

# ---- meeting presentations ----
pres = json.load(open(SITE / "data" / "presentations.json", encoding="utf-8"))
for r in pres:
    rows.append({
        "y": r["year"],
        "k": "Presentation",
        "n": r["group"].replace(" Working Group", " WG") + " &middot; " + r["date"],
        "t": r["title"],
        "a": r.get("presenter", ""),
        "p": "/files" + r["files"][0],
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
  <input id="q" type="text" placeholder="Search title, author, abstract, report number&hellip;"
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
</div>
<script>
var DATA = __DATA__;
var tbody = document.getElementById("rows"), q = document.getElementById("q"),
    topic = document.getElementById("topic"), sortSel = document.getElementById("sort"),
    count = document.getElementById("count");
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
  tbody.innerHTML = rows.map(function(r){
    return "<tr><td>"+(r.y||"&mdash;")+"</td><td>"+r.k+"</td><td>"+r.n+"</td><td><a href=\\""+r.p+
      "\\" title=\\""+esc(r.ab)+"\\">"+esc(r.t)+"</a></td><td>"+esc(r.a)+"</td><td>"+r.c.map(esc).join("<br/>")+"</td></tr>";
  }).join("");
}
q.addEventListener("input", render); topic.addEventListener("change", render);
document.getElementById("kind").addEventListener("change", render);
sortSel.addEventListener("change", render); render();
</script>
"""
content = (CONTENT
           .replace("__COUNT__", str(len(rows)))
           .replace("__TOPICOPTS__", "".join(f'<option>{html.escape(t)}</option>' for t in all_topics))
           .replace("__DATA__", json.dumps(rows, separators=(",", ":"))))
out = SITE / "reports" / "browse.html"
out.write_text(head + content + tail, encoding="utf-8")
print("wrote", out)
