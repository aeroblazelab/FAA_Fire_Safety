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
"""

BANNER = """
<div id="archive-banner">
<strong class="lead">&#9888;&#65039; UNOFFICIAL ARCHIVE</strong> &mdash; historical copy of the former FAA Fire Safety website (fire.tc.faa.gov), preserved from the
<a href="https://web.archive.org/web/20241207155156/https://www.fire.tc.faa.gov/">Internet Archive</a>.
<strong>Not affiliated with or endorsed by the Federal Aviation Administration.</strong> Content is U.S. Government work (public domain).
</div>
"""
BANNER_LINK = '<link href="/archive-assets/banner.css" rel="stylesheet"/>'

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

HANDBOOK_NOTE = """
<div style="background:#e8f4fd;border:1px solid #7db9e8;border-radius:6px;padding:14px 18px;margin:12px 0;font-size:14px;line-height:1.6;">
<strong style="font-size:15px;">&#128214; Looking for the official, current Handbook?</strong><br/>
The authoritative copies of the <em>Aircraft Materials Fire Test Handbook</em> are maintained in the FAA&rsquo;s
<a href="https://drs.faa.gov/browse"><strong>Dynamic Regulatory System (DRS)</strong></a>:
scroll to the bottom of the DRS browse page, then click <strong>&ldquo;Fire Safety&rdquo;</strong> &rarr;
<strong>&ldquo;Aircraft Materials Fire Test Handbook&rdquo;</strong>.
<span style="color:#8a6d00;">Note: the separate &ldquo;Revision&nbsp;3&rdquo; entry in DRS is <strong>not yet officially
approved for use</strong>.</span><br/>
<span style="color:#555;">Everything on this page is preserved for historical record only.</span>
</div>
"""

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
    if "<h3>Sign In</h3>" in text:
        for rx, repl in SIGNIN_SUBS:
            text = rx.sub(repl, text)
    if site in ("/handbook/index.html", "/handbook.html"):
        text = text.replace("<h2>Aircraft Materials Fire Test Handbook</h2>",
                            "<h2>Aircraft Materials Fire Test Handbook</h2>" + HANDBOOK_NOTE, 1)
    text = text.replace(LOGO_OLD, LOGO_NEW)
    text = text.replace(
        "Federal Aviation Administration\n                            <br />\n                            Fire Safety",
        "FAA Fire Safety Research &ndash; Unofficial Archive")
    text = URL_ATTR.sub(lambda m: m.group(1) + m.group(2) + rewrite_url(m.group(3), orig) + m.group(2), text)
    # injected after link rewriting so the rewriter never touches our own references
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
    for rawrel in raw_to_site:
        process(rawrel)
    # copy assets referenced from site root (css/js/images) into site tree from Drive files/
    print("pages:", stats["written"], " link rewrites:", dict(stats))
    print("\nTop unresolved link targets:")
    for k, c in unresolved.most_common(15):
        print(f"  {c:5d}  {k}")

if __name__ == "__main__":
    main()
