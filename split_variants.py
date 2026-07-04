#!/usr/bin/env python3
"""
Prepare separate artifact directories for each CSS variant.

Each output directory contains one CSS file plus only the woff2 files that CSS
actually references. This is useful for publishing separate websites or npm
packages for the original, TC, and SC variants.

Usage:
    python split_variants.py [--clean]
    python split_variants.py --out dist-variants --with-site

Outputs:
    dist-variants/jigmo/
    dist-variants/jigmo-tc/
    dist-variants/jigmo-sc/
"""

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
FONTS_DIR = ROOT / "fonts"
DEFAULT_OUT = ROOT / "dist-variants"

VARIANTS = {
    "jigmo": {
        "css": "jigmo.css",
        "families": {"Source Serif 4", "Source Han Serif TC", "Jigmo"},
    },
    "jigmo-tc": {
        "css": "jigmo-tc.css",
        "families": {"Source Serif 4", "Source Han Serif TC", "Jigmo TC"},
    },
    "jigmo-sc": {
        "css": "jigmo-sc.css",
        "families": {"Source Serif 4", "Source Han Serif SC", "Jigmo SC"},
    },
}

FONT_URL_RE = re.compile(r"url\((['\"]?)(fonts/[^)'\"\s]+\.woff2)\1\)")
FONT_FACE_RE = re.compile(r"@font-face\s*\{[^{}]*\}", re.DOTALL)
FONT_FAMILY_RE = re.compile(r"font-family:\s*(['\"])(.*?)\1")


def referenced_fonts(css_text: str) -> list[str]:
    return sorted({Path(match.group(2)).name for match in FONT_URL_RE.finditer(css_text)})


def font_face_family(block: str) -> str | None:
    match = FONT_FAMILY_RE.search(block)
    return match.group(2) if match else None


def filtered_css(css_text: str, allowed_families: set[str]) -> str:
    first_block = FONT_FACE_RE.search(css_text)
    header = css_text[: first_block.start()].rstrip() if first_block else css_text.rstrip()
    kept_blocks = [
        block.group(0)
        for block in FONT_FACE_RE.finditer(css_text)
        if font_face_family(block.group(0)) in allowed_families
    ]
    if not kept_blocks:
        raise RuntimeError(f"No @font-face rules matched: {', '.join(sorted(allowed_families))}")
    family_list = ", ".join(sorted(allowed_families))
    package_header = f"/* Variant package: {family_list} */"
    return header + "\n\n" + package_header + "\n\n" + "\n\n".join(kept_blocks) + "\n"


def copy_optional(src_name: str, dest_dir: Path) -> None:
    src = ROOT / src_name
    if src.exists():
        shutil.copy2(src, dest_dir / src.name)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build_variant(name: str, css_name: str, allowed_families: set[str], out_root: Path, with_site: bool) -> None:
    css_src = ROOT / css_name
    if not css_src.exists():
        raise FileNotFoundError(f"{css_name} not found. Run build.py first.")

    source_css_text = css_src.read_text(encoding="utf-8")
    css_text = filtered_css(source_css_text, allowed_families)
    font_names = referenced_fonts(css_text)
    if not font_names:
        raise RuntimeError(f"No font URLs found in {css_name}")

    dest = out_root / name
    if dest.exists():
        shutil.rmtree(dest)
    fonts_dest = dest / "fonts"
    fonts_dest.mkdir(parents=True, exist_ok=True)

    missing = [font for font in font_names if not (FONTS_DIR / font).exists()]
    if missing:
        preview = ", ".join(missing[:8])
        more = f" (+{len(missing) - 8} more)" if len(missing) > 8 else ""
        raise FileNotFoundError(f"{css_name} references missing font files: {preview}{more}")

    (dest / css_src.name).write_text(css_text, encoding="utf-8")
    for font_name in font_names:
        shutil.copy2(FONTS_DIR / font_name, fonts_dest / font_name)

    copy_optional("LICENSE", dest)
    copy_optional("THIRD_PARTY_LICENSES.md", dest)
    copy_optional("README.md", dest)

    if with_site:
        copy_optional("index.html", dest)
        copy_optional("_headers", dest)

    total_mb = sum((fonts_dest / font).stat().st_size for font in font_names) / 1024 / 1024
    rules = css_text.count("@font-face")
    print(f"{display_path(dest)}  {css_name}  {rules} rules  {len(font_names)} fonts  {total_mb:.1f} MB")


def build(out_root: Path, clean: bool, with_site: bool) -> None:
    if clean and out_root.exists():
        shutil.rmtree(out_root)
        print(f"Cleaned {display_path(out_root)}")

    out_root.mkdir(parents=True, exist_ok=True)
    for name, config in VARIANTS.items():
        build_variant(name, config["css"], config["families"], out_root, with_site)

    print("\nArtifacts ready:")
    for name in VARIANTS:
        print(f"  {out_root / name}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clean", action="store_true", help="Delete the output directory before building")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Output root (default: {DEFAULT_OUT})")
    ap.add_argument("--with-site", action="store_true", help="Also copy index.html and _headers into each artifact")
    args = ap.parse_args()

    out_root = args.out if args.out.is_absolute() else ROOT / args.out
    build(out_root=out_root, clean=args.clean, with_site=args.with_site)


if __name__ == "__main__":
    main()
