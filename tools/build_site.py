#!/usr/bin/env python3
"""Build the static recreation of fire.tc.faa.gov from Wayback raw captures.

Inputs (Google Drive archive):
  raw_html/            raw HTML pages fetched with Wayback id_ (original bytes)
  _manifests/html_map.tsv       ts <TAB> original_url <TAB> raw_html-relative path
  _manifests/latest_manifest.txt  urlkey original ts mimetype status length

Output:
  <repo>/site/         static site, lowercase paths
                       file links rewritten to FILE_BASE + canonical captured path
"""
import os, re, sys, urllib.parse, pathlib, collections

DRIVE = r"G:\My Drive\FAA_Fire_Safety_Archive"
RAW = os.path.join(DRIVE, "raw_html")
MAP = os.path.join(DRIVE, "_manifests", "html_map.tsv")
MANIFEST = os.path.join(DRIVE, "_manifests", "latest_manifest.txt")
REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "site"
FILE_BASE = os.environ.get("FILE_BASE", "/files")  # where pdf/ppt/zip/etc. are served
WAYBACK_FALLBACK = "https://web.archive.org/web/2024/"  # for links whose target was never captured locally

HOST_RE = re.compile(r"^https?://(www\.)?fire\.tc\.faa\.gov(:80)?", re.I)

def norm_key(path_query: str) -> str:
    """case-insensitive lookup key for a site-relative url (no leading slash)"""
    return urllib.parse.unquote(path_query).lstrip("/").lower()

def qsafe(query: str) -> str:
    """must mirror the bash capture naming: tr -c 'A-Za-z0-9._=-' '_' | cut -c1-80"""
    return re.sub(r"[^A-Za-z0-9._=-]", "_", query)[:80]

# ---- load html map: original url -> static site path (lowercase) ----
html_lookup = {}   # norm_key -> site path ("/..." lowercase)
raw_to_site = {}   # raw file (drive-relative, / separators) -> (site path, original url)
with open(MAP, encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 3:
            continue
        ts, orig, rawrel = parts
        rel = HOST_RE.sub("", orig).lstrip("/")
        path, _, query = rel.partition("?")
        if query:
            site = f"{path}__Q_{qsafe(query)}.html"
        elif rel == "" or rel.endswith("/"):
            site = f"{path}index.html"
        else:
            site = f"{path}.html"
        site = "/" + site.lower()
        html_lookup[norm_key(rel)] = site
        raw_to_site[rawrel.replace("\\", "/")] = (site, orig)

# ---- load file manifest: norm path -> canonical captured path (original case) ----
file_lookup = {}
with open(MANIFEST, encoding="utf-8") as f:
    for line in f:
        p = line.split()
        if len(p) < 6 or p[3] == "text/html":
            continue
        orig = p[1]
        rel = HOST_RE.sub("", orig).lstrip("/")
        path = rel.partition("?")[0]
        if not path:
            continue
        file_lookup[norm_key(path)] = "/" + urllib.parse.unquote(path)

BANNER_CSS = """/* single source of truth for the archive banner, referenced by every page */
#archive-banner {
  background: #ffc107;
  color: #1a1a1a;
  padding: 12px 16px;
  font-size: 15px;
  line-height: 1.6;
  text-align: center;
  font-family: Arial, Helvetica, sans-serif;
  border-bottom: 3px solid #1a1a2e;
}
#archive-banner strong.lead { font-size: 16px; }
#archive-banner a { color: #0b4ea2; font-weight: bold; }

/* first-visit notice modal */
#archive-modal-overlay {
  position: fixed; inset: 0; background: rgba(10,10,30,.65);
  z-index: 99999; display: flex; align-items: center; justify-content: center; padding: 16px;
}
#archive-modal {
  background: #fff; max-width: 560px; border-radius: 8px; padding: 26px 30px;
  font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.6; color: #1a1a1a;
  box-shadow: 0 12px 40px rgba(0,0,0,.4); border-top: 6px solid #ffc107;
}
#archive-modal h2 { margin: 0 0 10px; font-size: 21px; }
#archive-modal button {
  margin-top: 16px; padding: 10px 22px; font-size: 15px; font-weight: bold;
  background: #0b4ea2; color: #fff; border: 0; border-radius: 5px; cursor: pointer;
}
#archive-modal button:hover { background: #09407f; }

/* handbook: standout official-source notice + collapsed historical content */
.handbook-official {
  background: #fff3cd; border: 3px solid #e67e22; border-radius: 8px;
  padding: 20px 24px; margin: 16px 0; font-size: 17px; line-height: 1.7;
}
.handbook-official .hb-title { font-size: 20px; color: #b34700; }
.handbook-reveal {
  display: inline-block; margin: 6px 0 18px; padding: 10px 20px; font-size: 15px;
  background: #e9ecef; color: #333; border: 1px solid #adb5bd; border-radius: 5px; cursor: pointer;
}
.handbook-reveal:hover { background: #dde0e3; }
"""

ARCHIVE_JS = r"""// first-visit notice: shown once per browser session
(function () {
  var KEY = "archiveNoticeSeen";
  try { if (sessionStorage.getItem(KEY)) return; } catch (e) {}
  function show() {
    var o = document.createElement("div");
    o.id = "archive-modal-overlay";
    o.innerHTML = '<div id="archive-modal" role="dialog" aria-modal="true" aria-labelledby="am-title">' +
      '<h2 id="am-title">&#9888;&#65039; Unofficial Historical Archive</h2>' +
      '<p>This is a preserved <strong>snapshot of the former FAA Fire Safety website</strong> ' +
      '(fire.tc.faa.gov) as captured through <strong>October&nbsp;2025</strong>, rebuilt from the ' +
      'Internet Archive after the original site went offline.</p>' +
      '<p><strong>Content is historical record only and is no longer being updated.</strong> ' +
      'This archive is not affiliated with or endorsed by the Federal Aviation Administration. ' +
      'For current regulations and guidance, use the FAA’s ' +
      '<a href="https://drs.faa.gov/" target="_blank" rel="noopener">Dynamic Regulatory System (DRS)</a>.</p>' +
      '<p style="font-size:13.5px;color:#555;">Built and hosted by ' +
      '<a href="https://www.aeroblazelab.com/" target="_blank" rel="noopener">Aeroblaze Laboratory</a> ' +
      'to keep these essential presentations, reports, and test resources accessible to the community ' +
      'while official channels are unavailable. <a href="/about-archive.html">About this archive &rarr;</a></p>' +
      '<button type="button" id="am-ok">I understand &mdash; view the archive</button></div>';
    document.body.appendChild(o);
    document.getElementById("am-ok").addEventListener("click", function () {
      try { sessionStorage.setItem(KEY, "1"); } catch (e) {}
      o.remove();
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", show);
  else show();
})();

// handbook: collapse historical content behind a reveal button
(function () {
  var hist = document.getElementById("handbook-historical");
  if (!hist) return;
  var btn = document.getElementById("handbook-reveal-btn");
  btn.addEventListener("click", function () {
    hist.style.display = "";
    btn.style.display = "none";
  });
})();
"""

BANNER = """
<div id="archive-banner">
<strong class="lead">&#9888;&#65039; UNOFFICIAL ARCHIVE</strong> &mdash; a <strong>snapshot of the former FAA Fire Safety website</strong> (fire.tc.faa.gov) as of <strong>October 2025</strong>, preserved from the
<a href="https://web.archive.org/web/20241207155156/https://www.fire.tc.faa.gov/">Internet Archive</a>.
<strong>Historical record only; no longer updated. Not affiliated with or endorsed by the FAA.</strong>
&middot; <a href="/about-archive.html">About this archive</a>
</div>
"""
BANNER_LINK = ('<link href="/archive-assets/banner.css" rel="stylesheet"/>'
               '<link rel="icon" href="/archive-assets/favicon.svg" type="image/svg+xml"/>'
               '<script src="/archive-assets/archive.js" defer></script>')

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<circle cx="32" cy="32" r="30" fill="#b22222"/>
<path d="M32 12c4 8 12 12 12 22a12 12 0 0 1-24 0c0-6 3-9 6-13 0 4 2 6 4 7-1-5 0-11 2-16z" fill="#ffc107"/>
</svg>
"""

PAGE_404 = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Not Found : FAA Fire Safety Archive</title>
<link href="/archive-assets/banner.css" rel="stylesheet"/>
<link rel="icon" href="/archive-assets/favicon.svg" type="image/svg+xml"/>
<style>
body { font-family: Arial, Helvetica, sans-serif; margin: 0; color: #1a1a1a; }
.wrap { max-width: 640px; margin: 60px auto; padding: 0 20px; text-align: center; }
h1 { font-size: 26px; }
.actions a, .actions button {
  display: inline-block; margin: 8px; padding: 10px 20px; font-size: 15px;
  background: #0b4ea2; color: #fff; border: 0; border-radius: 5px;
  text-decoration: none; cursor: pointer;
}
.muted { color: #555; font-size: 14px; line-height: 1.6; }
</style>
</head>
<body>
<div id="archive-banner">
<strong class="lead">&#9888;&#65039; UNOFFICIAL ARCHIVE</strong> &mdash; snapshot of the former FAA Fire Safety website (fire.tc.faa.gov) as of October 2025.
</div>
<div class="wrap">
<h1>&#128293; Page not found in this archive</h1>
<p class="muted">This page or file may not have been captured before the original FAA Fire Safety
site went offline, or the address may have changed. Two good options:</p>
<div class="actions">
<a href="/reports/browse.html">Search the Reports &amp; Presentations Index</a>
<button type="button" id="wb">Look for this page on the Wayback Machine</button>
</div>
<p class="muted"><a href="/">&larr; Back to the archive home page</a> &middot; <a href="/about-archive.html">About this archive</a></p>
</div>
<script>
document.getElementById("wb").addEventListener("click", function () {
  location.href = "https://web.archive.org/web/2024/https://www.fire.tc.faa.gov" +
    location.pathname + location.search;
});
</script>
</body>
</html>
"""

ROBOTS_TXT = """User-agent: *
Allow: /

Sitemap: https://firesafety.aeroblazelab.com/sitemap.xml
"""

ABOUT_CONTENT = """
<a name="content"></a>
<div class="container-fluid">
<h2>About This Archive</h2>

<p><strong>This is an unofficial, historical archive of the former FAA Fire Safety website</strong>
(<code>fire.tc.faa.gov</code>) &mdash; the online home of the Fire Safety Branch at the FAA William J.
Hughes Technical Center. The original site went offline and was not restored. This archive is a
<strong>snapshot as captured through October 2025</strong>, rebuilt from pages and files preserved by the
<a href="https://web.archive.org/web/20241207155156/https://www.fire.tc.faa.gov/">Internet Archive&rsquo;s Wayback Machine</a>.
It is not affiliated with or endorsed by the Federal Aviation Administration, and its content is
<strong>no longer being updated</strong>.</p>

<h3>Why this exists</h3>
<p>For decades, the Fire Safety site was where the aviation community went for fire test methods, the
<em>Aircraft Materials Fire Test Handbook</em>, working-group meeting presentations, training videos, and
over a thousand technical reports &mdash; material that labs, manufacturers, designated engineering
representatives, and researchers rely on in day-to-day certification work. When the site disappeared,
that access disappeared with it. This archive is a <strong>temporary bridge</strong>: a place to keep those
essential presentations, reports, and files reachable until official channels fully restore them.</p>

<h3>Who built it</h3>
<p>This archive was built and is hosted by
<a href="https://www.aeroblazelab.com/"><strong>Aeroblaze Laboratory</strong></a>, an FAA-accepted
aircraft interior flammability testing laboratory that depends on &mdash; and believes in open access
to &mdash; this body of public fire-safety research.</p>

<h3>What&rsquo;s here, and what isn&rsquo;t</h3>
<ul>
<li>All major sections of the original site: working-group pages, ~68 meeting archives, nine
international conference sites (1998&ndash;2022), the Fire Test Handbook, and a searchable
<a href="/reports/browse.html">Reports &amp; Presentations Index</a> built from the original report database.</li>
<li>Documents are preserved exactly as published, including original FAA authorship and attribution.</li>
<li>Some content was never captured before the site went offline and could not be recovered; links to
missing items fall back to a Wayback Machine lookup. Pages behind the old meeting-registration login
were never publicly archived.</li>
</ul>

<h3>Official sources</h3>
<p>For current, authoritative material, use the FAA&rsquo;s
<a href="https://drs.faa.gov/">Dynamic Regulatory System (DRS)</a> and the
<a href="https://rosap.ntl.bts.gov/">National Transportation Library (ROSA-P)</a>. Works of the U.S.
Government are in the public domain (17 U.S.C. &sect; 105).</p>

<h3>Problems or corrections</h3>
<p>Found a broken link, a missing document you can source, or an error? Open an issue on the
<a href="https://github.com/a-feghali/FAA_Fire_Safety">project&rsquo;s GitHub repository</a>.</p>
</div>
"""

LOGO_OLD = '<img src="/Resources/logoFAA.png" alt="FAA Fire Safety" />'
LOGO_NEW = '<span style="display:inline-block;width:36px;height:36px;border-radius:50%;background:#b22222;color:#fff;font-size:20px;text-align:center;line-height:36px;vertical-align:middle;" aria-hidden="true">&#128293;</span>'

# site-wide alert that is stale in an archive (conference has long since happened/moved)
POSTPONED_RE = re.compile(
    r'<div class="page-header text-center alert alert-info">\s*'
    r'<h2><a href="[^"]*">2025 TRIENNIAL CONFERENCE POSTPONED[^<]*</a></h2>\s*</div>', re.S)

# ---- sign-in removal (registration backend no longer exists) ----
# the whole sidebar sign-in block on the meetings pages is dropped outright
SIGNIN_BLOCK_RE = re.compile(
    r'<div class="content-block">\s*<h3>Sign In</h3>.*?20 minute period of inactivity\.\s*</p>\s*</div>', re.S)
# any other stray login forms (account-creation page etc.) get their fields disabled
SIGNIN_SUBS = [
    (re.compile(r'(<input[^>]*\bname="(?:Email|Password)"[^>]*?)\s*/>', re.I),
     r'\1 disabled style="background:#e9e9e9;color:#888;" />'),
    (re.compile(r'(<button type="submit"[^>]*class="btn btn-primary"[^>]*)>(\s*Sign In\s*)</button>', re.I),
     r'\1 disabled style="opacity:.5;cursor:not-allowed;" title="Sign-in disabled in this archive">\2</button>'),
]

# nav item removed: the Conference entry (conference sites remain reachable from Meetings)
CONFERENCE_NAV_RE = re.compile(r'<li>\s*<a href="/2022Conference/conference\.asp">\s*Conference\s*</a>\s*</li>', re.I)

# meetings page: the offcanvas sidebar held only the sign-in block; once that is
# removed, drop the empty sidebar, its Menu toggle, and widen the content column
EMPTY_SIDEBAR_RE = re.compile(r'<div class="col-md-3 sidebar-offcanvas" id="sidebar">\s*</div>', re.S)
MENU_TOGGLE_RE = re.compile(r'<button type="button" class="btn btn-primary btn-xs" data-toggle="offcanvas">.*?Menu</button>', re.S)

HANDBOOK_NOTE = """
<div class="handbook-official">
<strong class="hb-title">&#128214; Looking for the official, current Handbook?</strong><br/>
The authoritative copies of the <em>Aircraft Materials Fire Test Handbook</em> are maintained in the FAA&rsquo;s
<a href="https://drs.faa.gov/browse"><strong>Dynamic Regulatory System (DRS)</strong></a>:
scroll to the bottom of the DRS browse page, then click <strong>&ldquo;Fire Safety&rdquo;</strong> &rarr;
<strong>&ldquo;Aircraft Materials Fire Test Handbook&rdquo;</strong>.<br/>
<span style="color:#8a6d00;">Note: the separate &ldquo;Revision&nbsp;3&rdquo; entry in DRS is <strong>not yet officially
approved for use</strong>.</span><br/>
<span style="color:#555;">The chapters and appendixes below are preserved for historical record only and are no longer updated.</span>
</div>
"""

HANDBOOK_REVEAL_BTN = '<button type="button" id="handbook-reveal-btn" class="handbook-reveal">&#9660; View historical Handbook chapters &amp; appendixes</button>'

SCRIPT_STRIP = [
    # Google Analytics (gtag) pair
    re.compile(r'<!-- Global site tag \(gtag\.js\).*?</script>\s*<script>.*?gtag\(\'config\'[^<]*</script>', re.S),
    # Akamai boomerang / mPulse blobs
    re.compile(r'<script>\(window\.BOOMR_mq.*?</script>', re.S),
    re.compile(r'<script>!function\(e\)\{var n="https://s\.go-mpulse\.net.*?</script>', re.S),
    re.compile(r'<script>.{0,200}?BOOMR_lstart.*?</script>', re.S),
    re.compile(r'<script[^>]*src="[^"]*go-mpulse[^"]*"[^>]*>\s*</script>', re.S),
]

URL_ATTR = re.compile(r'''(\b(?:href|src|action)\s*=\s*)(['"])(.*?)\2''', re.I | re.S)

stats = collections.Counter()
unresolved = collections.Counter()

def rewrite_url(url: str, page_orig: str) -> str:
    u = url.strip()
    if not u or u.startswith(("#", "mailto:", "javascript:", "data:")):
        return url
    # absolute external?
    if re.match(r"^(https?:)?//", u, re.I):
        if not HOST_RE.match(u if u.lower().startswith("http") else "https:" + u):
            stats["external"] += 1
            return url
    # resolve against the page's original url, then strip host
    absu = urllib.parse.urljoin(page_orig, u)
    if not HOST_RE.match(absu):
        stats["external"] += 1
        return url
    rel = HOST_RE.sub("", absu).lstrip("/")
    path, _, query = rel.partition("?")
    frag = ""
    if "#" in path:
        path, _, frag = path.partition("#")
    elif "#" in query:
        query, _, frag = query.partition("#")
    frag = ("#" + frag) if frag else ""
    # the site's inline document viewer: /home/Viewer?path=/pdf/... -> link the file directly
    if norm_key(path) == "home/viewer" and query:
        qs = urllib.parse.parse_qs(query)
        target = (qs.get("path") or [""])[0]
        if target:
            tkey = norm_key(target)
            if tkey in file_lookup:
                stats["viewer_file"] += 1
                return FILE_BASE + urllib.parse.quote(file_lookup[tkey]) + frag
        stats["viewer_unresolved"] += 1
        return WAYBACK_FALLBACK + urllib.parse.quote(absu, safe=":/?&=%")
    # html page? (try exact, then with/without trailing slash)
    key = norm_key(path + ("?" + query if query else ""))
    candidates = [key]
    if not query:
        candidates.append(key.rstrip("/") if key.endswith("/") else key + "/")
    for k in candidates:
        if k in html_lookup:
            stats["page"] += 1
            return html_lookup[k] + frag
    # page without its query variant captured -> try bare page
    if query:
        for k in (norm_key(path), norm_key(path) + "/"):
            if k in html_lookup:
                stats["page_dropquery"] += 1
                return html_lookup[k] + frag
    # downloadable file?
    fkey = norm_key(path)
    if fkey in file_lookup:
        stats["file"] += 1
        return FILE_BASE + urllib.parse.quote(file_lookup[fkey]) + frag
    # spacer gifs: original site had them at many paths; serve the generated stub
    if fkey.endswith("images/pixel.gif"):
        stats["file"] += 1
        return FILE_BASE + "/reports/images/pixel.gif"
    # the old dynamic report search cannot work statically: send it to the browsable index
    if re.search(r"reports/(searchresults|listresults)\.asp$", norm_key(path)):
        stats["search_to_index"] += 1
        return "/reports/browse.html"
    # not captured: degrade gracefully to a Wayback Machine lookup instead of a local 404
    stats["unresolved"] += 1
    unresolved[rel[:120]] += 1
    return WAYBACK_FALLBACK + urllib.parse.quote(absu, safe=":/?&=%")

def process(rawrel: str):
    site, orig = raw_to_site[rawrel]
    src = os.path.join(DRIVE, rawrel.replace("/", os.sep))  # map paths already start with raw_html/
    try:
        text = open(src, encoding="utf-8", errors="replace").read()
    except OSError as e:
        stats["read_error"] += 1
        return
    for rx in SCRIPT_STRIP:
        text = rx.sub("", text)
    text = POSTPONED_RE.sub("", text)
    text = CONFERENCE_NAV_RE.sub("", text)
    text = SIGNIN_BLOCK_RE.sub("", text)
    cleaned = EMPTY_SIDEBAR_RE.sub("", text)
    if cleaned != text:
        text = MENU_TOGGLE_RE.sub("", cleaned).replace(
            '<div class="col-md-9">', '<div class="col-md-12">', 1)
    if "<h3>Sign In</h3>" in text:
        for rx, repl in SIGNIN_SUBS:
            text = rx.sub(repl, text)
    if site in ("/handbook/index.html", "/handbook.html"):
        h2 = "<h2>Aircraft Materials Fire Test Handbook</h2>"
        text = text.replace(h2, h2 + HANDBOOK_NOTE, 1)
        # Resources and regulatory links stay visible; the chapter/appendix listing
        # (from its heading to </main>) collapses behind the reveal button
        chapters = "<h3>Individual Chapters and Appendixes"
        start = text.find(chapters)
        end = text.find("</main>", start)
        if start >= 0 and end > start:
            text = (text[:start] + HANDBOOK_REVEAL_BTN
                    + '<div id="handbook-historical" style="display:none;">'
                    + text[start:end] + "</div>" + text[end:])
    text = text.replace(LOGO_OLD, LOGO_NEW)
    text = text.replace(
        "Federal Aviation Administration\n                            <br />\n                            Fire Safety",
        "FAA Fire Safety Research &ndash; Unofficial Archive")
    text = URL_ATTR.sub(lambda m: m.group(1) + m.group(2) + rewrite_url(m.group(3), orig) + m.group(2), text)
    # --- post-rewrite chrome wiring (our own paths; the rewriter must not touch them) ---
    # header search box: repoint the dead faa.gov search at the local index
    text = re.sub(r'action="https://web\.archive\.org/web/[^"]*faa\.gov/search/?"|action="https?://(?:www\.)?faa\.gov/search/?"',
                  'action="/reports/browse.html"', text)
    # nav: Reports entry goes straight to the browsable index
    text = text.replace('<a href="/reports/reports.asp.html">Reports</a>',
                        '<a href="/reports/browse.html">Reports</a>')
    text = text.replace("</head>", BANNER_LINK + "\n</head>", 1)
    text = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + BANNER, text, count=1)
    dest = OUT / site.lstrip("/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    stats["written"] += 1

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assets = OUT / "archive-assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "banner.css").write_text(BANNER_CSS, encoding="utf-8")
    (assets / "archive.js").write_text(ARCHIVE_JS, encoding="utf-8")
    (assets / "favicon.svg").write_text(FAVICON_SVG, encoding="utf-8")
    (OUT / "404.html").write_text(PAGE_404, encoding="utf-8")
    (OUT / "robots.txt").write_text(ROBOTS_TXT, encoding="utf-8")
    for rawrel in raw_to_site:
        process(rawrel)
    # about page: reuse the site's own shell (header/nav/footer) around our content
    shell = (OUT / "directions.html").read_text(encoding="utf-8")
    m = re.search(r"(<main[^>]*>)(.*)(</main>)", shell, re.S)
    about = shell[:m.end(1)] + ABOUT_CONTENT + shell[m.start(3):]
    about = re.sub(r"<title>[^<]*</title>", "<title>About This Archive : FAA Fire Safety</title>", about, 1)
    (OUT / "about-archive.html").write_text(about, encoding="utf-8")
    # sitemap: every page at its pretty url
    base = "https://firesafety.aeroblazelab.com"
    urls = []
    for p in sorted(OUT.rglob("*.html")):
        rel = p.relative_to(OUT).as_posix()
        if rel == "404.html":
            continue
        if rel.endswith("/index.html"):
            rel = rel[: -len("index.html")]
        elif rel == "index.html":
            rel = ""
        else:
            rel = rel[: -len(".html")]
        urls.append(f"<url><loc>{base}/{rel}</loc></url>")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")
    print("sitemap urls:", len(urls))
    # copy assets referenced from site root (css/js/images) into site tree from Drive files/
    print("pages:", stats["written"], " link rewrites:", dict(stats))
    print("\nTop unresolved link targets:")
    for k, c in unresolved.most_common(15):
        print(f"  {c:5d}  {k}")

if __name__ == "__main__":
    main()
