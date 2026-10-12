#!/usr/bin/env python3
"""Local preview server: serves site/ as docroot and /files/* from the Drive archive."""
import http.server, socketserver, urllib.parse, pathlib, functools, os

REPO = pathlib.Path(__file__).resolve().parent.parent
SITE = REPO / "site"
FILES = pathlib.Path(r"G:\My Drive\FAA_Fire_Safety_Archive\files")
PORT = int(os.environ.get("PORT", "8787"))

class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        if path.startswith("/files/"):
            return str(FILES / path[len("/files/"):].lstrip("/"))
        p = (SITE / path.lstrip("/"))
        if path.endswith("/"):
            p = p / "index.html"
        return str(p)

    def end_headers(self):
        # the site is being actively rebuilt; never let the browser cache stale pages
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass

with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
    print(f"serving site on http://127.0.0.1:{PORT}")
    httpd.serve_forever()
