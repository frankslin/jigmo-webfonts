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


def build_font(ttf_name: str, force: bool, jobs: int) -> list[str]:
    ttf_path = SRC_DIR / ttf_name
    if not ttf_path.exists():
        print(f"  WARNING: {ttf_name} not found, skipping.")
        return []

    print(f"\n── {ttf_name} {'─' * (50 - len(ttf_name))}")
    all_cps = scan_cmap(ttf_path)
    print(f"  Cmap: {len(all_cps):,} codepoints")

    chunk_map: dict[int, set[int]] = {}
    for cp in all_cps:
        chunk_start = (cp // CHUNK_SIZE) * CHUNK_SIZE
        chunk_map.setdefault(chunk_start, set()).add(cp)

    print(f"  Chunks with glyphs: {len(chunk_map)}")
    FONTS_DIR.mkdir(exist_ok=True)

    # Determine which chunks need (re)building
    tasks = []
    skip_count = 0
    for chunk_start, cps in sorted(chunk_map.items()):
        out_path = FONTS_DIR / f"jigmo-{chunk_start:06x}.woff2"
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

    # Generate (chunk_name, css_rule) pairs for all chunks in this font
    result = []
    for chunk_start in sorted(chunk_map):
        chunk_name = f"jigmo-{chunk_start:06x}.woff2"
        rule = (
            "@font-face {\n"
            "  font-family: 'Jigmo';\n"
            "  font-style: normal;\n"
            "  font-weight: 400;\n"
            "  font-display: swap;\n"
            f"  src: url('fonts/{chunk_name}') format('woff2');\n"
            f"  unicode-range: {unicode_range_str(chunk_start)};\n"
            "}"
        )
        result.append((chunk_name, rule))
    return result


def build_all(force: bool, jobs: int):
    seen: set[str] = set()   # deduplicate by chunk name (first TTF wins)
    all_rules: list[str] = []
    for ttf_name in FONT_FILES:
        for chunk_name, rule in build_font(ttf_name, force=force, jobs=jobs):
            if chunk_name not in seen:
                seen.add(chunk_name)
                all_rules.append(rule)

    header = (
        "/* Jigmo Webfonts — chunked woff2 for CJK ideograph display\n"
        " * Generated by build.py — do not edit manually.\n"
        " * Font: Jigmo (CC0 1.0)  https://kamichikoichi.github.io/jigmo/\n"
        " * Chunk size: 256 codepoints (U+xx00–U+xxFF per file)\n"
        " */\n\n"
    )
    CSS_PATH.write_text(header + "\n\n".join(all_rules) + "\n", encoding="utf-8")
    print(f"\nCSS → {CSS_PATH}  ({len(all_rules)} @font-face rules)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-dl", action="store_true", help="Skip download step")
    ap.add_argument("--force", action="store_true", help="Rebuild existing chunk files")
    ap.add_argument("--jobs", type=int, default=cpu_count(), metavar="N",
                    help=f"Parallel workers (default: {cpu_count()})")
    args = ap.parse_args()

    if not args.no_dl:
        download_jigmo()

    build_all(force=args.force, jobs=args.jobs)
    print("\nDone. Open index.html to preview.")


if __name__ == "__main__":
    main()
