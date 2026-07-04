#!/usr/bin/env python3
"""
Prepare the dist/ deployment directory.

Copies CSS-referenced fonts (jigmo-*, shs-*, ss4-*) and the landing page into
dist/, ready for a single Cloudflare Pages deployment.

Cloudflare Pages limit is 25 MB *per file*; total deployment size is not
capped, so a single project covers all fonts.

Usage:
    python split.py [--clean]
    npm run build

Then deploy:
    wrangler pages deploy dist --project-name jigmo --branch main
"""

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
FONTS_DIR = ROOT / "fonts"
DIST = ROOT / "dist"
FONT_URL_RE = re.compile(r"url\((['\"]?)fonts/([^)'\"\s]+\.woff2)\1\)")


def referenced_fonts(css_files: list[Path]) -> list[str]:
    font_names: set[str] = set()
    for css_src in css_files:
        css_text = css_src.read_text(encoding="utf-8")
        font_names.update(match.group(2) for match in FONT_URL_RE.finditer(css_text))
    return sorted(font_names)


def build(clean: bool):
    if clean and DIST.exists():
        shutil.rmtree(DIST)
        print("Cleaned dist/")

    fonts_out = DIST / "fonts"
    fonts_out.mkdir(parents=True, exist_ok=True)

    # Copy CSS files first; URLs are already relative, so no rewriting is needed.
    css_files = sorted(ROOT.glob("jigmo*.css"))
    if not css_files:
        print("No jigmo*.css found — run build.py first")
        return

    font_names = referenced_fonts(css_files)
    missing = [font for font in font_names if not (FONTS_DIR / font).exists()]
    if missing:
        preview = ", ".join(missing[:8])
        more = f" (+{len(missing) - 8} more)" if len(missing) > 8 else ""
        raise FileNotFoundError(f"CSS references missing font files: {preview}{more}")

    for font_name in font_names:
        shutil.copy2(FONTS_DIR / font_name, fonts_out / font_name)

    total_mb = sum((fonts_out / font_name).stat().st_size for font_name in font_names) / 1024 / 1024
    print(f"dist/fonts  {len(font_names)} files  {total_mb:.1f} MB")

    for css_src in css_files:
        shutil.copy2(css_src, DIST / css_src.name)
        n_rules = css_src.read_text(encoding="utf-8").count("@font-face")
        size_kb = css_src.stat().st_size // 1024
        print(f"dist/{css_src.name}  ({n_rules} @font-face rules, {size_kb} KB)")

    # Copy landing page
    html_src = ROOT / "index.html"
    if html_src.exists():
        shutil.copy2(html_src, DIST / "index.html")
        print("dist/index.html")

    # Copy Cloudflare Pages headers config
    headers_src = ROOT / "_headers"
    if headers_src.exists():
        shutil.copy2(headers_src, DIST / "_headers")
        print("dist/_headers")

    print(f"\nDeploy with:")
    print(f"  wrangler pages deploy dist --project-name jigmo --branch main")
    print(f"\nThen reference in your site:")
    print(f"  <link rel=\"stylesheet\" href=\"https://jigmo.digitalhumanities.dev/jigmo.css\">")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--clean", action="store_true", help="Delete dist/ before building")
    args = ap.parse_args()
    build(clean=args.clean)


if __name__ == "__main__":
    main()
