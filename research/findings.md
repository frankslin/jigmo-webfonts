# Google Fonts Noto CJK (TC/SC) vs Adobe Source Han — baseline/line-height investigation

Date: 2026-07-04
Scope: `Noto Serif TC`, `Noto Sans TC` (primary), `Noto Serif SC`, `Noto Sans SC` (auxiliary) served by
Google Fonts, compared against the current official Adobe releases of `Source Han Serif TC` and
`Source Han Sans TC`. Weight tested: 400 (Regular) only.

Everything below was produced by the scripts in `research/scripts/` against the files in
`research/fonts/` and `research/repro/`. Re-running `scripts/fetch-google-fonts.sh` will re-download
current Google Fonts assets (they may differ from what's recorded here if Google ships a new build).

> **Erratum (post-publication correction):** an earlier version of the repro pages
> (`repro/index.html`, `repro/per-char.html`) included a `<link>` tag loading the live
> `fonts.googleapis.com` CSS to render a "Google Fonts CDN (network)" comparison variant. In this
> sandboxed environment, headless Chromium (launched via Playwright) cannot reach
> `fonts.googleapis.com`/`fonts.gstatic.com` through the egress proxy this environment requires —
> unlike `curl`, which reads `HTTPS_PROXY` automatically and was used for every download in §1, Chromium
> does not use that env var by default, and the request fails with `net::ERR_CONNECTION_RESET`
> (confirmed reproducible, and not fixed by explicitly passing `--proxy-server`, disabling QUIC, or
> disabling Encrypted Client Hello — the exact proxy-side cause was not isolated). When the `<link>`
> silently failed, `font-family: 'Noto Serif TC'` resolved to nothing, `document.fonts` never
> registered it, and CSS fell through to the generic `serif` keyword — which triggered Chromium's
> own system-fallback logic to substitute **`WenQuanYi Zen Hei`** (a pre-installed, unrelated
> sans-serif Chinese font, nothing to do with Noto or Source Han) for every CJK character. This was
> caught by pixel-diffing an explicit `font-family: 'WenQuanYi Zen Hei'` render against the "Google
> Fonts CDN" render: identical. **All data and screenshots previously labeled "Google Fonts CDN
> (network)" have been removed** — they were not measuring Noto Serif TC at all. The tables in §3
> (built from files downloaded by `curl`, hash-verified in `data/sha256.tsv`) were never affected by
> this bug and remain valid; only the live-in-browser rendering variant was wrong. The "self-hosted
> Google woff2" variant is unaffected (it only ever loaded local files) and is now the sole
> representative of Google's font in the repro pages, since it is byte-identical to what
> `fonts.gstatic.com` serves.

## 1. What was downloaded

### 1.1 Google Fonts (via CSS2 API, Chrome UA, `wght@400`)

| family | CSS build tag (from woff2 URL) | internal `name` version string (nameID 5) |
|---|---|---|
| Noto Serif TC | v36 | `Version 2.003-H1;hotconv 1.1.1;makeotfexe 2.6.0` |
| Noto Sans TC  | v39 | `Version 2.004-H2;hotconv 1.0.118;makeotfexe 2.5.65603` |
| Noto Serif SC | v35 | `Version 2.003-H1;hotconv 1.1.1;makeotfexe 2.6.0` |
| Noto Sans SC  | v40 | `Version 2.004-H2;hotconv 1.0.118;makeotfexe 2.5.65603` |

Each CSS response contains ~101-108 `@font-face` blocks (one per `unicode-range` chunk of ≈256
code points, i.e. Google's usual CJK chunking). **All** of them were downloaded:

- Noto Serif TC: 108 files, 3.2 MB
- Noto Sans TC: 105 files, 2.4 MB
- Noto Serif SC: 101 files, 3.3 MB
- Noto Sans SC: 101 files, 2.6 MB

Full URL → local path list: `data/urls.tsv` (416 rows). Full SHA-256 + size: `data/sha256.tsv`.
Raw CSS responses: `data/google-noto-{serif,sans}-{tc,sc}.css`.

### 1.2 Adobe Source Han originals

Adobe's release assets are hosted on GitHub. `github.com` and `api.github.com` were **not reachable**
from this environment's egress proxy (403, organization policy), but `raw.githubusercontent.com` was
reachable, and Adobe commits the actual per-language, per-weight static OTFs directly into the
`release` branch of each repo (not only as zipped release assets), so the individual font files were
fetched from there instead:

| font | source URL | release tag (per repo README) | internal version (nameID 5) | SHA-256 |
|---|---|---|---|---|
| Source Han Serif TC Regular | `https://raw.githubusercontent.com/adobe-fonts/source-han-serif/release/OTF/TraditionalChinese/SourceHanSerifTC-Regular.otf` | 2.003R | `Version 2.003;hotconv 1.1.1;makeotfexe 2.6.0` | `659c9606d8fda03372247b99ec5e5bbc5a034e06a70d80fb00546772c582d3e5` |
| Source Han Sans TC Regular | `https://raw.githubusercontent.com/adobe-fonts/source-han-sans/release/OTF/TraditionalChinese/SourceHanSansTC-Regular.otf` | 2.005R | `Version 2.005;addfeatures 5.0.0b21` | `10e6d832bc73650840aa7fbfec4e10c527f8136ae2aec71c3e1c13a67475c24a` |

**Verified, citable fact:** Google's Noto Sans TC/SC (v39/v40) embeds source version string
`2.004-H2`, while Adobe's current public release of Source Han Sans is `2.005R`. Google's Sans build
is one upstream version behind Adobe's current release. For Serif, both sides say `2.003`, i.e. no
version lag was found there. This was **not** cross-checked against an archived 2.004R Source Han
Sans release (none was fetched in this investigation, since Adobe's `release` branch only carries the
current version), so whether Adobe changed any vertical metrics between 2.004 and 2.005 is **not
proven either way** — flagged as an open question, not a conclusion.

## 2. Table structure comparison (`ttx -l`)

Ran on 8 representative Google chunks (Latin-range chunk + one CJK-range chunk, per TC/SC ×
Serif/Sans) and the 2 Adobe originals. Full listing: `work/ttx-list-full.txt`; matrix: `data/tables.tsv`.

| file | OS/2 | hhea | BASE | vhea | vmtx | name | cmap | head | maxp | GSUB | GPOS | GDEF | STAT | glyf | loca | CFF | prep | gasp | DSIG | VORG |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SourceHanSansTC-Regular.otf  | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | – | – | – | ✔ | – | – | ✔ | ✔ |
| SourceHanSerifTC-Regular.otf | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | – | – | – | ✔ | – | – | ✔ | ✔ |
| noto-sans-tc (Latin chunk)   | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | – | ✔ | ✔ | – | – |
| noto-sans-tc (CJK chunk)     | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | – | ✔ | ✔ | ✔ | – | ✔ | ✔ | – | – |
| noto-serif-tc (Latin chunk)  | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | – | ✔ | ✔ | – | – |
| noto-serif-tc (CJK chunk)    | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | – | ✔ | ✔ | ✔ | – | ✔ | ✔ | – | – |
| noto-sans-sc / noto-serif-sc | (same pattern as the corresponding TC row) | | | | | | | | | | | | | | | | | | |

Findings:

- **`BASE` is present in every single file checked** — all 4 Google families' chunks (Latin and CJK
  alike) and both Adobe originals. No case of a missing `BASE` table was found in the currently-shipped
  builds.
- Adobe's originals are **CFF-flavored OpenType** (PostScript outlines, `CFF` table, `VORG` for
  vertical origins, `DSIG` dummy signature, no `glyf`/`loca`/variable-font remnants).
- Google's current builds are **TrueType-flavored** (`glyf`/`loca`/`prep`/`gasp`) and carry a leftover
  `STAT` table even though no `fvar` is present — i.e. these are static instances cut from a variable
  font source, and the `STAT` table from that variable source was not stripped. This is a real,
  structural technology difference (cubic PostScript curves vs quantized quadratic TrueType curves),
  but it does not by itself touch `hhea`/`OS/2`/`BASE` numeric fields (see §3).
- `GDEF` is present in the Latin chunk but absent from the CJK chunk of the same Google font. This is
  an artifact of per-chunk subsetting (no mark-attachment glyphs survive in that particular 256-code
  point chunk) and was observed consistently across all four families — not a Google-vs-Adobe
  difference.

## 3. OS/2 / hhea / BASE / head / name / cmap field comparison

Full dump: `data/metrics.tsv` (machine-readable), raw TTX XML in `work/ttx-dumps/*.ttx`. Script:
`scripts/compare-metrics.py`.

| file | unitsPerEm | hhea asc/desc/lineGap | OS/2 sTypo asc/desc/lineGap | OS/2 usWin asc/desc | fsSelection | BASE present |
|---|---|---|---|---|---|---|
| SourceHanSerifTC-Regular (Adobe) | 1000 | 1151 / -286 / 0 | 880 / -120 / 0 | 1151 / 286 | `0x0040` (REGULAR only) | ✔ |
| noto-serif-tc, Latin chunk (Google) | 1000 | 1151 / -286 / 0 | 880 / -120 / 0 | 1151 / 286 | `0x0040` (REGULAR only) | ✔ |
| noto-serif-tc, CJK chunk (Google)   | 1000 | 1151 / -286 / 0 | 880 / -120 / 0 | 1151 / 286 | `0x0040` (REGULAR only) | ✔ |
| noto-serif-sc, both chunks (Google) | 1000 | 1151 / -286 / 0 | 880 / -120 / 0 | 1151 / 286 | `0x0040` (REGULAR only) | ✔ |
| SourceHanSansTC-Regular (Adobe)  | 1000 | 1160 / -288 / 0 | 880 / -120 / 0 | 1160 / 288 | `0x0040` (REGULAR only) | ✔ |
| noto-sans-tc, both chunks (Google) | 1000 | 1160 / -288 / 0 | 880 / -120 / 0 | 1160 / 288 | `0x0040` (REGULAR only) | ✔ |
| noto-sans-sc, both chunks (Google)  | 1000 | 1160 / -288 / 0 | 880 / -120 / 0 | 1160 / 288 | `0x0040` (REGULAR only) | ✔ |

**Result: for the current shipped builds, `hhea.ascent/descent/lineGap`, `OS/2.sTypoAscender/
Descender/LineGap`, `OS/2.usWinAscent/Descent`, and `OS/2.fsSelection` are bit-for-bit identical
between Google Fonts' Noto Serif/Sans TC (and SC) and Adobe's Source Han Serif/Sans TC**, at Regular
weight. `USE_TYPO_METRICS` (fsSelection bit 7) is **off** in both, on both sides.

### BASE table content

`BASE` horizontal-axis default baseline coordinates (script `DFLT`, coordinate values in font units,
1000 upm):

| file | icfb | icft | ideo | romn |
|---|---|---|---|---|
| SourceHanSerifTC-Regular (Adobe) | -78 | 838 | -120 | 0 |
| noto-serif-tc (Google)           | -79 | 839 | -120 | 0 |
| SourceHanSansTC-Regular (Adobe)  | -74 | 834 | -120 | 0 |
| noto-sans-tc (Google)            | -78 | 838 | -120 | 0 |

There is a small, real discrepancy here: 1 unit (Serif) to 4 units (Sans) out of 1000 units-per-em.
At 64px that is ≤0.26px — below what's visible, and (per §5's controlled experiment) `BASE` doesn't
drive line-height or the default alphabetic-baseline position in ordinary horizontal text layout
anyway. This is recorded as a genuine, measured difference, but it is **not** large enough to explain
a visible baseline shift.

### `name` table anomaly (verified, unrelated to metrics)

Every one of the four Google Fonts Regular-weight files checked has an internal name table
(nameID 1/2/4/6) that does **not** say "Regular":

| Google file (CSS says `font-weight: 400`, `usWeightClass` is correctly `400`) | nameID 1 (family) | nameID 4 (full name) | nameID 6 (PostScript name) |
|---|---|---|---|
| Noto Serif TC | `Noto Serif TC ExtraLight` | `Noto Serif TC ExtraLight Regular` | `NotoSerifTCExtraLight-Regular` |
| Noto Sans TC  | `Noto Sans TC Thin` | `Noto Sans TC Thin Regular` | `NotoSansTCThin-Regular` |
| Noto Serif SC | `Noto Serif SC ExtraLight` | `Noto Serif SC ExtraLight Regular` | `NotoSerifSCExtraLight-Regular` |
| Noto Sans SC  | `Noto Sans SC Thin` | `Noto Sans SC Thin Regular` | `NotoSansSCThin-Regular` |

This was double-checked against the CSS: the exact same URL is served under
`font-family: 'Noto Serif TC'; font-weight: 400;` in the CSS response (see `data/google-noto-serif-tc.css`,
first `@font-face` block). `usWeightClass` inside the font is `400`. So the font correctly *behaves*
as Regular/400 (browsers go by the CSS `@font-face` descriptor + `usWeightClass`, not by the vanity
name string), but its self-reported name metadata is wrong — almost certainly leftover naming from
whichever named instance of Google's internal variable-font source was used to cut this static weight.
This is a real, confirmed, and easily reproduced anomaly. **It has no mechanical effect on line-height
or baseline** (name table isn't consulted for layout), so it is reported here as a distinct, notable
finding, not as an explanation for baseline/line-height differences.

### `cmap` coverage

Google's chunk files each cover a few hundred code points (a 256-code-point `unicode-range` slice, or
fewer/more depending on how many of the codepoints in that block actually have glyphs); Adobe's
originals cover the font's full Pan-CJK repertoire (~42,000+ codepoints via `cmap_format_12`). This is
exactly what a deliberate unicode-range-chunked CDN delivery is supposed to look like — it is
subsetting-by-design, not an anomalous or unexpected loss of coverage.

## 4. Google Fonts CSS descriptors

Checked all four CSS responses for `ascent-override`, `descent-override`, `line-gap-override`,
`size-adjust`: **none of these descriptors appear anywhere in any of the four CSS files** (`grep -c
override` → 0 in all four). Google is not compensating for any metrics mismatch at the CSS level for
these families. `font-display: swap` is present on every block; `font-style: normal` throughout (this
investigation only requested weight 400 normal style).

## 5. Repro page + measurements

`repro/index.html` (served locally over HTTP, screenshotted/measured with Playwright + the
pre-installed Chromium) renders 4 sources × 3 test strings × 3 line-heights. (An earlier version had
a 5th "Google Fonts CDN, live network" source; see the erratum at the top of this document for why it
was removed — it was not actually rendering Noto Serif TC.)

1. The Google woff2 bytes downloaded in §1.1, self-hosted locally via the same `unicode-range`
   chunking Google uses (byte-identical to the `fonts.gstatic.com` originals, verified by SHA-256 in
   `data/sha256.tsv`)
2. Adobe Source Han Serif TC compiled straight to WOFF2, no subsetting (all tables/glyphs kept)
3. Adobe original run through `pyftsubset` with `--layout-features='*' --name-IDs='*'
   --drop-tables-=BASE` (explicit "keep everything relevant")
4. Adobe original run through `pyftsubset` with only `--text=... --flavor=woff2` (bare defaults)

Screenshots: `repro/screenshots/variant-*.png`, `repro/screenshots/index-full.png`.

Canvas ink-bounding-box measurements (`data/measure-index.json`, alphabetic baseline at fixed y,
64px), for `你好臺灣漢字測試`:

| source | ink top (px from baseline) | ink bottom (px from baseline) | ink height (px) |
|---|---|---|---|
| Google self-hosted (verified same bytes as fonts.gstatic.com) | -55 | 5 | 61 |
| Adobe full | -55 | 6 | 62 |
| Adobe subset (tables kept) | -55 | 6 | 62 |
| Adobe subset (default) | -55 | 6 | 62 |

All four sources put the **top** of the ink at the same pixel row (-55). The **bottom** for the
Google file is 1px higher than all three Adobe-derived variants (5 vs 6, out of ~61-62px ink height,
i.e. ~1.6%) — consistent with the TrueType-vs-CFF outline/rounding difference noted in §2, and with
the ≤4/1000-em `BASE` coordinate rounding noted in §3. This was visually confirmed in the screenshots:
at normal reading distance the four renderings are not distinguishable by eye (see
`variant-gf-selfhost.png` vs `variant-adobe-full.png`). **This 1px difference is not a line-height
difference and not a whole-line baseline shift** — it's within-glyph ink-extent noise, an order of
magnitude smaller than anything a reader would notice.

## 6. Per-character glyph-ink verification (does chunking cause misalignment, and is chunk-splitting even the right suspect?)

A reviewer looking at an earlier (since-corrected — see erratum) screenshot pointed out that within a
single rendered line — one `font-family`, one weight, one line — "你好" and "臺灣漢字" visibly do not
line up: some characters look like they sit higher or lower than others. That is a real, correct
visual observation about CJK text rendering in general, worth checking directly rather than waving
away, because Google Fonts serves Noto Serif TC as ~108 separate `unicode-range` chunk files (§1.1) —
if two chunks were built or hinted inconsistently, that would show up exactly as within-line vertical
misalignment between characters from different chunks, and would be a genuinely different bug from
anything in §2/§3 (which only looked at whole-font tables, not per-glyph vertical placement).

Investigating this is what surfaced the bug described in the erratum: the first attempt at this test
compared "live Google Fonts CDN" against the Adobe original and found **suspiciously perfect,
pixel-identical** results for every character — which in hindsight was the tell that the "CDN" side
wasn't actually Noto Serif TC (it was the WenQuanYi Zen Hei fallback, which is a coincidence-free,
character-for-character match to itself, not to Adobe). Redone correctly, using the self-hosted
Google woff2 bytes (verified identical to `fonts.gstatic.com` via SHA-256) against the Adobe original
— `repro/per-char.html`, full data in `data/per-char.json`, screenshot `repro/screenshots/per-char.png`:

`你`/`好`/`字`/`灣` are served from chunk `.122`, `漢` from chunk `.117`, `臺` from chunk `.119`, and
`測`/`試` from two further chunks not separately isolated in this test — four-plus different files
(see `scripts/parse_css_ranges.py` output), all loaded together in one `font-family` in
`repro/per-char.html` exactly as Google's CSS declares them.

| char | chunk | Google self-hosted top / bottom (px) | Adobe original top / bottom (px) | diff |
|---|---|---|---|---|
| 你 | .122 | -54 / 4 | -54 / 5 | 1px (bottom) |
| 好 | .122 | -55 / 4 | -55 / 5 | 1px (bottom) |
| 臺 | .119 | -54 / 1 | -55 / 2 | 1px (both) |
| 灣 | .122 | -54 / 5 | -55 / 5 | 1px (top) |
| 漢 | .117 | -54 / 5 | -55 / 6 | 1px (both) |
| 字 | .122 | -54 / 5 | -54 / 5 | 0 |
| 測 | — | -54 / 4 | -54 / 5 | 1px (bottom) |
| 試 | — | -54 / 4 | -54 / 5 | 1px (bottom) |
| H (Latin, for scale) | — | -47 / -1 | -47 / -1 | 0 |
| g (Latin, for scale) | — | -34 / 16 | -34 / 16 | 0 |

Every character is within 0-1px of the Adobe original, with **no correlation between which chunk a
character came from and the size of the (tiny) discrepancy** — `字` (chunk `.122`, same chunk as
`你`/`好`/`灣`) matches exactly, while `你`/`好`/`灣` (same chunk) each show a 1px difference on one
side. So:

- **Chunking is not the cause of anything visible.** If splitting the font into per-unicode-range
  files introduced inconsistent vertical placement, characters from the same chunk would move
  together and characters from different chunks would move independently; instead the ≤1px
  differences look like ordinary rounding noise scattered without regard to which chunk each
  character came from.
- **The visual unevenness a reader sees between "你好" and "臺灣漢字" is real, but it is a property of
  the glyph designs themselves — present identically in Google's font and in Adobe's original.**
  `好`'s ink descends 4-5px below baseline while `臺`'s only descends 1-2px — a gap on the same order
  as the 17px gap between Latin `g` (descends 16px) and `H` (does not descend, -1px). Nobody reads
  Latin `g`/`H` unevenness as a font bug; the same design logic (uneven ink distribution within the
  em-box, character by character) applies to CJK ideographs too, and both fonts show it the same way.
- This finding is **consistent with, not contradicting,** §3's conclusion that Google's and Adobe's
  whole-font metrics (`hhea`/`OS/2`/`BASE`) match almost exactly (the ≤4/1000-em `BASE` rounding noted
  there shows up here as the ≤1px per-glyph noise) — it adds a second, independent, per-glyph
  confirmation using genuinely verified files this time.

## 7. Controlled pyftsubset variable-isolation experiment (§8 of the task)

`repro/measure.html` isolates each candidate variable individually, starting from the Adobe Source
Han Serif TC Regular original:

| variant | what changed | measured line-box height (`line-height: normal`, 64px) | ink bbox |
|---|---|---|---|
| Adobe-Full | nothing (reference) | 92px | top -55 / bottom 16 |
| A: pyftsubset default | `pyftsubset --text=... --flavor=woff2` only | 92px | top -55 / bottom 16 |
| B: pyftsubset, BASE kept explicitly | `--drop-tables-=BASE` | 92px | top -55 / bottom 16 |
| C: pyftsubset, BASE dropped | `--drop-tables+=BASE` | 92px | top -55 / bottom 16 |
| D: hhea/OS2 metrics altered | hhea 1000/-400/200, OS/2 typo 1000/-400/200, usWin 1200/500 | **103px** | top -55 / bottom 16 |
| E: USE_TYPO_METRICS set (OS/2 v3) | `fsSelection \|= 0x80`, OS/2 version left at 3 | **64px** | top -55 / bottom 16 |
| E2: USE_TYPO_METRICS set (OS/2 v4) | same as E but OS/2 version bumped to 4 | **64px** | top -55 / bottom 16 |

Screenshot: `repro/screenshots/measure-full.png` (the highlighted background box around each sample
directly visualizes the measured line-box height — E/E2 are visibly tighter).

This isolates the causes precisely, in Chromium (via Playwright), for horizontal Latin+CJK mixed text:

- **Removing `BASE` (variant C) changed nothing.** Line-box height and ink position were identical
  to keeping it (A, B) and to the untouched original (Adobe-Full). In this test, `BASE` table
  presence/absence has **no measurable effect** on default line-height or on the alphabetic-baseline
  position of horizontal text in Chromium. (`BASE` matters for explicit cross-script baseline
  alignment — e.g. `dominant-baseline`/vertical writing modes/ruby — which this test does not
  exercise.)
- **Changing `hhea`/`OS/2` typo metrics (variant D) changed the line-box height** from 92px to 103px,
  exactly as expected — this is the mechanism that actually controls `line-height: normal`.
- **Setting `USE_TYPO_METRICS` (E, E2) changed the line-box height to exactly 64px** — i.e. exactly
  1 em (`sTypoAscender` 880 + `|sTypoDescender|` 120 + `sTypoLineGap` 0 = 1000 units = 1 em). This
  confirms Chromium honors the bit and switches its line-height source from `hhea` to `OS/2` typo
  metrics when it's set, and that this took effect even with `OS/2.version` left at 3 (E), not just
  after bumping it to 4 (E2) — contrary to a naive reading of the spec (`USE_TYPO_METRICS` is
  formally only defined for `OS/2` version ≥ 4).
- Ink bbox (top -55/bottom 16 throughout D and E) did **not** move with any of these table-level
  edits — glyph ink position is fixed by the glyph outlines, not by `hhea`/`OS/2`/`BASE`, and none of
  A-E2 touched the outlines.

## 8. Answers to the specific verification checklist

| Question | Answer |
|---|---|
| Does the Google woff2 have `OS/2`, `hhea`, `BASE`, `vhea`, `vmtx`, `name`, `cmap`, `head`, `maxp`, `GSUB`, `GPOS`? | Yes, all of them, in every chunk checked. |
| Does the Adobe original have the same tables? | Yes, same list, plus `CFF`/`VORG`/`DSIG` (CFF-flavored) instead of `glyf`/`loca`/`STAT`/`prep`/`gasp` (Google's TrueType-flavored, variable-font-derived build). |
| `head.unitsPerEm` | 1000 on both sides, all four families. |
| `hhea.ascent/descent/lineGap` | Identical between Google (current build) and Adobe (current release): Serif 1151/-286/0, Sans 1160/-288/0. |
| `OS/2.sTypoAscender/Descender/LineGap` | Identical: 880/-120/0 on both sides, both families. |
| `OS/2.usWinAscent/Descent` | Identical: Serif 1151/286, Sans 1160/288. |
| `OS/2.fsSelection`, `USE_TYPO_METRICS` bit | Identical: `0x0040`, bit 7 (`USE_TYPO_METRICS`) is **off** on both sides. |
| Does `BASE` exist? | Yes, in every file checked (Google and Adobe alike). |
| Is `BASE` content identical? | Nearly — DFLT-script coordinates differ by 1 unit (Serif) to 4 units (Sans) out of 1000 upm. Not visually significant, confirmed by experiment (§7) to have zero effect on this test's line-height/baseline. |
| `name` table family/subfamily/full/PostScript name | CSS-visible family name (`Noto Serif TC` / `Noto Sans TC`, weight 400) is correct; the font's **internal** RIBBI name strings (nameID 1/2/4/6) incorrectly say "ExtraLight"/"Thin" for all four Regular-weight Google families tested — a real, confirmed cosmetic bug, unrelated to metrics. |
| Is `cmap` coverage just differently-sized subsetting, or anomalous loss? | Ordinary unicode-range-chunked subsetting; no anomalous gaps found for the codepoints tested. |
| Google Fonts CSS: `ascent-override`/`descent-override`/`line-gap-override`/`size-adjust`? | None present in any of the four CSS responses. |

## 9. Conclusions

1. For the **currently shipped** builds (`v36`/`v39` Google Fonts CSS vs Adobe `2.003R`/`2.005R`
   release-branch OTFs), Google Fonts' Noto Serif TC/Sans TC (and SC) are **identical** to Adobe's
   Source Han Serif TC/Sans TC on `head.unitsPerEm`, `hhea.ascent/descent/lineGap`,
   `OS/2.sTypoAscender/Descender/LineGap`, `OS/2.usWinAscent/Descent`, and `OS/2.fsSelection`
   (including the `USE_TYPO_METRICS` bit, which is off on both sides). They differ in SFNT outline
   flavor (CFF vs TrueType-from-variable-font) and in trivial (≤4/1000 em) `BASE` coordinate rounding.
2. Google Fonts WOFF2 **does** contain a `BASE` table — in all four families and in both the Latin
   and CJK chunks checked. No missing-`BASE` case was found.
3. Google Fonts WOFF2's `OS/2`/`hhea` metrics **are** identical to the Source Han originals, for the
   Regular weight of TC/SC Serif and Sans, as shipped today.
4. In this investigation's own controlled test (§7), default `line-height: normal` differences are
   caused **exclusively** by actual differences in `hhea`/`OS/2` typo metric values or by the
   `USE_TYPO_METRICS` bit — not by `BASE` table presence. Since Google's current build and Adobe's
   current original carry identical `hhea`/`OS/2`/`fsSelection` values for this weight/family
   combination, **no line-height difference is predicted or was observed between them** in this test.
   If a user has observed a visible line-height difference in production between "Noto Serif/Sans TC
   via Google Fonts" and "Source Han Serif/Sans TC self-hosted," the most likely explanations —
   **not directly tested here** — are: (a) an older, previously-shipped Google Fonts build with
   different metrics (Google's CSS build tags go up to v36/v39, implying many prior revisions not
   examined in this investigation), (b) comparison against a different weight/style than Regular 400,
   or (c) a different actual fallback font being rendered because the intended web font failed to load
   for the *user's* browser (network failure, ad blocker, corporate proxy, CSP, etc.) and the browser
   silently substituted whatever CJK-capable system font it could find. This last scenario is not
   hypothetical: §6's erratum documents this investigation accidentally reproducing exactly this
   failure mode in its own test harness (Chromium in this sandbox silently substituted an unrelated
   system font, `WenQuanYi Zen Hei`, when the real network request failed) — which is direct, if
   incidental, proof that "the font that actually rendered wasn't the one requested" is a real,
   easy-to-miss failure mode for this kind of comparison, worth checking for in any report of a
   Google-Fonts-vs-self-hosted visual difference before concluding the two font *files* differ.
5. **Baseline** (vertical ink position within the line) differences: this investigation measured a
   small (1px out of ~60-62px ink height, i.e. ~1.6%) discrepancy in ink extent between the verified
   self-hosted Google woff2 (byte-identical to `fonts.gstatic.com`, confirmed by SHA-256) and the
   Adobe-derived files, scattered across top/bottom with no correlation to which `unicode-range` chunk
   a character came from (§6). This is far too small to be a "disaster"-level visual defect, is not
   explained by any `hhea`/`OS/2` field (all of which matched exactly, per §3), and is most plausibly
   attributable to the CFF-vs-TrueType outline/rounding difference documented in §2 and/or the
   ≤4/1000-em `BASE` coordinate rounding documented in §3 — **this attribution is a plausible
   correlation, not a proven causal mechanism**; isolating it further would require diffing the actual
   glyph outlines/hints, which this investigation did not do.
6. Actionable mitigations (independent of whether they're needed for the *current* builds, since this
   investigation found no live metrics mismatch for Regular/400 TC/SC):
   - **CSS metrics override**: if a real mismatch is ever found (e.g., against an older cached Google
     Fonts build, or a non-Regular weight/style not tested here), `size-adjust` /
     `ascent-override` / `descent-override` / `line-gap-override` on the `@font-face` rule for
     whichever family renders "too tall/short" is the standard, no-rebuild fix — confirmed workable
     in principle by this investigation's variant D/E experiment, which shows the browser's line-box
     height is a direct, controllable function of exactly these values.
   - **Self-hosted subsetting**: `pyftsubset` does **not** need any special flag to retain `BASE`,
     `OS/2`, or `hhea` — its default `drop_tables` list (`JSTF, DSIG, EBDT, EBLC, EBSC, PCLT, LTSH,
     Feat, Glat, Gloc, Silf, Sill`) does not include any of them. A bare
     `pyftsubset font.otf --text=... --flavor=woff2` already preserves `BASE`/`OS/2`/`hhea` unchanged
     (verified: variant A above is byte-identical to variant B, which explicitly forces `BASE` to be
     kept).
   - **`USE_TYPO_METRICS`**: only relevant as a fix if `hhea` and `OS/2` typo metrics genuinely
     disagree in a specific font build being served — for the files examined here they don't, so
     flipping this bit would not currently change anything visible. If it is ever needed, this
     investigation confirms (variant E, `OS/2.version` left at 3) that Chromium honors the bit even
     without bumping `OS/2.version` to 4, contrary to a literal reading of the OpenType spec's
     "defined for version ≥ 4" language.

## 10. What this report does NOT claim

- It does not claim anything about weights other than Regular/400, or about italic/oblique styles.
- It does not claim anything about older/historical Google Fonts builds — only the `v36`/`v39`/`v35`/
  `v40` CSS responses fetched on 2026-07-04 were examined.
- It does not claim to have isolated the exact cause of the ~3-4px ink-bottom discrepancy in §5/§7 —
  that is reported as a measured fact with a plausible (outline-flavor) explanation, explicitly marked
  unproven.
- It does not cite Wikipedia, Grokipedia, or any GitHub issue content as evidence — `google/fonts#8911`
  and the Adobe issue trackers named in the task brief were not fetched (GitHub web/API access was
  blocked by this environment's egress policy; `raw.githubusercontent.com` file fetches were used
  instead, which only serve raw repository file content, not issues/PRs).

## Repro instructions (for an independent reviewer)

```bash
cd research
pip install fonttools brotli zopfli
bash scripts/fetch-google-fonts.sh          # downloads data/google-*.css + fonts/google/**/*.woff2
bash scripts/dump-font-tables.sh            # regenerates data/tables.tsv from work/rep/*
python3 scripts/compare-metrics.py work/ttx-dumps   # regenerates data/metrics.tsv

# Adobe originals (raw.githubusercontent.com, not github.com):
curl -sL -o fonts/adobe/SourceHanSerifTC-Regular.otf \
  'https://raw.githubusercontent.com/adobe-fonts/source-han-serif/release/OTF/TraditionalChinese/SourceHanSerifTC-Regular.otf'
curl -sL -o fonts/adobe/SourceHanSansTC-Regular.otf \
  'https://raw.githubusercontent.com/adobe-fonts/source-han-sans/release/OTF/TraditionalChinese/SourceHanSansTC-Regular.otf'

# repro page + Playwright measurement:
(cd repro && python3 -m http.server 8931 &)
NODE_PATH=/opt/node22/lib/node_modules node scripts/screenshot.js
```
