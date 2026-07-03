#!/usr/bin/env python3
"""
Build chunked woff2 + CSS for Jigmo webfonts.

Splits Jigmo.ttf / Jigmo2.ttf / Jigmo3.ttf into 256-codepoint woff2 chunks
so browsers download only the blocks they actually need via CSS unicode-range.

Usage:
    pip install -r requirements.txt
    python build.py              # download Jigmo + build all chunks
    python build.py --no-dl      # skip download (src/*.ttf already present)
    python build.py --force      # rebuild existing chunk files
    python build.py --jobs 4     # parallel workers (default: CPU count)
"""

import argparse
import logging
import re
import sys
import urllib.request
import zipfile
from multiprocessing import Pool, cpu_count
from pathlib import Path

from fontTools import subset as ft_subset
from fontTools.ttLib import TTFont

# Suppress fontTools chatter about unrecognised tables (e.g. FFTM from FontForge)
logging.getLogger("fontTools").setLevel(logging.ERROR)

# ── Config ─────────────────────────────────────────────────────────────────────

JIGMO_URL  = "https://kamichikoichi.github.io/jigmo/Jigmo-20250912.zip"
JIGMO_SHA1 = "2fb963ee7bba1d23ccfe81b228422f22da9dc574"
CHUNK_SIZE = 0x100  # 256 codepoints per chunk; matches Google's Noto CJK approach

SS4_API = (
    "https://fonts.googleapis.com/css2?family=Source+Serif+4:"
    "ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap"
)

# Source Han Serif TC — Regular only, common CJK blocks
SHT_URL  = "https://github.com/adobe-fonts/source-han-serif/releases/download/2.003R/10_SourceHanSerifTC.zip"
SHT_FILE = "SourceHanSerifTC-Regular.otf"
# Only chunk the blocks that matter for CBDB: CJK punctuation + URO
SHT_RANGES = [
    (0x3000, 0x303F),  # CJK Symbols and Punctuation（。，！？「」…）
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs (URO)
]

ROOT      = Path(__file__).parent
SRC_DIR   = ROOT / "src"
FONTS_DIR = ROOT / "fonts"
CSS_PATH  = ROOT / "jigmo.css"

FONT_FILES = ["Jigmo.ttf", "Jigmo2.ttf", "Jigmo3.ttf"]

# ── Download ───────────────────────────────────────────────────────────────────

def download_jigmo():
    SRC_DIR.mkdir(exist_ok=True)
    zip_path = SRC_DIR / "Jigmo.zip"

    if not zip_path.exists():
        print(f"Downloading {JIGMO_URL} …")
        urllib.request.urlretrieve(JIGMO_URL, zip_path)
        size_mb = zip_path.stat().st_size / 1024 / 1024
        print(f"  Saved {size_mb:.1f} MB → {zip_path}")

    missing = [f for f in FONT_FILES if not (SRC_DIR / f).exists()]
    if missing:
        print(f"Extracting {missing} …")
        with zipfile.ZipFile(zip_path) as zf:
            for entry in zf.namelist():
                name = Path(entry).name
                if name in FONT_FILES:
                    (SRC_DIR / name).write_bytes(zf.read(entry))
        print("  Done.")
    else:
        print("Source fonts already present, skipping extraction.")

# ── Core build ─────────────────────────────────────────────────────────────────

def scan_cmap(ttf_path: Path) -> set[int]:
    tt = TTFont(str(ttf_path), lazy=True)
    cmap = tt.getBestCmap()
    result = set(cmap.keys()) if cmap else set()
    tt.close()
    return result


def _build_chunk_worker(args: tuple) -> tuple[str, int]:
    """Worker function for multiprocessing: returns (chunk_name, file_size_bytes)."""
    ttf_path_str, codepoints, out_path_str = args
    out_path = Path(out_path_str)

    options = ft_subset.Options()
    options.flavor = "woff2"
    options.layout_features = []  # drop OT layout; not needed for display fallback
    options.name_IDs = [1, 2, 4]
    options.drop_tables += ["DSIG", "morx", "prop", "GDEF", "GPOS", "GSUB"]

    font = ft_subset.load_font(ttf_path_str, options)
    subsetter = ft_subset.Subsetter(options=options)
    subsetter.populate(unicodes=sorted(codepoints))
    subsetter.subset(font)
    ft_subset.save_font(font, out_path_str, options)
    font.close()

    return out_path.name, out_path.stat().st_size


def unicode_range_str(start: int) -> str:
    end = start + CHUNK_SIZE - 1
    if end <= 0xFFFF:
        return f"U+{start:04X}-U+{end:04X}"
    return f"U+{start:05X}-U+{end:05X}"


def in_ranges(cp: int, ranges: list[tuple[int, int]]) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def build_font(
    ttf_path: Path,
    prefix: str,
    family: str,
    force: bool,
    jobs: int,
    ranges: list[tuple[int, int]] | None = None,
) -> list[tuple[str, str]]:
    """Chunk a TTF/OTF into woff2 files and return (chunk_name, css_rule) pairs.

    ranges: optional list of (lo, hi) codepoint pairs to restrict coverage.
    """
    if not ttf_path.exists():
        print(f"  WARNING: {ttf_path.name} not found, skipping.")
        return []

    print(f"\n── {ttf_path.name} {'─' * (50 - len(ttf_path.name))}")
    all_cps = scan_cmap(ttf_path)
    if ranges:
        all_cps = {cp for cp in all_cps if in_ranges(cp, ranges)}
    print(f"  Cmap: {len(all_cps):,} codepoints" + (f" (filtered to {len(ranges)} range(s))" if ranges else ""))

    chunk_map: dict[int, set[int]] = {}
    for cp in all_cps:
        chunk_start = (cp // CHUNK_SIZE) * CHUNK_SIZE
        chunk_map.setdefault(chunk_start, set()).add(cp)

    print(f"  Chunks with glyphs: {len(chunk_map)}")
    FONTS_DIR.mkdir(exist_ok=True)

    tasks = []
    skip_count = 0
    for chunk_start, cps in sorted(chunk_map.items()):
        out_path = FONTS_DIR / f"{prefix}-{chunk_start:06x}.woff2"
        if out_path.exists() and not force:
            skip_count += 1
        else:
            tasks.append((str(ttf_path), cps, str(out_path)))

    if skip_count:
        print(f"  Skipping {skip_count} existing chunks (use --force to rebuild).")

    if tasks:
        print(f"  Building {len(tasks)} chunks with {jobs} worker(s) …")
        with Pool(processes=jobs) as pool:
            for i, (chunk_name, size) in enumerate(pool.imap_unordered(_build_chunk_worker, tasks), 1):
                if i % 50 == 0 or i == len(tasks):
                    print(f"  [{i:4d}/{len(tasks)}] {chunk_name}  {size // 1024} KB")

    result = []
    for chunk_start in sorted(chunk_map):
        chunk_name = f"{prefix}-{chunk_start:06x}.woff2"
        rule = (
            "@font-face {\n"
            f"  font-family: '{family}';\n"
            "  font-style: normal;\n"
            "  font-weight: 400;\n"
            "  font-display: swap;\n"
            f"  src: url('fonts/{chunk_name}') format('woff2');\n"
            f"  unicode-range: {unicode_range_str(chunk_start)};\n"
            "}"
        )
        result.append((chunk_name, rule))
    return result


def download_source_serif_4() -> str:
    """Download Source Serif 4 woff2 files from Google Fonts; return self-hosted CSS block."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    req = urllib.request.Request(SS4_API, headers=headers)
    css = urllib.request.urlopen(req).read().decode("utf-8")

    FONTS_DIR.mkdir(exist_ok=True)
    url_to_fname: dict[str, str] = {}
    counter = [0]

    def _rewrite(m: re.Match) -> str:
        url = m.group(1).strip("'\"")
        if url not in url_to_fname:
            counter[0] += 1
            fname = f"ss4-{counter[0]:02d}.woff2"
            dest = FONTS_DIR / fname
            if not dest.exists():
                print(f"  Downloading {fname} …")
                urllib.request.urlretrieve(url, dest)
            url_to_fname[url] = fname
        return f"url('fonts/{url_to_fname[url]}')"

    local_css = re.sub(r"url\(([^)]+)\)", _rewrite, css)
    n = counter[0]
    print(f"  Source Serif 4: {n} woff2 file(s) cached in fonts/")
    header = "/* Source Serif 4 — self-hosted (OFL-1.1), fetched from Google Fonts API */\n\n"
    return header + local_css


def download_source_han_serif_tc() -> Path:
    """Download Source Han Serif TC Regular OTF; return local path."""
    SRC_DIR.mkdir(exist_ok=True)
    dest = SRC_DIR / SHT_FILE
    if dest.exists():
        print(f"  {SHT_FILE} already present, skipping download.")
        return dest

    zip_path = SRC_DIR / "SourceHanSerifTC.zip"
    if not zip_path.exists():
        print(f"  Downloading Source Han Serif TC …")
        urllib.request.urlretrieve(SHT_URL, zip_path)
        size_mb = zip_path.stat().st_size / 1024 / 1024
        print(f"  Saved {size_mb:.1f} MB → {zip_path}")

    print(f"  Extracting {SHT_FILE} …")
    with zipfile.ZipFile(zip_path) as zf:
        matches = [e for e in zf.namelist() if Path(e).name == SHT_FILE]
        if not matches:
            raise FileNotFoundError(
                f"{SHT_FILE} not found in zip. Entries: {zf.namelist()[:20]}"
            )
        dest.write_bytes(zf.read(matches[0]))
    print(f"  → {dest}")
    return dest


def build_all(force: bool, jobs: int, no_ss4: bool = False, no_sht: bool = False):
    seen: set[str] = set()   # deduplicate by chunk name (first TTF wins)
    all_rules: list[str] = []
    for ttf_name in FONT_FILES:
        for chunk_name, rule in build_font(
            SRC_DIR / ttf_name, prefix="jigmo", family="Jigmo", force=force, jobs=jobs
        ):
            if chunk_name not in seen:
                seen.add(chunk_name)
                all_rules.append(rule)

    sht_rules: list[str] = []
    if not no_sht:
        sht_path = download_source_han_serif_tc()
        for chunk_name, rule in build_font(
            sht_path, prefix="sht", family="Source Han Serif TC",
            force=force, jobs=jobs, ranges=SHT_RANGES,
        ):
            if chunk_name not in seen:
                seen.add(chunk_name)
                sht_rules.append(rule)

    ss4_css = "" if no_ss4 else download_source_serif_4()

    header = (
        "/* Jigmo Webfonts — chunked woff2 for CJK ideograph display\n"
        " * Generated by build.py — do not edit manually.\n"
        " * Font: Jigmo (CC0 1.0)  https://kamichikoichi.github.io/jigmo/\n"
        " * Chunk size: 256 codepoints (U+xx00–U+xxFF per file)\n"
        " */\n\n"
    )
    sht_css = ""
    if sht_rules:
        sht_css = (
            "/* Source Han Serif TC — self-hosted (OFL-1.1), common CJK blocks only */\n\n"
            + "\n\n".join(sht_rules) + "\n\n"
        )
    content = header + ss4_css + sht_css + "\n\n".join(all_rules) + "\n"
    CSS_PATH.write_text(content, encoding="utf-8")
    total = len(all_rules) + len(sht_rules)
    print(f"\nCSS → {CSS_PATH}  ({total} @font-face rules)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-dl",  action="store_true", help="Skip Jigmo download step")
    ap.add_argument("--no-ss4", action="store_true", help="Skip Source Serif 4 download")
    ap.add_argument("--no-sht", action="store_true", help="Skip Source Han Serif TC download/build")
    ap.add_argument("--force",  action="store_true", help="Rebuild existing chunk files")
    ap.add_argument("--jobs", type=int, default=cpu_count(), metavar="N",
                    help=f"Parallel workers (default: {cpu_count()})")
    args = ap.parse_args()

    if not args.no_dl:
        download_jigmo()

    build_all(force=args.force, jobs=args.jobs, no_ss4=args.no_ss4, no_sht=args.no_sht)
    print("\nDone. Open index.html to preview.")


if __name__ == "__main__":
    main()
