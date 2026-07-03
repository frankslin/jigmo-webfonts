#!/usr/bin/env python3
"""
Split the built fonts/ directory into two Cloudflare Pages deployments:

  dist/jigmo/   — plane 2-3 chunks (Extension B–J, NOT covered by Source Han Serif)
                  This is the primary repo: rare ideographs that need Jigmo as fallback.

  dist/jigmo2/  — plane 0-1 chunks (URO + Extension A, covered by Source Han Serif TC)
                  Secondary / optional: common CJK coverage for systems without Source Han.

Both stay well under the 25 MiB Cloudflare Pages limit.

Usage:
    python split.py --jigmo  https://jigmo.digitalhumanities.dev \
                   --jigmo2 https://jigmo2.digitalhumanities.dev

Then deploy:
    wrangler pages deploy dist/jigmo  --project-name jigmo
    wrangler pages deploy dist/jigmo2 --project-name jigmo2
"""

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
FONTS_DIR = ROOT / "fonts"
DIST = ROOT / "dist"


def split(base_jigmo: str, base_jigmo2: str):
    base_jigmo = base_jigmo.rstrip("/")
    base_jigmo2 = base_jigmo2.rstrip("/")

    dist1 = DIST / "jigmo" / "fonts"
    dist2 = DIST / "jigmo2" / "fonts"
    dist1.mkdir(parents=True, exist_ok=True)
    dist2.mkdir(parents=True, exist_ok=True)

    # ── Distribute woff2 chunks ───────────────────────────────────────────
    for woff2 in sorted(FONTS_DIR.glob("*.woff2")):
        if woff2.stem.startswith("ss4-"):
            # Source Serif 4: only needed by jigmo (primary, has the landing page)
            shutil.copy2(woff2, dist1 / woff2.name)
            continue
        chunk_start = int(woff2.stem.split("-")[1], 16)
        # plane 2-3 (U+20000+): rare chars not covered by Source Han → jigmo (primary)
        # plane 0-1 (U+00000–U+1FFFF): common CJK covered by Source Han → jigmo2 (secondary)
        dest = dist1 if chunk_start >= 0x020000 else dist2
        shutil.copy2(woff2, dest / woff2.name)

    n1 = len(list(dist1.glob("*.woff2")))
    n2 = len(list(dist2.glob("*.woff2")))
    s1 = sum(f.stat().st_size for f in dist1.glob("*.woff2")) / 1024 / 1024
    s2 = sum(f.stat().st_size for f in dist2.glob("*.woff2")) / 1024 / 1024
    print(f"dist/jigmo/fonts   {n1:3d} files  {s1:.1f} MB")
    print(f"dist/jigmo2/fonts  {n2:3d} files  {s2:.1f} MB")

    # ── Rewrite CSS with absolute URLs ────────────────────────────────────
    css_src = ROOT / "jigmo.css"
    if not css_src.exists():
        print("jigmo.css not found — run build.py first")
        return

    original = css_src.read_text(encoding="utf-8")

    def rewrite_url(m: re.Match) -> str:
        chunk_name = m.group(1)
        if chunk_name.startswith("ss4-"):
            # SS4 fonts are served from jigmo (primary); keep relative URL
            return f"url('fonts/{chunk_name}')"
        chunk_start = int(chunk_name.split("-")[1].replace(".woff2", ""), 16)
        base = base_jigmo if chunk_start >= 0x020000 else base_jigmo2
        return f"url('{base}/fonts/{chunk_name}')"

    rewritten = re.sub(r"url\('fonts/([^']+\.woff2)'\)", rewrite_url, original)

    # Strip the generated-by block comment
    rewritten = re.sub(r"/\* Jigmo Webfonts.*?\*/\n\n", "", rewritten, flags=re.DOTALL)

    # Minify: collapse each @font-face block to one line
    rewritten = re.sub(r"\n  ", " ", rewritten)   # indent → space
    rewritten = re.sub(r"\n\}", "}", rewritten)    # closing brace
    rewritten = re.sub(r"\n\n+", "\n", rewritten)  # blank lines

    banner = (
        f"/* Jigmo Webfonts | jigmo.digitalhumanities.dev | CC0 1.0 | "
        f"Plane 2-3 (Ext B-J): {base_jigmo} | "
        f"Plane 0-1 (URO+ExtA): {base_jigmo2} */\n"
    )
    rewritten = banner + rewritten.lstrip()

    css_out = DIST / "jigmo" / "jigmo.css"
    css_out.write_text(rewritten, encoding="utf-8")
    size_kb = css_out.stat().st_size // 1024
    print(f"dist/jigmo/jigmo.css  ({rewritten.count('@font-face')} rules, minified, {size_kb} KB)")

    # ── Copy landing page (update CSS href to self-relative) ─────────────
    html_src = ROOT / "index.html"
    if html_src.exists():
        shutil.copy2(html_src, DIST / "jigmo" / "index.html")
        print("dist/jigmo/index.html")

    # jigmo2 is fonts-only; Cloudflare Pages requires at least one HTML file
    stub = (
        f'<!doctype html><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0;url={base_jigmo}">'
        f'<title>Jigmo Webfonts</title>'
        f'<p>Redirecting to <a href="{base_jigmo}">{base_jigmo}</a>…</p>'
    )
    (DIST / "jigmo2" / "index.html").write_text(stub, encoding="utf-8")
    print("dist/jigmo2/index.html  (stub)")

    print(f"\nDeploy with:")
    print(f"  wrangler pages deploy dist/jigmo  --project-name jigmo  --branch main")
    print(f"  wrangler pages deploy dist/jigmo2 --project-name jigmo2 --branch main")
    print(f"\nThen reference in your site:")
    print(f"  <link rel=\"stylesheet\" href=\"{base_jigmo}/jigmo.css\">")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jigmo",  default="https://jigmo.digitalhumanities.dev",  metavar="URL",
                    help="Base URL of the jigmo Pages project (plane 0-1)")
    ap.add_argument("--jigmo2", default="https://jigmo2.digitalhumanities.dev", metavar="URL",
                    help="Base URL of the jigmo2 Pages project (plane 2-3)")
    ap.add_argument("--clean", action="store_true", help="Delete dist/ before splitting")
    args = ap.parse_args()

    if args.clean and DIST.exists():
        shutil.rmtree(DIST)
        print("Cleaned dist/")

    split(args.jigmo, args.jigmo2)


if __name__ == "__main__":
    main()
