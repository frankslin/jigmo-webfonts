#!/usr/bin/env python3
"""
Generate a CSV report for GlyphWiki G/T/J source glyph coverage.

The output is intended for lookup and auditing: one row per Unicode codepoint
that has a default uXXXXX glyph and/or a uXXXXX-g, uXXXXX-t, or uXXXXX-j source
glyph in the current GlyphWiki dump.

Usage:
    python glyphwiki_sources_csv.py
    python glyphwiki_sources_csv.py --only-source-coded
    python glyphwiki_sources_csv.py --out /tmp/glyphwiki-sources.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import shutil
import tarfile
import unicodedata
import urllib.request
from pathlib import Path


ROOT = Path(__file__).parent
WORK_DIR = ROOT / "src" / "glyphwiki"
LEGACY_WORK_DIR = ROOT / "src" / "jigmo-cn"
DEFAULT_DUMP = WORK_DIR / "dump.tar.gz"
DEFAULT_OUT = WORK_DIR / "glyphwiki-sources-g-t-j.csv"
GLYPHWIKI_DUMP_URL = "https://glyphwiki.org/dump.tar.gz"
HTTP_HEADERS = {
    "User-Agent": "jigmo-webfonts/1.0 (+https://github.com/frankslin/jigmo-webfonts)",
}
SOURCES = ("g", "t", "j")


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    print(f"Downloading {url} -> {dest}")
    with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as fp:
        shutil.copyfileobj(response, fp)
    tmp.replace(dest)


def ensure_dump(dump_path: Path) -> None:
    if dump_path.exists():
        return
    legacy_dump = LEGACY_WORK_DIR / "dump.tar.gz"
    if legacy_dump.exists():
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_dump, dump_path)
        print(f"Copied existing GlyphWiki dump -> {dump_path}")
        return
    download(GLYPHWIKI_DUMP_URL, dump_path)


def parse_dump(dump_path: Path) -> dict[int, dict[str, str]]:
    rows: dict[int, dict[str, str]] = {}
    with tarfile.open(dump_path, "r:gz") as tar:
        fp = tar.extractfile("dump_newest_only.txt")
        if fp is None:
            raise RuntimeError("dump_newest_only.txt not found in GlyphWiki dump")
        wrapper = io.TextIOWrapper(fp, encoding="utf-8", errors="replace")
        for line in wrapper:
            parts = [part.strip() for part in line.rstrip("\n").split("|", 2)]
            if len(parts) != 3 or parts[0] == "name" or set(parts[0]) <= {"-"}:
                continue
            glyph_name, related, data = parts
            if not glyph_name.startswith("u"):
                continue
            stem, sep, suffix = glyph_name.partition("-")
            if not (4 <= len(stem[1:]) <= 6):
                continue
            try:
                cp = int(stem[1:], 16)
            except ValueError:
                continue
            if not 0 <= cp <= 0x10FFFF:
                continue
            if not sep:
                key = "default"
            elif suffix in SOURCES:
                key = suffix
            else:
                continue
            entry = rows.setdefault(cp, {})
            entry[f"{key}_name"] = glyph_name
            entry[f"{key}_related"] = related
            entry[f"{key}_sha1"] = hashlib.sha1(data.encode("utf-8")).hexdigest()[:12]
    return rows


def unicode_name(cp: int) -> str:
    try:
        return unicodedata.name(chr(cp))
    except ValueError:
        return ""


def block_name(cp: int) -> str:
    ranges = [
        ("CJK Ext A", 0x3400, 0x4DBF),
        ("CJK URO", 0x4E00, 0x9FFF),
        ("CJK Compatibility", 0xF900, 0xFAD9),
        ("CJK Ext B", 0x20000, 0x2A6DF),
        ("CJK Ext C", 0x2A700, 0x2B73F),
        ("CJK Ext D", 0x2B740, 0x2B81F),
        ("CJK Ext E", 0x2B820, 0x2CEAF),
        ("CJK Ext F", 0x2CEB0, 0x2EBEF),
        ("CJK Ext I", 0x2EBF0, 0x2EE5F),
        ("CJK Compatibility Supplement", 0x2F800, 0x2FA1F),
        ("CJK Ext G", 0x30000, 0x3134F),
        ("CJK Ext H", 0x31350, 0x323AF),
        ("CJK Ext J", 0x323B0, 0x3347F),
    ]
    for label, lo, hi in ranges:
        if lo <= cp <= hi:
            return label
    return ""


def write_csv(rows: dict[int, dict[str, str]], out_path: Path, only_source_coded: bool) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "codepoint",
        "char",
        "unicode_name",
        "block",
        "default_name",
        "has_default",
        "g_name",
        "has_g",
        "t_name",
        "has_t",
        "j_name",
        "has_j",
        "missing_sources",
        "available_sources",
        "g_sha1",
        "t_sha1",
        "j_sha1",
        "default_sha1",
        "g_equals_t",
        "g_equals_j",
        "t_equals_j",
        "default_equals_g",
        "default_equals_t",
        "default_equals_j",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for cp in sorted(rows):
            entry = rows[cp]
            has = {source: f"{source}_name" in entry for source in SOURCES}
            if only_source_coded and not any(has.values()):
                continue
            missing = [source.upper() for source in SOURCES if not has[source]]
            available = [source.upper() for source in SOURCES if has[source]]
            sha = {source: entry.get(f"{source}_sha1", "") for source in (*SOURCES, "default")}
            writer.writerow(
                {
                    "codepoint": f"U+{cp:04X}" if cp <= 0xFFFF else f"U+{cp:05X}",
                    "char": chr(cp),
                    "unicode_name": unicode_name(cp),
                    "block": block_name(cp),
                    "default_name": entry.get("default_name", ""),
                    "has_default": "1" if "default_name" in entry else "0",
                    "g_name": entry.get("g_name", ""),
                    "has_g": "1" if has["g"] else "0",
                    "t_name": entry.get("t_name", ""),
                    "has_t": "1" if has["t"] else "0",
                    "j_name": entry.get("j_name", ""),
                    "has_j": "1" if has["j"] else "0",
                    "missing_sources": "".join(missing),
                    "available_sources": "".join(available),
                    "g_sha1": sha["g"],
                    "t_sha1": sha["t"],
                    "j_sha1": sha["j"],
                    "default_sha1": sha["default"],
                    "g_equals_t": "1" if sha["g"] and sha["g"] == sha["t"] else "0",
                    "g_equals_j": "1" if sha["g"] and sha["g"] == sha["j"] else "0",
                    "t_equals_j": "1" if sha["t"] and sha["t"] == sha["j"] else "0",
                    "default_equals_g": "1" if sha["default"] and sha["default"] == sha["g"] else "0",
                    "default_equals_t": "1" if sha["default"] and sha["default"] == sha["t"] else "0",
                    "default_equals_j": "1" if sha["default"] and sha["default"] == sha["j"] else "0",
                }
            )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", type=Path, default=DEFAULT_DUMP, help="GlyphWiki dump path")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="CSV output path")
    ap.add_argument(
        "--only-source-coded",
        action="store_true",
        help="Only include codepoints that have at least one of -g, -t, or -j",
    )
    args = ap.parse_args()

    ensure_dump(args.dump)
    rows = parse_dump(args.dump)
    write_csv(rows, args.out, only_source_coded=args.only_source_coded)
    print(f"CSV -> {args.out} ({args.out.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
