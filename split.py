#!/usr/bin/env python3
"""
Prepare the dist/jigmo/ deployment directory.

Copies all built fonts (jigmo-*, sht-*, ss4-*) and the landing page into
dist/jigmo/, ready for a single Cloudflare Pages deployment.

Cloudflare Pages limit is 25 MB *per file*; total deployment size is not
capped, so a single project covers all fonts.

Usage:
    python split.py [--clean]

Then deploy:
    wrangler pages deploy dist/jigmo --project-name jigmo --branch main
"""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
FONTS_DIR = ROOT / "fonts"
DIST = ROOT / "dist" / "jigmo"


def build(clean: bool):
    if clean and DIST.exists():
        shutil.rmtree(DIST)
        print("Cleaned dist/jigmo/")

    fonts_out = DIST / "fonts"
    fonts_out.mkdir(parents=True, exist_ok=True)

    # Copy all woff2 files into one flat fonts/ directory
    woff2_files = sorted(FONTS_DIR.glob("*.woff2"))
    for woff2 in woff2_files:
        shutil.copy2(woff2, fonts_out / woff2.name)

    total_mb = sum(f.stat().st_size for f in fonts_out.glob("*.woff2")) / 1024 / 1024
    print(f"dist/jigmo/fonts  {len(woff2_files)} files  {total_mb:.1f} MB")

    # Copy CSS (URLs are already relative — no rewriting needed)
    css_src = ROOT / "jigmo.css"
    if not css_src.exists():
        print("jigmo.css not found — run build.py first")
        return
    shutil.copy2(css_src, DIST / "jigmo.css")
    n_rules = css_src.read_text(encoding="utf-8").count("@font-face")
    size_kb = css_src.stat().st_size // 1024
    print(f"dist/jigmo/jigmo.css  ({n_rules} @font-face rules, {size_kb} KB)")

    # Copy landing page
    html_src = ROOT / "index.html"
    if html_src.exists():
        shutil.copy2(html_src, DIST / "index.html")
        print("dist/jigmo/index.html")

    print(f"\nDeploy with:")
    print(f"  wrangler pages deploy dist/jigmo --project-name jigmo --branch main")
    print(f"\nThen reference in your site:")
    print(f"  <link rel=\"stylesheet\" href=\"https://jigmo.digitalhumanities.dev/jigmo.css\">")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--clean", action="store_true", help="Delete dist/jigmo/ before building")
    args = ap.parse_args()
    build(clean=args.clean)


if __name__ == "__main__":
    main()
