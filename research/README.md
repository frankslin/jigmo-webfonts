# Noto CJK (Google Fonts) vs Source Han (Adobe) baseline/line-height research

Read **[findings.md](./findings.md)** for the full writeup with conclusions.

## Layout

```
research/
  README.md            <- this file
  findings.md           <- full report (start here)
  scripts/
    fetch-google-fonts.sh   downloads Google Fonts CSS (wght 400) + every referenced .woff2
    dump-font-tables.sh     ttx -l over research/work/rep/* -> data/tables.tsv
    compare-metrics.py      extracts OS/2/hhea/BASE/head/name/cmap fields -> data/metrics.tsv
    parse_css_ranges.py     finds which unicode-range chunk(s) cover a given test string
    screenshot.js           Playwright: screenshots + canvas ink-bbox measurements of repro/
  data/
    google-noto-*.css       raw Google Fonts CSS2 responses
    urls.tsv                every downloaded font: URL, local path, family
    sha256.tsv               sha256 + size for every downloaded/derived font file
    tables.tsv               SFNT table presence matrix (Google chunks vs Adobe originals)
    metrics.tsv               OS/2/hhea/head/name field values per file
    measure-index.json        Playwright canvas ink-bbox results for repro/index.html
    measure-experiment.json   Playwright results for repro/measure.html (pyftsubset A-E2)
  fonts/
    google/<family-slug>/*.woff2   every woff2 referenced by each Google Fonts CSS response
    adobe/*.otf                     Adobe Source Han Serif/Sans TC Regular, from the
                                     adobe-fonts release branch (raw.githubusercontent.com)
  work/
    rep/                 representative files used for ttx -l / metrics dumps
    ttx-dumps/            ttx -q XML dumps (OS/2, hhea, BASE, head, name, cmap)
    ttx-list-full.txt      full `ttx -l` output for every file in work/rep/
    pyftsubset-experiment/  variants A-E2 isolating BASE / metrics / USE_TYPO_METRICS
  repro/
    index.html            5-source x 3-string x 3-line-height comparison page
    measure.html           pyftsubset A-E2 line-box-height + ink-bbox isolation page
    fonts/                 all woff2 referenced by the two repro pages
    screenshots/            Playwright PNG captures
```

## Re-running from scratch

```bash
pip install fonttools brotli zopfli
bash scripts/fetch-google-fonts.sh
# (Adobe originals + repro asset generation: see findings.md "Repro instructions")
```

Network notes for this environment: `fonts.googleapis.com` / `fonts.gstatic.com` and
`raw.githubusercontent.com` were reachable; `github.com` and `api.github.com` returned 403
(organization egress policy). Adobe's font repos commit the actual OTFs into their `release`
branch, so `raw.githubusercontent.com/.../release/OTF/...` works as a substitute for browsing
GitHub Releases through `github.com`.
