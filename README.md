# FAA Fire Safety — Unofficial Archive

A static recreation of the former **FAA Fire Safety website** (`fire.tc.faa.gov`), rebuilt from
captures preserved by the [Internet Archive's Wayback Machine](https://web.archive.org/web/20241207155156/https://www.fire.tc.faa.gov/).
The original site — home of the FAA William J. Hughes Technical Center's Fire Safety Branch —
went offline and was not restored; this project preserves its content for the aviation
fire-safety community.

> **⚠️ Unofficial archive.** This project is **not affiliated with or endorsed by the Federal
> Aviation Administration**. Content is preserved for historical record. Works of the U.S.
> Government are in the public domain (17 U.S.C. § 105). FAA logos and seals have been removed
> to avoid any implication of official status. For current official guidance, see the FAA's
> [Dynamic Regulatory System](https://drs.faa.gov/).

## What's here

- `site/` — the deployable static site (~2,700 pages): all section pages, 68+ working-group
  meeting pages, nine conference sites (1998–2022), the Aircraft Materials Fire Test Handbook
  section, and a searchable [Reports & Presentations Index](site/reports/browse.html) covering
  877 technical reports and 1,281 meeting presentations with automatic topic categorization.
- `tools/` — the pipeline that builds it:
  - `build_site.py` — transforms raw Wayback captures into the static site (link rewriting,
    dynamic-URL flattening, tracking-script removal, branding/disclaimer injection).
    `FILE_BASE` env var sets where downloadable files are served from.
  - `extract_reports.py` / `extract_presentations.py` — mine report and presentation metadata
    from captured database pages (three markup generations, 2004–2025).
  - `build_reports_index.py` — generates the searchable index page.
  - `serve.py` — local preview server (serves `site/` plus the file archive).

## What's not here

The downloadable file archive (~60 GB: 6,700+ PDFs, 1,000+ presentations, training videos) is
too large for git. It lives in object storage (Cloudflare R2) and the site links to it via
`FILE_BASE`. Raw Wayback captures and download manifests are kept offline for reproducibility.

## Build

```bash
python tools/build_site.py          # raw captures -> site/
python tools/extract_reports.py    # mine report metadata
python tools/extract_presentations.py
python tools/build_reports_index.py  # generate the index page
python tools/serve.py              # preview at http://localhost:8787
```

## Contributing

Issues and pull requests are welcome — especially reports of broken links, missing documents
you can source elsewhere, or corrections to the automatic topic categorization. All changes to
`main` require review (see `.github/CODEOWNERS`). Please don't commit large binary files;
the file archive lives in object storage, not git.

## License & provenance

- **Archived content** (reports, presentations, page text, images, videos): works of the U.S.
  Government, public domain under 17 U.S.C. § 105. Original authorship and FAA attribution are
  preserved within the documents themselves.
- **Build pipeline** (`tools/`): see `LICENSE`.
- Every page was sourced from the Wayback Machine (latest capture per URL); download manifests
  recording the exact capture timestamps are retained for reproducibility.

## Status

- [x] Full Wayback enumeration (194k captures, 69k unique URLs)
- [x] Site rebuild (2,675 pages, ~62k internal links rewritten)
- [x] Reports & Presentations index with topic filters
- [x] PDFs downloaded (6,700+ files, 18 GB)
- [ ] PowerPoint archive download (31 GB, in progress)
- [ ] Videos + 2004 conference files (6 GB, in progress)
- [ ] CSRTG Aircraft Accident Database rebuild (~14,600 captured views)
- [ ] Production hosting (Cloudflare Pages + R2)
