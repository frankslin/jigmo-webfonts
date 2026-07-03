#!/usr/bin/env python3
"""
Build full Jigmo SC/TC font variants by replacing selected upstream glyphs.

The generated fonts keep upstream Jigmo as the baseline and only replace CJK
glyphs when GlyphWiki has a preferred source glyph:

    Jigmo SC: uXXXXX-g -> uXXXXX-t -> original Jigmo glyph
    Jigmo TC: uXXXXX-t -> uXXXXX-g -> original Jigmo glyph

Usage:
    python build_jigmo_variants.py --prepare-only
    python build_jigmo_variants.py --limit 10
    python build_jigmo_variants.py --render-kage-svg --download-kage-engine

The GlyphWiki dump contains KAGE data, not SVG outlines. The full build can
render missing SVGs locally through kage-engine, reuse an existing SVG cache,
or download missing SVG files from glyphwiki.org with explicit --allow-remote-svg.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "src"
WORK_DIR = SRC_DIR / "glyphwiki"
LEGACY_WORK_DIR = SRC_DIR / "jigmo-cn"
GLYPH_DIR = WORK_DIR / "glyph"
FONT_DIR = WORK_DIR / "font"
KAGE_ENGINE_DIR = WORK_DIR / "kage-engine"
KAGE_DATA_PATH = WORK_DIR / "kage-data.tsv"
KAGE_DATA_META_PATH = WORK_DIR / "kage-data.tsv.meta"
KAGE_DATA_CACHE_VERSION = "3"
KAGE_RENDERER = ROOT / "render_glyphwiki_svgs.js"

GLYPHWIKI_DUMP_URL = "https://glyphwiki.org/dump.tar.gz"
KAGE_ENGINE_RAW_BASE = "https://raw.githubusercontent.com/kamichikoichi/kage-engine/master"
KAGE_ENGINE_FILES = (
    "2d.js",
    "buhin.js",
    "curve.js",
    "kage.js",
    "kagecd.js",
    "kagedf.js",
    "polygon.js",
    "polygons.js",
    "COPYING",
)
HTTP_HEADERS = {
    "User-Agent": "jigmo-webfonts/1.0 (+https://github.com/frankslin/jigmo-webfonts)",
}

SOURCE_FONT_FILES = ("Jigmo.ttf", "Jigmo2.ttf", "Jigmo3.ttf")
BASE_FONTS = (
    ("", SRC_DIR / "Jigmo.ttf", lambda cp: cp <= 0x1FFFF),
    ("2", SRC_DIR / "Jigmo2.ttf", lambda cp: 0x20 <= cp <= 0xFF or 0x20000 <= cp <= 0x2FFFF),
    ("3", SRC_DIR / "Jigmo3.ttf", lambda cp: 0x20 <= cp <= 0xFF or 0x30000 <= cp <= 0x3FFFF),
)
VARIANTS = {
    "sc": {
        "family": "Jigmo SC",
        "postscript": "JigmoSC",
        "priority": ("g", "t"),
        "description": "G-source preferred, T-source fallback, then original Jigmo",
    },
    "tc": {
        "family": "Jigmo TC",
        "postscript": "JigmoTC",
        "priority": ("t", "g"),
        "description": "T-source preferred, G-source fallback, then original Jigmo",
    },
}

CJK_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAD9),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x2EBF0, 0x2EE5F),
    (0x2F800, 0x2FA1F),
    (0x30000, 0x3134F),
    (0x31350, 0x323AF),
    (0x323B0, 0x3347F),
)

VERSIONED_REF_RE = re.compile(r":([^:$\s]+@[0-9]+)(?=[:$])")


def log(message: str) -> None:
    print(message, flush=True)


@dataclass(frozen=True)
class Replacement:
    variant: str
    font_name: str
    source_font: Path
    codepoint: int
    encoded_name: str
    source_name: str
    source_kind: str


def cp_name(cp: int) -> str:
    return f"u{cp:04x}" if cp <= 0xFFFF else f"u{cp:x}"


def base_name(name: str) -> str:
    return name.split("-", 1)[0]


def glyph_path(name: str) -> Path:
    base = base_name(name)
    return GLYPH_DIR / base[:-3] / base[:-2] / f"{name}.svg"


def is_cjk(cp: int) -> bool:
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def fontforge_select(cp: int) -> str:
    return f"0u{cp:x}"


def glyph_width(cp: int) -> int:
    if 0x20 <= cp <= 0x7E:
        return 512
    category = unicodedata.category(chr(cp)) if cp <= 0x10FFFF else ""
    if category.startswith("M"):
        return 0
    return 1024


def output_font_name(variant: str, suffix: str) -> str:
    return f"{VARIANTS[variant]['postscript']}{suffix}"


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    log(f"Downloading {url} -> {dest}")
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as fp:
        shutil.copyfileobj(response, fp)
    tmp.replace(dest)


def ensure_inputs() -> None:
    missing = [name for name in SOURCE_FONT_FILES if not (SRC_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            "Missing upstream Jigmo source fonts: "
            + ", ".join(missing)
            + ". Run `python build.py --no-ss4 --no-sht` first."
        )


def ensure_dump(dump_path: Path) -> None:
    if dump_path.exists():
        return
    legacy_dump = LEGACY_WORK_DIR / "dump.tar.gz"
    if legacy_dump.exists():
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_dump, dump_path)
        log(f"Copied existing GlyphWiki dump -> {dump_path}")
        return
    download(GLYPHWIKI_DUMP_URL, dump_path)


def load_repertoire(ttf_path: Path) -> set[int]:
    from fontTools.ttLib import TTFont

    font = TTFont(str(ttf_path), lazy=True)
    try:
        cmap = font.getBestCmap() or {}
        return {
            cp
            for cp in cmap
            if 0 <= cp <= 0x10FFFF
            and not (0xF0000 <= cp <= 0x10FFFF)  # upstream IVS helper glyphs
        }
    finally:
        font.close()


def load_glyphwiki_names(dump_path: Path) -> set[str]:
    log(f"Loading GlyphWiki names from {dump_path}")
    names: set[str] = set()
    with tarfile.open(dump_path, "r:gz") as tar:
        fp = tar.extractfile("dump_newest_only.txt")
        if fp is None:
            raise RuntimeError("dump_newest_only.txt not found in GlyphWiki dump")
        wrapper = io.TextIOWrapper(fp, encoding="utf-8", errors="replace")
        for line in wrapper:
            if "|" not in line:
                continue
            name = line.split("|", 1)[0].strip()
            if name and name != "name" and not set(name) <= {"-"}:
                names.add(name)
    log(f"Loaded {len(names):,} GlyphWiki names")
    return names


def parse_dump_line(line: str) -> tuple[str, str] | None:
    if "|" not in line:
        return None
    parts = line.rstrip("\n").split("|", 2)
    if len(parts) < 3:
        return None
    name = parts[0].strip().replace("\\@", "@")
    data = parts[2].strip()
    if not name or not data or name == "name" or set(name) <= {"-"}:
        return None
    return name, data


def versioned_refs(data: str) -> set[str]:
    return set(VERSIONED_REF_RE.findall(data))


def write_kage_data_cache(dump_path: Path) -> Path:
    if (
        KAGE_DATA_PATH.exists()
        and KAGE_DATA_META_PATH.exists()
        and KAGE_DATA_META_PATH.read_text(encoding="utf-8").strip() == KAGE_DATA_CACHE_VERSION
        and KAGE_DATA_PATH.stat().st_mtime >= dump_path.stat().st_mtime
    ):
        return KAGE_DATA_PATH

    KAGE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = KAGE_DATA_PATH.with_suffix(".tsv.tmp")
    newest_count = 0
    versioned_count = 0
    pending_versioned: set[str] = set()
    resolved_versioned: set[str] = set()
    with tarfile.open(dump_path, "r:gz") as tar, tmp.open("w", encoding="utf-8") as out:
        log("Writing KAGE data cache from dump_newest_only.txt")
        fp = tar.extractfile("dump_newest_only.txt")
        if fp is None:
            raise RuntimeError("dump_newest_only.txt not found in GlyphWiki dump")
        wrapper = io.TextIOWrapper(fp, encoding="utf-8", errors="replace")
        for line in wrapper:
            parsed = parse_dump_line(line)
            if parsed is None:
                continue
            name, data = parsed
            out.write(f"{name}\t{data}\n")
            newest_count += 1
            pending_versioned.update(versioned_refs(data))

        pass_no = 0
        unresolved: set[str] = set()
        while pending_versioned:
            pass_no += 1
            wanted = pending_versioned - resolved_versioned
            if not wanted:
                break
            log(f"Resolving versioned KAGE components pass {pass_no}: {len(wanted):,} pending")
            pending_versioned = set()
            found_this_pass = 0
            fp = tar.extractfile("dump_all_versions.txt")
            if fp is None:
                raise RuntimeError("dump_all_versions.txt not found in GlyphWiki dump")
            wrapper = io.TextIOWrapper(fp, encoding="utf-8", errors="replace")
            for line in wrapper:
                parsed = parse_dump_line(line)
                if parsed is None:
                    continue
                name, data = parsed
                if name not in wanted:
                    continue
                out.write(f"{name}\t{data}\n")
                resolved_versioned.add(name)
                versioned_count += 1
                found_this_pass += 1
                pending_versioned.update(ref for ref in versioned_refs(data) if ref not in resolved_versioned)
            unresolved = wanted - resolved_versioned
            log(
                f"  resolved={found_this_pass:,}; "
                f"new_pending={len(pending_versioned - resolved_versioned):,}; "
                f"unresolved={len(unresolved):,}"
            )
            if found_this_pass == 0:
                break
    tmp.replace(KAGE_DATA_PATH)
    KAGE_DATA_META_PATH.write_text(KAGE_DATA_CACHE_VERSION + "\n", encoding="utf-8")
    total = newest_count + versioned_count
    log(
        f"KAGE data cache -> {KAGE_DATA_PATH} "
        f"({total:,} glyphs: newest={newest_count:,}, versioned={versioned_count:,}, unresolved={len(unresolved):,})"
    )
    return KAGE_DATA_PATH


def choose_replacement(cp: int, names: set[str], priority: tuple[str, str]) -> tuple[str, str] | None:
    if not is_cjk(cp):
        return None
    name = cp_name(cp)
    for source in priority:
        source_name = f"{name}-{source}"
        if source_name in names:
            return source_name, source
    return None


def build_replacements(dump_path: Path, variants: set[str]) -> list[Replacement]:
    names = load_glyphwiki_names(dump_path)
    replacements: list[Replacement] = []
    for suffix, source_font, predicate in BASE_FONTS:
        log(f"Scanning {source_font.name}")
        cps = sorted(cp for cp in load_repertoire(source_font) if predicate(cp))
        log(f"  {source_font.name}: {len(cps):,} candidate codepoints")
        for variant in sorted(variants):
            font_name = output_font_name(variant, suffix)
            priority = VARIANTS[variant]["priority"]
            font_count = 0
            for cp in cps:
                chosen = choose_replacement(cp, names, priority)
                if chosen is None:
                    continue
                source_name, source_kind = chosen
                replacements.append(
                    Replacement(
                        variant=variant,
                        font_name=font_name,
                        source_font=source_font,
                        codepoint=cp,
                        encoded_name=cp_name(cp),
                        source_name=source_name,
                        source_kind=source_kind,
                    )
                )
                font_count += 1
            log(f"{font_name}: {font_count:,} replacement glyphs")
    return replacements


def write_manifest(replacements: list[Replacement], limit: int | None = None) -> dict[str, list[Replacement]]:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    by_font: dict[str, list[Replacement]] = {}
    for repl in replacements:
        by_font.setdefault(repl.font_name, []).append(repl)

    rows = ["variant\tfont\tcodepoint\tsource\tkind"]
    limited_by_font: dict[str, list[Replacement]] = {}
    for font_name in sorted(by_font):
        entries = sorted(by_font[font_name], key=lambda item: item.codepoint)
        if limit is not None:
            entries = entries[:limit]
        limited_by_font[font_name] = entries
        (WORK_DIR / f"{font_name}.replacements.txt").write_text(
            "\n".join(f"{entry.encoded_name}\t{entry.source_name}\t{entry.source_kind}" for entry in entries)
            + "\n",
            encoding="utf-8",
        )
        for entry in entries:
            rows.append(
                f"{entry.variant}\t{entry.font_name}\t{entry.encoded_name}\t{entry.source_name}\t{entry.source_kind}"
            )
    (WORK_DIR / "variant-glyph-map.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    counts: dict[str, int] = {}
    for entries in limited_by_font.values():
        for entry in entries:
            key = f"{entry.variant}:{entry.source_kind}"
            counts[key] = counts.get(key, 0) + 1
    log("Replacement selection: " + ", ".join(f"{k}={v:,}" for k, v in sorted(counts.items())))
    log(f"Map -> {WORK_DIR / 'variant-glyph-map.tsv'}")
    return limited_by_font


def fetch_one(name: str, force: bool = False) -> tuple[str, bool, str | None]:
    dest = glyph_path(name)
    if dest.exists() and not force:
        return name, False, None
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://glyphwiki.org/glyph/{name}.svg"
    last_error: str | None = None
    for _attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HTTP_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
            if data.startswith(b"<svg") and len(data) > 193:
                tmp = dest.with_suffix(".svg.tmp")
                tmp.write_bytes(data)
                tmp.replace(dest)
                return name, True, None
            last_error = f"unexpected response ({len(data)} bytes)"
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc)
        time.sleep(1)
    return name, False, last_error or "unknown error"


def replacement_svg_names(replacements_by_font: dict[str, list[Replacement]]) -> list[str]:
    return sorted({entry.source_name for entries in replacements_by_font.values() for entry in entries})


def missing_svg_names(names: list[str]) -> list[str]:
    return [name for name in names if not glyph_path(name).exists()]


def write_name_list(path: Path, names: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")
    return path


def download_svgs(replacements_by_font: dict[str, list[Replacement]], jobs: int, force: bool) -> None:
    names = replacement_svg_names(replacements_by_font)
    targets = names if force else missing_svg_names(names)
    log(f"SVGs: {len(names):,} unique replacement glyphs; missing={len(targets):,}")
    if not targets:
        return

    failures: list[tuple[str, str]] = []
    done = 0
    downloaded = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        future_map = {executor.submit(fetch_one, name, force): name for name in targets}
        for future in concurrent.futures.as_completed(future_map):
            name, did_download, error = future.result()
            done += 1
            if did_download:
                downloaded += 1
            if error:
                failures.append((name, error))
            if done % 1000 == 0 or done == len(targets):
                log(f"  [{done:6d}/{len(targets)}] downloaded={downloaded:,} failures={len(failures):,}")
    if failures:
        report = WORK_DIR / "svg-failures.tsv"
        report.write_text("\n".join(f"{name}\t{error}" for name, error in failures) + "\n", encoding="utf-8")
        raise RuntimeError(f"{len(failures)} SVG downloads failed; see {report}")


def ensure_kage_engine(engine_dir: Path, download_missing: bool) -> None:
    missing = [name for name in KAGE_ENGINE_FILES if not (engine_dir / name).exists()]
    if not missing:
        return
    if not download_missing:
        raise SystemExit(
            "Missing kage-engine files in "
            f"{engine_dir}: {', '.join(missing)}. "
            "Re-run with --download-kage-engine, or pass --kage-engine-dir to an existing checkout."
        )
    engine_dir.mkdir(parents=True, exist_ok=True)
    for name in missing:
        download(f"{KAGE_ENGINE_RAW_BASE}/{name}", engine_dir / name)


def render_svgs_from_kage(
    replacements_by_font: dict[str, list[Replacement]],
    dump_path: Path,
    engine_dir: Path,
    download_engine: bool,
    force: bool,
    cross_check_limit: int,
) -> None:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node is required to render SVGs with kage-engine")
    ensure_kage_engine(engine_dir, download_engine)

    names = replacement_svg_names(replacements_by_font)
    missing = missing_svg_names(names)
    targets = names if force or cross_check_limit else missing
    log(f"KAGE SVGs: {len(names):,} unique replacement glyphs; missing={len(missing):,}")
    if not targets:
        return

    data_path = write_kage_data_cache(dump_path)
    target_path = write_name_list(WORK_DIR / "kage-render-targets.txt", targets)
    check_report = WORK_DIR / "kage-svg-cross-check.tsv"
    cmd = [
        node,
        str(KAGE_RENDERER),
        "--engine-dir",
        str(engine_dir),
        "--data",
        str(data_path),
        "--targets",
        str(target_path),
        "--out-dir",
        str(GLYPH_DIR),
        "--check-existing-limit",
        str(cross_check_limit),
        "--check-report",
        str(check_report),
    ]
    if force:
        cmd.append("--force")
    subprocess.run(cmd, check=True)
    if cross_check_limit:
        log(f"KAGE cross-check -> {check_report}")


def check_svg_cache(replacements_by_font: dict[str, list[Replacement]]) -> None:
    names = replacement_svg_names(replacements_by_font)
    missing = missing_svg_names(names)
    if not missing:
        log(f"SVG cache complete: {len(names):,} replacement glyphs")
        return

    sample = ", ".join(missing[:5])
    raise SystemExit(
        "GlyphWiki dump contains KAGE data, not SVG outlines. "
        f"The local SVG cache is missing {len(missing):,} of {len(names):,} replacement glyphs "
        f"(for example: {sample}). "
        "Re-run with --render-kage-svg to generate missing SVGs locally, "
        "or --allow-remote-svg to fetch missing SVGs from glyphwiki.org, "
        "or run --prepare-only if you only need the replacement map."
    )


def source_font_for_output(font_name: str) -> Path:
    if font_name.endswith("2"):
        return SRC_DIR / "Jigmo2.ttf"
    if font_name.endswith("3"):
        return SRC_DIR / "Jigmo3.ttf"
    return SRC_DIR / "Jigmo.ttf"


def write_fontforge_script(font_name: str, replacements: list[Replacement]) -> Path:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    script = FONT_DIR / f"{font_name}.scr"
    family_name = "Jigmo SC" if font_name.startswith("JigmoSC") else "Jigmo TC"
    subfamily_name = "Regular"
    full_name = f"{family_name} {subfamily_name}"
    source_font = source_font_for_output(font_name)
    lines = [
        f'Print("{font_name}: opening source font")',
        f'Open("{source_font}")',
        "Reencode(\"UnicodeFull\")",
        f'Print("{font_name}: importing {len(replacements)} replacement glyphs")',
    ]
    for lang in ("0x409", "0x411"):
        lines.extend(
            [
                f'SetTTFName({lang},0,"GlyphWiki Project / Jigmo")',
                f'SetTTFName({lang},1,"{family_name}")',
                f'SetTTFName({lang},2,"{subfamily_name}")',
                f'SetTTFName({lang},4,"{full_name}")',
                f'SetTTFName({lang},5,"GlyphWiki current dump; source-priority replacement build")',
                f'SetTTFName({lang},6,"{font_name}")',
            ]
        )
    sorted_replacements = sorted(replacements, key=lambda item: item.codepoint)
    for index, entry in enumerate(sorted_replacements, start=1):
        svg = glyph_path(entry.source_name)
        if index == 1 or index % 1000 == 0 or index == len(sorted_replacements):
            lines.append(f'Print("{font_name}: import {index}/{len(sorted_replacements)}")')
        lines.extend(
            [
                f"Select({fontforge_select(entry.codepoint)})",
                "Clear()",
                f'Import("{svg}")',
                "Scale(105,105,512,307)",
                f"SetWidth({glyph_width(entry.codepoint)})",
                "Move(0, 30)",
                "SetVWidth(1024)",
                "RoundToInt()",
                "DontAutoHint()",
                "ClearHints()",
                "AutoInstr()",
            ]
        )
    lines.extend(
        [
            f'Print("{font_name}: generating TTF")',
            f'Generate("{FONT_DIR / (font_name + ".ttf")}")',
            f'Print("{font_name}: done")',
            "Quit()",
        ]
    )
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return script


def build_fonts(replacements_by_font: dict[str, list[Replacement]], force: bool) -> None:
    fontforge = shutil.which("fontforge")
    if not fontforge:
        raise RuntimeError("fontforge is required to build JigmoSC/JigmoTC fonts")
    font_items = sorted(replacements_by_font.items())
    for font_index, (font_name, replacements) in enumerate(font_items, start=1):
        out_path = SRC_DIR / f"{font_name}.ttf"
        if out_path.exists() and not force:
            log(f"[FontForge {font_index}/{len(font_items)}] skip {out_path}; use --force to rebuild")
            continue
        started_at = time.monotonic()
        script = write_fontforge_script(font_name, replacements)
        log(
            "\n"
            f"=== FontForge START {font_index}/{len(font_items)}: {font_name}.ttf ===\n"
            f"replacements: {len(replacements):,}\n"
            f"script: {script} ({script.stat().st_size / 1024 / 1024:.1f} MB)\n"
            f"output: {out_path}"
        )
        subprocess.run([fontforge, "-script", str(script)], check=True)
        built = FONT_DIR / f"{font_name}.ttf"
        if not built.exists():
            raise RuntimeError(f"FontForge did not produce {built}")
        shutil.copy2(built, out_path)
        elapsed = time.monotonic() - started_at
        log(
            f"=== FontForge DONE {font_index}/{len(font_items)}: {font_name}.ttf "
            f"({out_path.stat().st_size / 1024 / 1024:.1f} MB, {elapsed:.1f}s) ===\n"
        )


def parse_variants(raw: str) -> set[str]:
    if raw == "all":
        return set(VARIANTS)
    variants = {part.strip().lower() for part in raw.split(",") if part.strip()}
    unknown = variants - set(VARIANTS)
    if unknown:
        raise SystemExit(f"Unknown variant(s): {', '.join(sorted(unknown))}")
    return variants


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", type=Path, default=WORK_DIR / "dump.tar.gz", help="GlyphWiki dump path")
    ap.add_argument("--variants", default="all", help="Comma-separated variants to build: sc,tc,all")
    ap.add_argument("--jobs", type=int, default=min(16, (os.cpu_count() or 4) * 2), help="SVG download workers")
    ap.add_argument(
        "--allow-remote-svg",
        action="store_true",
        help="Download missing SVG outlines from glyphwiki.org/glyph/*.svg",
    )
    ap.add_argument(
        "--render-kage-svg",
        action="store_true",
        help="Render missing SVG outlines locally from GlyphWiki KAGE data",
    )
    ap.add_argument("--kage-engine-dir", type=Path, default=KAGE_ENGINE_DIR, help="External kage-engine directory")
    ap.add_argument(
        "--download-kage-engine",
        action="store_true",
        help="Download kage-engine into src/glyphwiki/kage-engine if missing",
    )
    ap.add_argument(
        "--kage-cross-check-limit",
        type=int,
        default=0,
        help="Compare this many existing cached SVGs against local KAGE output; use -1 for all",
    )
    ap.add_argument("--force", action="store_true", help="Re-download SVGs and rebuild existing TTFs")
    ap.add_argument("--prepare-only", action="store_true", help="Only write replacement map files")
    ap.add_argument("--download-only", action="store_true", help="Stop after SVG downloads")
    ap.add_argument("--limit", type=int, help="Limit replacements per output font for smoke testing")
    args = ap.parse_args()

    variants = parse_variants(args.variants)
    log(f"Build variants: {', '.join(sorted(variants))}; limit={args.limit if args.limit is not None else 'none'}")
    ensure_inputs()
    ensure_dump(args.dump)

    log("Stage: select replacement glyphs")
    replacements = build_replacements(args.dump, variants)
    replacements_by_font = write_manifest(replacements, limit=args.limit)
    if args.prepare_only:
        log("Done: prepare-only")
        return

    if args.render_kage_svg:
        log("Stage: render missing SVGs from local KAGE data")
        render_svgs_from_kage(
            replacements_by_font,
            args.dump,
            args.kage_engine_dir,
            args.download_kage_engine,
            args.force,
            args.kage_cross_check_limit,
        )
    elif args.allow_remote_svg:
        log("Stage: download missing SVGs from GlyphWiki")
        download_svgs(replacements_by_font, jobs=args.jobs, force=args.force)
    else:
        log("Stage: verify SVG cache")
        check_svg_cache(replacements_by_font)
    if args.download_only:
        log("Done: download-only")
        return

    log("Stage: build TTF variants with FontForge")
    build_fonts(replacements_by_font, force=args.force)
    log("Done")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
